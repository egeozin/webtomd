# webtomd — Implementation Plan

A fast, reliable CLI to convert web pages into clean Markdown using a robust HTML normalization pipeline, with quality evaluation (heuristics + LLM) and fallback strategies (Jina Reader v1, Firecrawl). Packaged and run with uv only.

This document defines the architecture, CLI, algorithms, dependencies, and implementation steps to build the tool.

## Goals

- Robustly fetch and render web content, including dynamic pages when necessary.
- Normalize HTML into a semantic, minimal content tree following the provided principles.
- Convert normalized content to clean Markdown with consistent structure and front matter.
- Evaluate quality using deterministic heuristics and an (optional) LLM checker; auto-fallback if quality is insufficient.
- Provide explicit overrides to use Jina Reader v1 or Firecrawl as primary strategies.
- Package as a self-contained CLI via uv with reproducible builds and a clear developer workflow.

## Non-Goals

- Full-site crawling; this tool targets single-page extraction.
- Lossless preservation of all interactive features or arbitrary embedded media.

## CLI Specification

Command: `webtomd`

- Required
  - `-p, --page URL`: Source URL to extract.
  - `-o, --output PATH.md`: Output Markdown file path. If not provided, auto-generate from title/slug.

- Fetching and Strategy
  - `--browser/--no-browser`: Force Playwright browser-based fetch; default is auto (try HTTP first, then browser if needed).
  - `--use-jina`: Use Jina Reader v1 directly and skip the default pipeline.
  - `--use-firecrawl`: Use Firecrawl directly and skip the default pipeline.
  - `--timeout SECONDS`: Global timeout (default: 40s HTTP, 60s browser, 60s Firecrawl).
  - `--retry N`: Retries for transient errors (default: 1).
  - `--header KEY=VALUE`: Additional HTTP headers (repeatable).
  - `--cookie NAME=VALUE`: Cookies (repeatable).
  - `--respect-robots/--ignore-robots` (default: `--respect-robots`).

- Normalization and Conversion
  - `--keep-images/--no-images` (default: `--no-images`).
  - `--wrap/--no-wrap` (default: `--wrap`): Reflow long paragraphs to 80 columns.
  - `--front-matter/--no-front-matter` (default: `--front-matter`).

- Evaluation
  - `--llm-eval`: Enable LLM checker if API configured (default: auto if `OPENAI_API_KEY` present).
  - `--no-llm`: Disable LLM checker even if configured.
  - `--min-coverage FLOAT` (default: `0.6`): Minimum text coverage ratio threshold to pass heuristics.

- Misc
  - `--log-level [debug|info|warning|error]` (default: `info`).
  - `--version`

Examples

- Default pipeline with auto fallback to browser then Jina, then Firecrawl:
  - `webtomd -p "https://example.com/post" -o article.md`
- Force Jina Reader v1:
  - `webtomd -p "https://example.com/post" -o article.md --use-jina`
- Force Firecrawl:
  - `webtomd -p "https://example.com/post" -o article.md --use-firecrawl`
- Force browser fetch and disable LLM:
  - `webtomd -p "https://example.com/post" -o article.md --browser --no-llm`

## Architecture Overview

Modules (Python package: `webtomd`):

- `cli.py`: Argument parsing (Typer), orchestrates pipeline.
- `pipeline.py`: High-level orchestration; applies fetch → normalize → convert → evaluate → fallback.
- `fetchers/`
  - `http_fetcher.py`: HTTP(S) fetching via `httpx` with realistic defaults.
  - `browser_fetcher.py`: Playwright rendering; waits for network idle/main content.
  - `jina_reader.py`: Jina Reader v1 integration (`https://r.jina.ai/http://…`).
  - `firecrawl_fetcher.py`: Firecrawl v2 API integration.
- `normalize/`
  - `html_cleaner.py`: Apply mini-spec cleanup, removal of chrome and boilerplate, flatten text.
  - `readability_fallback.py`: Optional extraction using Readability-like approach when `main > article` not present.
- `convert/`
  - `html_to_markdown.py`: Convert cleaned HTML subtree to Markdown (customized markdownify rules + table handling + fenced code).
  - `frontmatter.py`: Compose YAML front matter from metadata.
- `evaluate/`
  - `heuristics.py`: Coverage ratio, heading/title checks, structural parity, table/code presence checks.
  - `llm_eval.py`: Optional structured judgment via OpenAI API; returns JSON verdict.
