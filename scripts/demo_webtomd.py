from __future__ import annotations

import argparse
import os
from pathlib import Path

from webtomd.pipeline import RunConfig, run
from webtomd.utils.logging import setup_logger
from webtomd.utils.url import slugify


def main():
    p = argparse.ArgumentParser(description="Demo runner for webtomd")
    p.add_argument("--url", action="append", help="URL to process (repeatable)")
    p.add_argument("--browser", action="store_true", help="Allow browser fallback")
    p.add_argument("--jina", action="store_true", help="Also run Jina Reader v1 for comparison")
    p.add_argument("--firecrawl", action="store_true", help="Also run Firecrawl for comparison (needs FIRECRAWL_API_KEY)")
    p.add_argument("--outdir", default="demo_outputs", help="Output directory")
    p.add_argument("--log-level", default="INFO", help="Log level")
    args = p.parse_args()

    setup_logger(args.log_level)
    urls = args.url or ["https://example.com/"]
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    for u in urls:
        base = slugify(u.replace("https://", "").replace("http://", "").strip("/")) or "page"
        # Default pipeline
        cfg = RunConfig(
            page=u,
            output=outdir / f"{base}.md",
            browser=True if args.browser else None,
        )
        print(f"[demo] Default pipeline: {u}")
        run(cfg)

        if args.jina:
            print(f"[demo] Jina Reader v1: {u}")
            cfg_j = RunConfig(page=u, output=outdir / f"{base}.jina.md", use_jina=True)
            run(cfg_j)

        if args.firecrawl:
            if not os.getenv("FIRECRAWL_API_KEY"):
                print("[demo] FIRECRAWL_API_KEY not set; skipping Firecrawl")
            else:
                print(f"[demo] Firecrawl: {u}")
                cfg_f = RunConfig(page=u, output=outdir / f"{base}.firecrawl.md", use_firecrawl=True)
                run(cfg_f)


if __name__ == "__main__":
    main()

