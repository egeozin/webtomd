from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Optional

from lxml import html


@dataclass
class PageMetadata:
    title: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    date_published: Optional[str] = None
    date_modified: Optional[str] = None
    site_name: Optional[str] = None
    url: Optional[str] = None
    retrieved_at: Optional[str] = None
    generator: Optional[str] = None

    def to_dict(self) -> Dict[str, str]:
        return {k: v for k, v in asdict(self).items() if v}


def extract_metadata(doc: html.HtmlElement, url: Optional[str]) -> PageMetadata:
    def get_meta(name: str) -> Optional[str]:
        node = doc.xpath(f"//meta[@name='{name}']/@content")
        return node[0].strip() if node else None

    def get_og(name: str) -> Optional[str]:
        node = doc.xpath(f"//meta[@property='og:{name}']/@content")
        return node[0].strip() if node else None

    def get_itemprop(name: str) -> Optional[str]:
        node = doc.xpath(f"//meta[@itemprop='{name}']/@content")
        return node[0].strip() if node else None

    title_nodes = doc.xpath("//title/text()")
    h1_nodes = doc.xpath("//h1[normalize-space(string())!='']")
    title = None
    if h1_nodes:
        title = h1_nodes[0].text_content().strip()
    if not title and title_nodes:
        title = title_nodes[0].strip()
    if not title:
        title = get_og("title") or get_meta("title")

    meta = PageMetadata(
        title=title,
        description=get_og("description") or get_meta("description"),
        author=get_meta("author") or get_itemprop("author"),
        date_published=get_meta("article:published_time") or get_itemprop("datePublished"),
        date_modified=get_meta("article:modified_time") or get_itemprop("dateModified"),
        site_name=get_og("site_name"),
        url=url or get_og("url"),
        retrieved_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        generator="webtomd",
    )
    return meta

