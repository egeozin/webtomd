from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional

from lxml import html

from .utils.logging import get_logger
from .utils.url import slugify, normalize_url
from .utils.io import write_text_file
from .utils.metadata import extract_metadata
from .utils.robots import is_allowed
from .fetchers import http_fetcher
from .fetchers.browser_fetcher import fetch_with_browser
from .fetchers.jina_reader import fetch_markdown as jina_fetch
from .fetchers.firecrawl_fetcher import fetch_markdown as firecrawl_fetch
from .normalize.html_cleaner import to_clean_html
from .convert.html_to_markdown import to_markdown
from .convert.wrap import reflow_paragraphs
from .convert.frontmatter import compose_front_matter
from .evaluate.heuristics import evaluate as eval_heur, HeuristicReport
from .evaluate.llm_eval import evaluate_with_openai


@dataclass
class RunConfig:
    page: str
    output: Optional[Path]
    use_jina: bool = False
    use_firecrawl: bool = False
    browser: Optional[bool] = None  # None=auto, True=force, False=disable
    timeout: float = 40.0
    retries: int = 1
    headers: Optional[Iterable[str]] = None
    cookies: Optional[Iterable[str]] = None
    respect_robots: bool = True
    keep_images: bool = False
    wrap: bool = True
    front_matter: bool = True
    llm_eval: Optional[bool] = None  # None=auto if OPENAI_API_KEY
    min_coverage: float = 0.6
    log_level: str = "INFO"
    llm_model: Optional[str] = None


def _maybe_llm_enabled(cfg: RunConfig) -> bool:
    import os

    if cfg.llm_eval is not None:
        return cfg.llm_eval
    return bool(os.getenv("OPENAI_API_KEY"))


def _finalize_output_path(cfg: RunConfig, meta_title: Optional[str]) -> Path:
    if cfg.output:
        return cfg.output
    slug = slugify(meta_title or "page") + ".md"
    return Path(slug)


def _http_pipeline(cfg: RunConfig, logger) -> Optional[str]:
    logger.debug("Fetching via HTTP")
    res = http_fetcher.fetch(cfg.page, timeout=cfg.timeout, headers=cfg.headers, cookies=cfg.cookies, retries=cfg.retries)
    cleaned = to_clean_html(res.html, keep_images=cfg.keep_images)
    md = to_markdown(cleaned)
    report = eval_heur(md, cleaned, cfg.min_coverage)
    logger.debug(f"Heuristics coverage={report.coverage:.2f} title={report.title_ok}")
    if _maybe_llm_enabled(cfg):
        meta = extract_metadata(cleaned.getroottree().getroot(), res.url)
        verdict = evaluate_with_openai(res.url, meta.title, cleaned.text_content(), md, model=cfg.llm_model)
        if verdict:
            logger.debug(f"LLM verdict={verdict.verdict} score={verdict.score}")
            if not verdict.passed():
                return None
    return md if report.passed(cfg.min_coverage) else None


def _browser_pipeline(cfg: RunConfig, logger) -> Optional[str]:
    try:
        bres = fetch_with_browser(cfg.page, timeout=max(cfg.timeout, 60.0))
    except Exception as e:
        logger.debug(f"Browser fetch error: {e}")
        return None
    cleaned = to_clean_html(bres.html, keep_images=cfg.keep_images)
    md = to_markdown(cleaned)
    report = eval_heur(md, cleaned, cfg.min_coverage)
    if _maybe_llm_enabled(cfg):
        meta = extract_metadata(cleaned.getroottree().getroot(), bres.url)
        verdict = evaluate_with_openai(bres.url, meta.title, cleaned.text_content(), md, model=cfg.llm_model)
        if verdict and not verdict.passed():
            return None
    return md if report.passed(cfg.min_coverage) else None


def _jina_pipeline(cfg: RunConfig, logger) -> Optional[str]:
    try:
        md = jina_fetch(cfg.page, timeout=max(cfg.timeout, 60.0))
    except Exception as e:
        logger.debug(f"Jina fetch error: {e}")
        return None
    report = eval_heur(md, None, cfg.min_coverage)
    return md if report.passed(cfg.min_coverage) else None


def _firecrawl_pipeline(cfg: RunConfig, logger) -> Optional[str]:
    try:
        md = firecrawl_fetch(cfg.page, timeout=max(cfg.timeout, 60.0))
    except Exception as e:
        logger.debug(f"Firecrawl fetch error: {e}")
        return None
    report = eval_heur(md, None, cfg.min_coverage)
    return md if report.passed(cfg.min_coverage) else None


def run(cfg: RunConfig) -> Path:
    logger = get_logger()
    page = normalize_url(cfg.page)
    logger.info(f"Source: {page}")

    if cfg.respect_robots:
        if not is_allowed(page):
            logger.warning("robots.txt disallows fetching this URL; use --ignore-robots to override.")
            raise SystemExit(2)

    result_md: Optional[str] = None
    tried = []

    if cfg.use_jina:
        tried.append("jina")
        result_md = _jina_pipeline(cfg, logger)
    elif cfg.use_firecrawl:
        tried.append("firecrawl")
        result_md = _firecrawl_pipeline(cfg, logger)
    else:
        # Default pipeline: HTTP -> (if needed) Browser -> Jina -> Firecrawl
        tried.append("http")
        result_md = _http_pipeline(cfg, logger)
        if result_md is None:
            if cfg.browser is None or cfg.browser is True:
                tried.append("browser")
                result_md = _browser_pipeline(cfg, logger)
        if result_md is None:
            tried.append("jina")
            result_md = _jina_pipeline(cfg, logger)
        if result_md is None:
            tried.append("firecrawl")
            result_md = _firecrawl_pipeline(cfg, logger)

    if result_md is None:
        logger.error(f"Failed after strategies: {', '.join(tried)}")
        raise SystemExit(1)

    # Compose front matter (best-effort)
    import re
    fm = ""
    if cfg.front_matter:
        title = None
        m = re.search(r"^#\s+(.+)$", result_md, flags=re.MULTILINE)
        if m:
            title = m.group(1).strip()
        meta_dict: Dict[str, str] = {"url": page, "generator": "webtomd"}
        if title:
            meta_dict["title"] = title
        fm = compose_front_matter(meta_dict)

    out_path = _finalize_output_path(cfg, None)
    final_md = result_md
    if cfg.wrap:
        final_md = reflow_paragraphs(final_md)
    written = write_text_file(out_path, (fm + final_md))
    logger.info(f"Saved: {written.path} ({written.bytes_written} bytes)")
    return written.path