- `utils/`
  - `logging.py`: Rich logging setup.
  - `robots.py`: robots.txt checks.
  - `url.py`: URL normalization and slug generation.
  - `io.py`: Safe writing, overwrite prompts, charset detection.
  - `metadata.py`: Extract OpenGraph/Schema.org/article metadata.
- `version.py`: Version constant.

Data Flow

1. CLI parses options and builds a `RunConfig`.
2. Strategy resolution:
   - If `--use-jina`: fetch via Jina → evaluate → write.
   - Else if `--use-firecrawl`: fetch via Firecrawl → evaluate → write.
   - Else default: HTTP fetch → normalize → markdown → evaluate.
     - If fail: try Browser fetch → normalize → markdown → evaluate.
     - If fail: try Jina → evaluate. If fail: try Firecrawl → evaluate.
3. If evaluation passes: write Markdown with optional front matter and report success.
4. If all strategies fail: exit non-zero with summary diagnostics.

## HTML Normalization Mini-Spec (Mapping to Implementation)

Principles to implement:

- Keep only semantic text blocks: `p, table, pre, blockquote, ul, ol, dl` (+ headings `h1..h6`, `hr`, `code`, `li`, `dt`, `dd`, `th`, `td`).
- Structures consistent:
  - `table > (thead?, tbody?, tfoot?) > tr > (th|td)`; fix invalid children where possible.
  - `(ul|ol) > li` only; unwrap stray wrappers.
- Trim and collapse whitespace; no loose text nodes outside of paragraphs (wrap in `<p>` where needed).
- Flatten nested inline elements inside blocks; unwrap spans with no semantics; preserve emphasis/strong/links/code for Markdown.
- Remove or unwrap nodes: `script, style, noscript, template, iframe, canvas, svg` (keep `img` optionally), `form, input, button, select`, `nav, header, footer, aside`, ads/social/promos (heuristic class/id patterns, applied conservatively), empty elements, comments, `<head>` content.
- Prefer `main > article` as the content root; if absent, choose best candidate via heuristics/Readability fallback.

Algorithm outline:

- Parse with `lxml.html` (robust) or `selectolax` (fast); we’ll use `lxml` for normalization passes and tree surgery.
- Detect candidate root in priority: `main > article`, `body article`, `main`, Readability-like heuristic, else `body`.
- Prune disallowed nodes; unwrap neutral wrappers; repair tables and lists.
- Normalize headings tree; ensure `h1` exists using document title if needed; demote multi `h1` to `h2` if conflicts.
- Collapse whitespace; wrap stray text in `p`.
- Optionally keep images if `--keep-images` using `![alt](src)` with resolved absolute URLs.

## Markdown Conversion

- Use `markdownify` with custom rules configured for:
  - Headings `h1..h6` → `#` notation with spacing safeguards.
  - Tables → GitHub-style tables; when structure is complex, fallback to simple pipe tables.
  - `pre > code[class*="language-"]` → fenced blocks with language tag; otherwise plain fenced blocks.
  - Lists and nested lists with consistent indentation (2 spaces).
  - `blockquote` preserved; `hr` as `---`.
  - Links `[text](url)` with footnotes avoided unless necessary.
- Post-process Markdown:
  - Strip trailing spaces, collapse triple newlines to doubles, ensure one newline around headings/blocks.
  - Optional reflow (`--wrap`) using a conservative paragraph wrapper (not touching code/pre or tables).
- Compose YAML front matter (if enabled):
  - `title`, `description`, `author(s)`, `date_published`, `date_modified`, `url`, `site_name`, `retrieved_at`, `generator`.

## Evaluation

Deterministic heuristics (fast, offline):

- Coverage ratio: `len(markdown_text_no_md_syntax) / len(cleaned_html_text)` within `[min_coverage, 1.25]`.
- Heading parity: markdown first `#` heading matches HTML `h1` or `<title>` within a fuzzy similarity threshold.
- Structural presence checks:
  - If HTML contains `table`, ensure at least one table present in MD.
  - If HTML contains code blocks, ensure fenced blocks present.
  - If there are > N list items in HTML, ensure comparable count in MD (±30%).
- Boilerplate noise check: link density and nav/aside tokens should be low in MD.
- Language consistency: detect dominant language from HTML text and ensure MD language matches.

LLM checker (optional):

- Provider: OpenAI (via `OPENAI_API_KEY`).
- Input: concise context containing:
  - Page title and URL.
  - First K characters of cleaned HTML text (or extracted main text) and the produced Markdown.
  - Checklist: structural fidelity (headings, lists, tables, code), correctness of links, clarity/conciseness, missing sections.
