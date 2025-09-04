# webtomd

Convert web pages to clean markdown using a normalization pipeline, quality evaluation (heuristics + optional LLM), and fallbacks (Jina Reader v1, Firecrawl). Packaged and run with uv only.

## Quickstart

- Prerequisites: Python 3.9+ and `uv` installed (see Install as CLI Tool below).
- Everything installs locally into `.venv` via `uv sync` — no global/system packages required.

Commands:

- Install deps: `uv sync`
- Run help: `uv run webtomd --help`
- Convert a page: `uv run webtomd -p https://example.com -o article.md`
- Use Jina Reader v1: `uv run webtomd -p https://example.com -o article.md --use-jina`
- Use Firecrawl: `uv run webtomd -p https://example.com -o article.md --use-firecrawl`
- Build wheel/sdist: `uv build`
- Install CLI locally: `uv tool install .`

## Install as CLI Tool (requires uv)

`uv tool install .` installs the `webtomd` command into an isolated environment and drops a small launcher into your user bin directory.

- Install uv (if you don’t have it): follow https://docs.astral.sh/uv/ (e.g., the installer script shown there). Ensure `uv` is on your PATH.
- Install the CLI from this repo:
  - Default: `uv tool install .`
  - With browser extra (Playwright): `uv tool install .[browser]`
- Make sure the tool bin directory is on PATH so new shells can find `webtomd`:
  - Common location: `~/.local/bin` (macOS/Linux)
  - Bash/Zsh: add `export PATH="$HOME/.local/bin:$PATH"` to your shell rc
  - Fish: `echo 'fish_add_path ~/.local/bin' >> ~/.config/fish/config.fish`
- Verify in a new terminal: `webtomd --version`
- Update after changes: rerun `uv tool install .`
- Uninstall: `uv tool uninstall webtomd`

Notes:
- The installed tool runs in its own environment (separate from this repo’s `.venv`).
- For the optional browser mode, you still need to provision Chromium once: `uvx playwright install --with-deps chromium`.

Optional:

- LLM eval: set `OPENAI_API_KEY` and use `--llm-eval` (or auto if present).
- Firecrawl: set `FIRECRAWL_API_KEY`.
- Playwright browser fetch (optional): install extra `browser` deps then `uv run playwright install --with-deps chromium`.

## Features

- HTTP-first pipeline with realistic headers and robots.txt checks.
- HTML normalization per mini-spec (semantic blocks, remove chrome, fix lists/tables, collapse whitespace).
- Markdown conversion with custom rules and optional YAML front matter.
- Heuristic evaluation for coverage and structural fidelity; optional LLM checker.
- Fallbacks: Browser fetch, Jina Reader v1, Firecrawl.

## Notes on Ethics and Use

This tool is designed for personal archiving and research. It respects robots.txt by default and uses standard-compliant fetch methods. Avoid attempting to defeat access controls, paywalls, or anti-bot measures beyond regular browsing behavior.

## Development

- Run tests (when added): `uv run pytest`
- Format/lint: choose your tools; none enforced by default.

See IMPLEMENTATION_PLAN.md for architecture and roadmap details.

## Contributing

See CONTRIBUTING.md for setup and workflow. Please also review CODE_OF_CONDUCT.md and SECURITY.md.

## License

MIT — see LICENSE.

## Demo

Run the included demo script to try common flows and produce sample outputs in `demo_outputs/` (the demo auto-loads `.env`):

- Default pipeline only:
  - `uv run python scripts/demo_webtomd.py --url https://example.com/`
- With browser fallback allowed (requires `browser` extra installed and Playwright provisioned):
  - `uv sync --extra browser && uv run playwright install --with-deps chromium`
  - `uv run python scripts/demo_webtomd.py --browser --url https://example.com/`
- Compare with Jina Reader v1 and Firecrawl (set `FIRECRAWL_API_KEY` for Firecrawl):
  - `uv run python scripts/demo_webtomd.py --url https://example.com/ --jina --firecrawl`

Outputs:
- `<slug>.md`: default pipeline
- `<slug>.jina.md`: Jina Reader v1
- `<slug>.firecrawl.md`: Firecrawl

## Tests

- Run tests: `uv run pytest`
- Tests are offline and cover normalization, Markdown conversion (including tables), and wrapping.

