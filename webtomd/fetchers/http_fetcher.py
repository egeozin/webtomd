from __future__ import annotations

import httpx
from dataclasses import dataclass
from typing import Dict, Iterable, Optional


DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


@dataclass
class FetchResult:
    url: str
    status_code: int
    headers: Dict[str, str]
    html: str


def build_headers(extra_headers: Optional[Iterable[str]] = None) -> Dict[str, str]:
    headers = dict(DEFAULT_HEADERS)
    if extra_headers:
        for kv in extra_headers:
            if "=" in kv:
                k, v = kv.split("=", 1)
                headers[k.strip()] = v.strip()
    return headers


def build_cookies(cookie_items: Optional[Iterable[str]] = None) -> Dict[str, str]:
    jar: Dict[str, str] = {}
    if cookie_items:
        for item in cookie_items:
            if "=" in item:
                k, v = item.split("=", 1)
                jar[k.strip()] = v.strip()
    return jar


def fetch(url: str, timeout: float = 40.0, headers: Optional[Iterable[str]] = None, cookies: Optional[Iterable[str]] = None, retries: int = 1) -> FetchResult:
    hdrs = build_headers(headers)
    jar = build_cookies(cookies)
    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            with httpx.Client(http2=True, timeout=timeout, follow_redirects=True, headers=hdrs, cookies=jar) as client:
                resp = client.get(url)
                resp.raise_for_status()
                content = resp.text
                return FetchResult(url=str(resp.url), status_code=resp.status_code, headers=dict(resp.headers), html=content)
        except Exception as e:
            last_exc = e
            if attempt >= retries:
                raise
            continue
    # Should not reach here
    assert last_exc
    raise last_exc

