from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional
from lxml import html
from langdetect import detect as detect_lang


@dataclass
class HeuristicReport:
    coverage: float
    title_ok: bool
    tables_ok: bool
    code_ok: bool
    lists_ok: bool
    language_ok: bool

    def passed(self, min_coverage: float) -> bool:
        return (
            self.coverage >= min_coverage
            and self.title_ok
            and self.tables_ok
            and self.code_ok
            and self.lists_ok
            and self.language_ok
        )


def _visible_text(el: html.HtmlElement) -> str:
    text = el.text_content()
    return " ".join(text.split())


_md_syntax_re = re.compile(r"[#*_`~>\-\[\]\(\)\|]")


def strip_md_syntax(md: str) -> str:
    s = _md_syntax_re.sub("", md)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def md_has_tables(md: str) -> bool:
    return "|" in md and "---" in md


def md_has_code_blocks(md: str) -> bool:
    return "```" in md


def count_list_items(el: html.HtmlElement) -> int:
    return len(el.xpath(".//li"))


def contains_tables(el: html.HtmlElement) -> bool:
    return bool(el.xpath(".//table"))


def contains_code(el: html.HtmlElement) -> bool:
    return bool(el.xpath(".//pre|.//code"))


def title_alignment_ok(cleaned_root: html.HtmlElement, md: str) -> bool:
    # Compare first MD H1 with HTML h1 or title
    m = re.search(r"^#\s+(.+)$", md, flags=re.MULTILINE)
    md_title = m.group(1).strip() if m else None
    h1_nodes = cleaned_root.xpath(".//h1")
    h1 = h1_nodes[0].text_content().strip() if h1_nodes else None
    if md_title and h1:
        return _fuzzy_similar(md_title, h1)
    return True


def _fuzzy_similar(a: str, b: str) -> bool:
    a, b = a.lower(), b.lower()
    if a == b:
        return True
    # token-based
    at = set(a.split())
    bt = set(b.split())
    inter = len(at & bt)
    return inter >= max(1, min(len(at), len(bt)) // 2)


def evaluate(md: str, cleaned_root: Optional[html.HtmlElement], min_coverage: float = 0.6) -> HeuristicReport:
    if cleaned_root is None:
        # External provider — run lighter checks
        s = strip_md_syntax(md)
        lang_ok = True
        return HeuristicReport(
            coverage=1.0 if s else 0.0,
            title_ok=True,
            tables_ok=True,
            code_ok=True,
            lists_ok=True,
            language_ok=lang_ok,
        )

    html_text = _visible_text(cleaned_root)
    md_text = strip_md_syntax(md)
    cov = (len(md_text) / max(1, len(html_text))) if html_text else (1.0 if md_text else 0.0)

    want_tables = contains_tables(cleaned_root)
    want_code = contains_code(cleaned_root)
    html_list_count = count_list_items(cleaned_root)
    md_list_count = md.count("\n- ") + md.count("\n* ") + md.count("\n1. ")

    title_ok = title_alignment_ok(cleaned_root, md)
    tables_ok = (not want_tables) or md_has_tables(md)
    code_ok = (not want_code) or md_has_code_blocks(md)
    lists_ok = True
    if html_list_count >= 5:
        # Allow 30% variance
        lists_ok = md_list_count >= max(1, int(0.7 * html_list_count))

    # Language consistency (best-effort)
    language_ok = True
    try:
        lang_html = detect_lang(html_text) if html_text else None
        lang_md = detect_lang(md_text) if md_text else None
        if lang_html and lang_md and lang_html != lang_md:
            language_ok = False
    except Exception:
        language_ok = True

    return HeuristicReport(
        coverage=cov,
        title_ok=title_ok,
        tables_ok=tables_ok,
        code_ok=code_ok,
        lists_ok=lists_ok,
        language_ok=language_ok,
    )

