from __future__ import annotations

from pathlib import Path
from typing import Optional, List

import typer

from .version import __version__
from .utils.logging import setup_logger
from .pipeline import RunConfig, run


app = typer.Typer(add_completion=False, help="Convert web pages to clean Markdown.")


@app.command()
def main(
    page: str = typer.Option(..., "-p", "--page", help="Source URL to extract"),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help="Output Markdown file path"),
    browser: Optional[bool] = typer.Option(None, help="Force browser fetch if true, disable if false; default auto"),
    use_jina: bool = typer.Option(False, "--use-jina", help="Use Jina Reader v1 directly"),
    use_firecrawl: bool = typer.Option(False, "--use-firecrawl", help="Use Firecrawl directly"),
    timeout: float = typer.Option(40.0, "--timeout", help="Timeout seconds"),
    retry: int = typer.Option(1, "--retry", help="Retries for transient errors"),
    header: List[str] = typer.Option(None, "--header", help="Extra HTTP header KEY=VALUE", show_default=False),
    cookie: List[str] = typer.Option(None, "--cookie", help="Cookie NAME=VALUE", show_default=False),
    respect_robots: bool = typer.Option(True, "--respect-robots/--ignore-robots", help="Respect robots.txt"),
    keep_images: bool = typer.Option(False, "--keep-images/--no-images", help="Keep images in output"),
    wrap: bool = typer.Option(True, "--wrap/--no-wrap", help="Reflow paragraphs to 80 cols"),
    front_matter: bool = typer.Option(True, "--front-matter/--no-front-matter", help="Add YAML front matter"),
    llm_eval: Optional[bool] = typer.Option(None, "--llm-eval/--no-llm", help="Enable/disable LLM evaluation"),
    min_coverage: float = typer.Option(0.6, "--min-coverage", help="Min coverage to pass heuristics"),
    log_level: str = typer.Option("INFO", "--log-level", help="Logging level"),
    llm_model: Optional[str] = typer.Option(None, "--llm-model", help="LLM model (default via env)"),
    version: bool = typer.Option(False, "--version", help="Print version and exit"),
):
    # Load environment variables from .env if present (best-effort)
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
    except Exception:
        pass
    if version:
        typer.echo(__version__)
        raise typer.Exit(code=0)

    setup_logger(log_level)
    cfg = RunConfig(
        page=page,
        output=output,
        use_jina=use_jina,
        use_firecrawl=use_firecrawl,
        browser=browser,
        timeout=timeout,
        retries=retry,
        headers=header,
        cookies=cookie,
        respect_robots=respect_robots,
        keep_images=keep_images,
        wrap=wrap,
        front_matter=front_matter,
        llm_eval=llm_eval,
        min_coverage=min_coverage,
        log_level=log_level,
        llm_model=llm_model,
    )
    run(cfg)


def entrypoint():
    app()

if __name__ == "__main__":
    entrypoint()