- Output schema (JSON): `{ verdict: "pass|fail", score: 0..1, reasons: [..], suggestions: [..], missing_sections: [..] }`.
- Pass criteria: `verdict=pass` and `score >= 0.75`.

Fallback policy:

- If heuristics fail OR LLM says fail:
  1) If default HTTP was used, try Browser fetch → normalize → convert → re-evaluate.
  2) If still failing, try Jina Reader v1 → evaluate.
  3) If still failing, try Firecrawl → evaluate.
- If user specified `--use-jina` or `--use-firecrawl`, skip default and go directly to the chosen strategy; still evaluate for sanity.

## Fetching Strategies

HTTP fetch (default first attempt):

- `httpx` with HTTP/2 enabled, sensible timeouts, redirects allowed, cookie jar, and realistic headers:
  - `User-Agent` (desktop), `Accept`, `Accept-Language`, `Referer` if applicable.
- Charset detection and decoding; handle gzip/br.
- Respect robots.txt unless `--ignore-robots` is set. Surface a clear warning if ignored.

Browser fetch (automatic fallback or `--browser`):

- Playwright Chromium (headless by default) with standard viewport and user-agent.
- Wait for network idle and/or content markers (e.g., presence of `article`, `main`, or notable text length).
- Extract HTML of the final DOM (`page.content()`).
- Note: no stealth/evasion; standard compliant automation only.

Jina Reader v1 (override or fallback):

- Request: `GET https://r.jina.ai/http://{URL}` (or `https://r.jina.ai/https://{URL}` accordingly).
- Response is readable text/markdown of main content. Treat as Markdown, still evaluate.

Firecrawl v2 (override or fallback):

- Endpoint (per docs): `POST https://api.firecrawl.dev/v2/scrape`
- Headers: `Authorization: Bearer ${FIRECRAWL_API_KEY}`
- Body example: `{ "url": "https://…", "formats": ["markdown"], "onlyMainContent": true }`
- Use returned Markdown. Still evaluate.

## Error Handling & Retries

- Categorize errors: network, HTTP status, charset, DOM parse, evaluation failure.
- Retry transient network errors (up to `--retry`).
- Provide informative exit codes/messages and a summary of which strategies were attempted.

## Logging

- Use `rich` for colored logs and progress spinners.
- Debug mode dumps:
  - Raw HTML (first 100KB) and cleaned HTML snapshot to temp files.
  - Evaluation JSON and heuristic metrics.
- Redact secrets (API keys) in logs.

## Security & Ethics

- Default: respect robots.txt and rate limits; identify as a person in `User-Agent`.
- Provide `--ignore-robots` only as an explicit advanced flag with a warning.

## Project Structure

```
webtomd/
  webtomd/
    __init__.py
    version.py
    cli.py
    pipeline.py
    fetchers/
      __init__.py
      http_fetcher.py
      browser_fetcher.py
      jina_reader.py
      firecrawl_fetcher.py
    normalize/
      __init__.py
      html_cleaner.py
      readability_fallback.py
    convert/
      __init__.py
      html_to_markdown.py
      frontmatter.py
    evaluate/
      __init__.py
      heuristics.py
      llm_eval.py
    utils/
      __init__.py
      logging.py
      robots.py
      url.py
      io.py
      metadata.py
  tests/
    test_cli.py
    test_normalize_basic.py
    test_markdown_tables.py
    fixtures/
      sample_static.html
      sample_dynamic.html
  pyproject.toml
  README.md
  LICENSE (optional)
```

## Dependencies (managed by uv)

- Core
  - `httpx` (HTTP/2, timeouts, redirects)
  - `lxml` (HTML parsing and tree surgery)
  - `markdownify` (HTML → Markdown with custom rules)
  - `typer` and `rich` (CLI + logging)
  - `pydantic` (evaluation schemas)

- Optional
  - `playwright` (browser fetch)
  - `openai` (LLM evaluation)
  - `python-dotenv` (local dev of API keys)
  - `langdetect` (language detection)

Notes

- After install, browsers must be provisioned once: `uv run playwright install --with-deps chromium` (or `stable`).

## uv Packaging & Commands

- `pyproject.toml` (PEP 621) with:
  - `project.name = "webtomd"`
  - `project.version = "0.1.0"`
  - `project.dependencies = [ ... ]`
  - `project.optional-dependencies` groups: `browser`, `llm`.
  - `project.scripts = { webtomd = "webtomd.cli:main" }`
- Common commands:
  - `uv sync` — create venv and install deps.
  - `uv run webtomd --help`
  - `uv build` — build wheel/sdist.
  - `uv tool install .` — install CLI locally from the repo.

