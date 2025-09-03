from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class BrowserFetchResult:
    url: str
    html: str


def fetch_with_browser(url: str, timeout: float = 60.0, wait_selector: Optional[str] = None) -> BrowserFetchResult:
    """Fetch final DOM HTML using Playwright if available.

    Note: Requires optional dependency `playwright`. This function attempts to
    import it lazily and raises a helpful error if missing.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:  # pragma: no cover - import-time
        raise RuntimeError(
            "Playwright is not installed. Install extra 'browser' (uv add --extra browser) "
            "and run 'uv run playwright install --with-deps chromium'."
        ) from e

    with sync_playwright() as p:  # pragma: no cover - requires browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()
        page.set_default_timeout(timeout * 1000)
        page.goto(url, wait_until="domcontentloaded")
        # Wait for a reasonable content anchor or network idle
        if wait_selector:
            try:
                page.wait_for_selector(wait_selector, timeout=timeout * 1000)
            except Exception:
                pass
        else:
            try:
                page.wait_for_load_state("networkidle", timeout=timeout * 1000)
            except Exception:
                pass
        content = page.content()
        final_url = page.url
        context.close()
        browser.close()
    return BrowserFetchResult(url=final_url, html=content)

