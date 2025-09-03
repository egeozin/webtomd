from __future__ import annotations

import httpx
from typing import Optional


def build_jina_url(url: str) -> str:
    if url.startswith("https://"):
        return f"https://r.jina.ai/https://{url[len('https://') :]}"
    if url.startswith("http://"):
        return f"https://r.jina.ai/http://{url[len('http://') :]}"
    # Default to http
    return f"https://r.jina.ai/http://{url}"


def fetch_markdown(url: str, timeout: float = 60.0) -> str:
    target = build_jina_url(url)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        resp = client.get(target)
        resp.raise_for_status()
        return resp.text

