from __future__ import annotations

from lxml import html


def pick_best_candidate(doc: html.HtmlElement) -> html.HtmlElement:
    """Very light Readability-like heuristic: choose the element with max text length among main/article/section/body divs.
    Conservative to avoid over-pruning.
    """
    candidates = doc.xpath("//main | //article | //section | //body | /html/body/div")
    best = None
    best_len = 0
    for el in candidates:
        text = " ".join(el.text_content().split())
        L = len(text)
        if L > best_len:
            best = el
            best_len = L
    return best or (doc.find(".//body") or doc)
