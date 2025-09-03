from __future__ import annotations

import textwrap


def reflow_paragraphs(md: str, width: int = 80) -> str:
    lines = md.splitlines()
    out = []
    in_code = False
    in_table = False
    buf = []

    def flush_buf():
        nonlocal buf
        if not buf:
            return
        para = " ".join([l.strip() for l in buf])
        wrapped = textwrap.fill(para, width=width)
        out.extend(wrapped.splitlines())
        buf = []

    for line in lines:
        if line.strip().startswith("```"):
            flush_buf()
            in_code = not in_code
            out.append(line)
            continue
        if in_code:
            out.append(line)
            continue
        if "|" in line:
            # crude table detection: keep as-is
            flush_buf()
            out.append(line)
            in_table = True if line.strip() else in_table
            continue
        if in_table and not line.strip():
            in_table = False
            out.append(line)
            continue
        if not line.strip():
            flush_buf()
            out.append("")
            continue
        if line.lstrip().startswith(("#", ">", "- ", "* ", "1. ")):
            flush_buf()
            out.append(line)
            continue
        buf.append(line)
    flush_buf()
    out.append("")
    return "\n".join(out)

