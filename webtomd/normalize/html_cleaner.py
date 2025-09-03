from __future__ import annotations

from typing import Iterable, Optional, Set
from lxml import html, etree


BLOCK_KEEP: Set[str] = {
    "article",
    "section",
    "header",
    "footer",
    "main",
    "p",
    "pre",
    "blockquote",
    "ul",
    "ol",
    "li",
    "dl",
    "dt",
    "dd",
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "th",
    "td",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
}

INLINE_KEEP: Set[str] = {"a", "em", "strong", "code", "kbd", "samp", "sup", "sub", "abbr", "cite"}
MEDIA_KEEP: Set[str] = {"img"}

DISCARD: Set[str] = {
    "script",
    "style",
    "noscript",
    "template",
    "iframe",
    "canvas",
    "svg",
    "form",
    "input",
    "button",
    "select",
    "nav",
    "aside",
}


def _sanitize_text(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    # Remove control characters (0x00-0x1F) except for tab (0x09), newline (0x0A), and carriage return (0x0D)
    # and also remove the unicode replacement character (0xFFFD)
    # See https://www.w3.org/TR/xml/#charsets for valid XML characters.
    return "".join(ch for ch in text if ch.isprintable() or ch in ['\t', '\n', '\r'])


def parse_html(html_text: str) -> html.HtmlElement:
    return html.fromstring(html_text)


def pick_content_root(doc: html.HtmlElement) -> html.HtmlElement:
    nodes = doc.xpath("//main/article")
    if nodes:
        return nodes[0]
    nodes = doc.xpath("//body//article")
    if nodes:
        return nodes[0]
    nodes = doc.xpath("//main")
    if nodes:
        return nodes[0]
    body = doc.find(".//body")
    return body if body is not None else doc


def remove_comments_and_head(doc: html.HtmlElement) -> None:
    head = doc.find(".//head")
    if head is not None and head.getparent() is not None:
        head.getparent().remove(head)
    comments = doc.xpath("//comment()")
    for c in comments:
        p = c.getparent()
        if p is not None:
            p.remove(c)


def prune(root: html.HtmlElement, keep_images: bool = False) -> None:
    disallowed = set(DISCARD)
    if not keep_images:
        disallowed = disallowed.union(MEDIA_KEEP)
    for el in list(root.iter()):
        tag = el.tag.lower() if isinstance(el.tag, str) else ""
        if tag in disallowed:
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)
        elif tag not in BLOCK_KEEP and tag not in INLINE_KEEP and tag not in MEDIA_KEEP:
            # unwrap unknown/neutral elements
            parent = el.getparent()
            if parent is not None and tag not in {"html", "body"}:
                el.text = _sanitize_text(el.text)
                el.tail = _sanitize_text(el.tail)
                el.drop_tag()


def normalize_lists_tables(root: html.HtmlElement) -> None:
    # Ensure ul/ol children are li
    for lst in root.xpath("//ul|//ol"):
        for child in list(lst):
            if not isinstance(child.tag, str):
                continue
            if child.tag.lower() != "li":
                li = html.Element("li")
                idx = lst.index(child)
                lst.remove(child)
                li.append(child)
                lst.insert(idx, li)

    # Ensure table structure
    for table in root.xpath("//table"):
        # Move stray tr/td into tbody if needed
        tbodies = table.xpath("./tbody")
        if not tbodies:
            tbody = html.Element("tbody")
            for child in list(table):
                if isinstance(child.tag, str) and child.tag.lower() == "tr":
                    tbody.append(child)
            if len(tbody):
                table.append(tbody)


def wrap_stray_text(root: html.HtmlElement) -> None:
    # Wrap direct text nodes under sections into <p>
    for parent in root.xpath("//article|//section|//main|//div|//body"):
        if parent is None:
            continue
        # Leading text
        if parent.text and parent.text.strip():
            p = html.Element("p")
            p.text = _sanitize_text(parent.text)
            parent.text = None
            parent.insert(0, p)
        # Tail text for each child
        for child in list(parent):
            if child.tail and child.tail.strip():
                p = html.Element("p")
                p.text = _sanitize_text(child.tail)
                child.tail = None
                idx = parent.index(child)
                parent.insert(idx + 1, p)


def collapse_whitespace(root: html.HtmlElement) -> None:
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        if el.tag.lower() in {"pre", "code"}:
            continue
        if el.text:
            el.text = _sanitize_text(" ".join(el.text.split()))
        if el.tail:
            el.tail = _sanitize_text(" ".join(el.tail.split()))


def normalize_headings(root: html.HtmlElement) -> None:
    # Ensure only one h1; demote extras to h2
    h1s = root.xpath(".//h1")
    if len(h1s) > 1:
        for h in h1s[1:]:
            h.tag = "h2"


def to_clean_html(html_text: str, keep_images: bool = False) -> html.HtmlElement:
    doc = parse_html(html_text)
    remove_comments_and_head(doc)
    root = pick_content_root(doc)
    prune(root, keep_images=keep_images)
    normalize_lists_tables(root)
    wrap_stray_text(root)
    collapse_whitespace(root)
    normalize_headings(root)
    return root