## Environment & API Keys

- Copy `.env.example` to `.env` and fill as needed (the CLI auto-loads `.env`).
- Do not commit `.env` or any real API keys; `.env` is ignored by default.
- `OPENAI_API_KEY`: optional, enables LLM-based QA (`--llm-eval` or auto if present). Obtain an API key at https://platform.openai.com/ and be mindful of usage costs.
- `WEBTOMD_LLM_MODEL`: optional, override model name used (default `gpt-4o-mini`).
- `FIRECRAWL_API_KEY`: optional, used when running with `--use-firecrawl` (or as a fallback). Get a key from https://app.firecrawl.dev/; docs at https://docs.firecrawl.dev/.
- Jina Reader v1: does not require an API key. `--use-jina` calls the `r.jina.ai` reader gateway directly.

Notes:
- The default pipeline does not require any API keys and works offline aside from fetching the page.
- Environment variables take effect at runtime; CLI flags take precedence where applicable.

## OpenAI LLM Evaluation

LLM evaluation helps verify that generated Markdown matches the original HTML’s content and structure. It’s optional and only used if enabled.

- Enable via env or flag:
  - Add your key to `.env`: `OPENAI_API_KEY=sk-...`
  - Or export in your shell: `export OPENAI_API_KEY=sk-...`
  - Run with `--llm-eval` to explicitly enable, or rely on auto-enable when the API key is present.
  - Disable anytime with `--no-llm`.

- Model selection:
  - Default model: `gpt-4o-mini`.
  - Override via `.env`: `WEBTOMD_LLM_MODEL=gpt-4o`
  - Or per run: `--llm-model gpt-4o`

- What’s evaluated:
  - The default and browser pipelines (HTML → Markdown) can use LLM QA.
  - Jina/Firecrawl outputs use heuristic checks only (to conserve tokens). You can extend code to evaluate those too if desired.

- Behavior and fallbacks:
  - If LLM verdict is “fail”, the pipeline tries the next strategy (browser → Jina → Firecrawl).
  - If “pass”, the output is saved.

- Data sent to OpenAI:
  - URL and title, the first ~3000 chars of cleaned HTML text, and up to ~6000 chars of the produced Markdown.
  - No secrets are included; review `webtomd/evaluate/llm_eval.py` to customize.

- Examples:
  - Explicitly enable LLM: `uv run webtomd -p https://example.com -o out.md --llm-eval`
  - Override model: `uv run webtomd -p https://example.com -o out.md --llm-eval --llm-model gpt-4o`
  - Disable when key is set: `uv run webtomd -p https://example.com -o out.md --no-llm`
  - Debug verdict: add `--log-level debug` to view LLM verdict and score in logs.

Costs and limits:
- LLM evaluation consumes tokens; monitor usage and rate limits in your OpenAI account.
# webtomd

Convert web pages to clean Markdown. Simple, fast, and works out‑of‑the‑box.

## Install (with uv)

- Requires: Python 3.9+ and `uv` (see https://docs.astral.sh/uv/)
- Try without installing: `uv run webtomd --help`
- Install the CLI: `uv tool install .`
  - Browser fallback support: `uv tool install .[browser]`
  - Ensure your user bin (often `~/.local/bin`) is on PATH

## Use

- Convert a page:
  - Not installed: `uv run webtomd -p https://example.com -o article.md`
  - Installed: `webtomd -p https://example.com -o article.md`
- Optional providers:
  - Jina Reader v1: `--use-jina`
  - Firecrawl: `--use-firecrawl` (needs `FIRECRAWL_API_KEY`)
- LLM quality check (optional): auto if `OPENAI_API_KEY` is set; disable with `--no-llm`

## Notes

- Respects robots.txt by default; override with `--ignore-robots` if needed.
- `.env` support in your working directory: copy `.env.example` to `.env` (never commit secrets).
- Optional keys: `OPENAI_API_KEY` (LLM evaluation), `FIRECRAWL_API_KEY` (Firecrawl).
- Browser fallback: after installing with `.[browser]`, run once: `uvx playwright install --with-deps chromium`.
- Output includes YAML front matter (URL, optional title) and tidy paragraph wrapping by default.
