from __future__ import annotations

import httpx
import os
from typing import Optional


class FirecrawlError(RuntimeError):
    pass


def fetch_markdown(url: str, timeout: float = 60.0) -> str:
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise FirecrawlError("FIRECRAWL_API_KEY not set")
    endpoint = "https://api.firecrawl.dev/v2/scrape"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": True,
    }
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        resp = client.post(endpoint, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()
        # Expected structure: { "data": { "markdown": "..." } } or similar per docs
        if isinstance(data, dict):
            # Try common fields
            md = (
                data.get("markdown")
                or (data.get("data") or {}).get("markdown")
                or (data.get("content") or {}).get("markdown")
            )
            if md:
                return md
        raise FirecrawlError("Unexpected Firecrawl response structure")

