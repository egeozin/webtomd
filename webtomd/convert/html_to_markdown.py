from __future__ import annotations

from typing import Optional
from lxml import html, etree
from markdownify import MarkdownConverter


class WebToMdConverter(MarkdownConverter):
    def _el_text(self, el) -> str:
        # Works for both BeautifulSoup Tag and lxml elements
        get_text = getattr(el, "get_text", None)
        if callable(get_text):
            # Join with spaces and strip extra whitespace
            text = " ".join(list(el.stripped_strings))
        else:
            # Fallbacks for other element types
            text = getattr(el, "text", "") or ""
        return " ".join(text.split())

    def convert_table(self, el, text, parent_tags):  # pipe tables
        # Build header from thead if present; otherwise fall back to first row
        rows = []
        header = []

        thead = el.find("thead")
        if thead is not None:
            tr = thead.find("tr")
            if tr is not None:
                header = [self._el_text(td) for td in tr.find_all(["th", "td"]) or []]

        # Gather all body rows (all <tr> not under <thead>)
        trs = []
        for tr in el.find_all("tr"):
            # Skip header rows
            if tr.find_parent("thead") is not None:
                continue
            trs.append(tr)

        # If header missing, use the first row as header
        if not header and trs:
            first = trs.pop(0)
            header = [self._el_text(td) for td in first.find_all(["th", "td"]) or []]

        # Extract body cell values
        for tr in trs:
            cells = tr.find_all("td")
            if not cells:
                cells = tr.find_all("th")
            if not cells:
                continue
            rows.append([self._el_text(td) for td in cells])

        if not header:
            # Fallback to default behavior if we can't infer a header
            return super().convert_table(el, text, parent_tags)

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

    def convert_pre(self, el, text, parent_tags):  # code blocks
        # Try to detect language from a nested <code class="language-...">
        lang = None
        code_el = None
        # Prefer a direct child <code> when present
        if getattr(el, "contents", None) and len(el.contents) == 1:
            child = el.contents[0]
            if getattr(child, "name", "").lower() == "code":
                code_el = child
        if code_el is None:
            code_el = el.find("code")
        if code_el is not None:
            classes = code_el.get("class", []) or []
            for token in classes:
                if token.startswith("language-"):
                    lang = token.split("-", 1)[-1]
                    break

        fence = "```"
        body = (text or "").rstrip("\n")
        head = f"{fence}{lang or ''}\n" if lang else f"{fence}\n"
        return f"\n{head}{body}\n{fence}\n\n"

    def convert_hr(self, el, text, parent_tags):
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