## Environment Variables

- `OPENAI_API_KEY` — LLM evaluation (optional).
- `FIRECRAWL_API_KEY` — Firecrawl integration (optional).

## Pseudocode Highlights

Pipeline (simplified):

```python
result = None
if cfg.use_jina:
    result = fetch_via_jina(url)
elif cfg.use_firecrawl:
    result = fetch_via_firecrawl(url)
else:
    page = http_fetch(url)
    html = page.html
    cleaned = normalize(html)
    md = to_markdown(cleaned)
    if evaluate(md, cleaned, cfg):
        result = md
    else:
        if cfg.allow_browser:
            html = browser_fetch(url)
            cleaned = normalize(html)
            md = to_markdown(cleaned)
            if evaluate(md, cleaned, cfg):
                result = md
        if result is None:
            md = fetch_via_jina(url)
            if evaluate(md, None, cfg):
                result = md
        if result is None:
            md = fetch_via_firecrawl(url)
            if evaluate(md, None, cfg):
                result = md

if result is None:
    fail()
else:
    write_markdown(output_path, front_matter + result)
```

Normalization core (sketch):

```python
def normalize(html: str) -> lxml.html.HtmlElement:
    doc = lxml.html.fromstring(html)
    root = pick_content_root(doc)
    prune_disallowed(root)
    repair_tables(root)
    repair_lists(root)
    wrap_stray_text(root)
    collapse_whitespace(root)
    normalize_headings(root)
    if not keep_images:
        remove_images(root)
    return root
```

Heuristics (sketch):

```python
def evaluate(md: str, cleaned_root: Optional[HtmlElement], cfg) -> bool:
    if cleaned_root is None:
        # External provider — run lighter checks only
        return simple_md_sanity(md)
    text_html = extract_visible_text(cleaned_root)
    text_md = strip_md_syntax(md)
    coverage = len(text_md) / max(1, len(text_html))
    if not (cfg.min_coverage <= coverage <= 1.25):
        return False
    if not title_alignment_ok(cleaned_root, md):
        return False
    if contains_tables(cleaned_root) and not md_has_tables(md):
        return False
    if contains_code(cleaned_root) and not md_has_code_blocks(md):
        return False
    if cfg.llm_eval_enabled and not llm_passes(md, text_html):
        return False
    return True
```

## Testing Strategy

- Unit tests
  - Normalization: removing chrome elements, fixing lists/tables, whitespace.
  - Conversion: headings, lists, tables, code fences.
  - Heuristics: coverage, title/headings, presence checks.
- Integration tests
  - End-to-end on `fixtures/sample_static.html` and `fixtures/sample_dynamic.html` (browser tests are optional/marked).
- Skipped in CI by default
  - Network-dependent tests (LLM, Firecrawl, Jina) behind env flags.

## Implementation Steps

1. Scaffold project with uv, `pyproject.toml`, package layout, and basic CLI skeleton.
2. Implement HTTP fetcher with robots checks and headers.
3. Implement normalization passes and content root selection.
4. Implement Markdown conversion with custom rules and front matter.
5. Implement heuristic evaluation.
6. Implement Playwright browser fetcher and auto fallback.
7. Implement Jina Reader v1 and Firecrawl integrations.
8. Implement LLM evaluation (OpenAI) with structured output.
9. Wire up pipeline, flags, and logging.
10. Add unit/integration tests and fixtures.
11. Write README with examples and uv usage.
12. Build and local install via uv; manual validation on known pages.

## Acceptance Criteria

- CLI runs via `uv run webtomd --help` and `uv tool install .`.
- Default pipeline succeeds on representative static pages with good coverage and formatting.
- Browser fallback improves JS-heavy pages for at least one fixture.
- `--use-jina` and `--use-firecrawl` produce usable Markdown with evaluation.
- Heuristics catch obvious failures; LLM checker can reject low-quality output when enabled.
- Output Markdown includes optional YAML front matter and follows consistent formatting.

## Developer Workflow (uv Only)

- Setup: `uv sync`
- Dev run: `uv run webtomd -p https://example.com -o out.md`
- Install browsers (once): `uv run playwright install --with-deps chromium`
- Build: `uv build`
- Install tool locally: `uv tool install .`

## Future Enhancements

- Optional image downloading and local linking.
- PDF detection and extraction.
- More advanced main-content detection using text-density models.
- Additional LLM providers via a small adapter layer.

---

This plan is the basis for implementation. Once you confirm, we will scaffold the repo with uv and implement the modules as specified.

