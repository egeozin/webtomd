from __future__ import annotations

from typing import Optional
from lxml import html, etree
from markdownify import MarkdownConverter


class WebToMdConverter(MarkdownConverter):
    def _el_text(self, el) -> str:
        from lxml.html import HtmlElement
        if isinstance(el, HtmlElement):
            text = el.text_content()
        else:
            text = str(el.text or "")
        return " ".join(text.split())

    def convert_table(self, el, text, convert_as_inline):  # pipe tables
        # Collect rows
        rows = []
        header = []
        thead = el.find(".//thead")
        if thead is not None:
            tr = thead.find(".//tr")
            if tr is not None:
                header = [self._el_text(td) for td in tr.findall(".//th") or tr.findall(".//td")]
        tbodies = el.findall(".//tbody")
        if header and not tbodies:
            # body rows may be direct tr children
            pass
        # Gather all tr in order, excluding thead if we already read header
        trs = []
        for child in el.iter():
            if getattr(child, "tag", "").lower() == "tr":
                trs.append(child)
        # Build header if not set from thead: use first row
        if not header and trs:
            first = trs[0]
            header = [self._el_text(td) for td in first.findall(".//th") or first.findall(".//td")]
            trs = trs[1:]
        # Body rows
        for tr in trs:
            cells = tr.findall(".//td")
            if not cells:
                cells = tr.findall(".//th")
            if not cells:
                continue
            rows.append([self._el_text(td) for td in cells])
        if not header:
            # Fallback to plain text conversion
            return "\n" + self.convert(el, convert_as_inline=True) + "\n"
        n = len(header)
        sep = ["---"] * n
        def line(cells):
            return "| " + " | ".join(cells) + " |"
        parts = ["", line(header), line(sep)]
        for r in rows:
            if len(r) < n:
                r = r + [""] * (n - len(r))
            parts.append(line(r[:n]))
        parts.append("")
        return "\n".join(parts)

    def convert_pre(self, el, text, convert_as_inline):  # code blocks
        code_el = None
        if len(el) == 1 and getattr(el[0], "tag", "").lower() == "code":
            code_el = el[0]
        code_text = (code_el.text or "") if code_el is not None else (el.text or "")
        code_text = code_text.rstrip("\n")
        lang = None
        if code_el is not None:
            cls = code_el.attrib.get("class", "")
            for token in cls.split():
                if token.startswith("language-"):
                    lang = token.split("-", 1)[-1]
                    break
        fence = "```"
        head = f"{fence}{lang or ''}\n" if lang else f"{fence}\n"
        return f"\n{head}{code_text}\n{fence}\n\n"

    def convert_hr(self, el, text, convert_as_inline):
        return "\n---\n\n"


def _converter() -> WebToMdConverter:
    return WebToMdConverter(bullets="*", escape_asterisks=False, strip="\n")


def to_markdown(root: html.HtmlElement) -> str:
    # Clone the element into a standalone HTML string
    html_str = etree.tostring(root, encoding="unicode")
    conv = _converter()
    md = conv.convert(html_str)
    # Post-process spacing
    md = _post_process(md)
    return md


def _post_process(md: str) -> str:
    # Remove trailing spaces; collapse >=3 newlines to 2; ensure spacing around headings
    lines = [line.rstrip() for line in md.splitlines()]
    md2 = "\n".join(lines)
    while "\n\n\n" in md2:
        md2 = md2.replace("\n\n\n", "\n\n")
    return md2.strip() + "\n"
