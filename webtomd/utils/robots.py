from __future__ import annotations

import httpx
import urllib.robotparser as robotparser
from urllib.parse import urlparse


def is_allowed(url: str, user_agent: str = "webtomd/0.1") -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = robotparser.RobotFileParser()
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(robots_url)
            if resp.status_code >= 400:
                # No robots or inaccessible; default allow
                return True
            rp.parse(resp.text.splitlines())
    except Exception:
        return True
    return rp.can_fetch(user_agent, url)

