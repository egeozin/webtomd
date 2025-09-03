from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse


_slug_re = re.compile(r"[^a-z0-9]+")


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme or "http"
    netloc = parsed.netloc
    path = parsed.path or "/"
    return urlunparse((scheme, netloc, path, "", parsed.query, parsed.fragment))


def slugify(text: str, max_len: int = 80) -> str:
    text = text.strip().lower()
    text = _slug_re.sub("-", text)
    text = text.strip("-")
    if not text:
        return "page"
    if len(text) > max_len:
        text = text[:max_len]
        text = text.rstrip("-")
    return text

