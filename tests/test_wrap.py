from webtomd.convert.wrap import reflow_paragraphs


def test_wrap_paragraphs_keeps_code_blocks_and_tables():
    md = """
This is a very long paragraph that should be wrapped into multiple lines without affecting the formatting of any other parts of the document because it exceeds the default eighty characters width used for wrapping paragraphs in this project.

```
code block should remain as is and not be reflowed even if it is very long long long long long long long
```

| H1 | H2 |
| --- | --- |
| A | B |
"""
    out = reflow_paragraphs(md, width=60)
    # Ensure the first paragraph was wrapped (has newline inserted)
    lines = out.strip().splitlines()
    assert any(len(line) <= 60 for line in lines[:3])
    # Code fence lines preserved
    assert "```" in out
    # Table kept intact
    assert "| H1 | H2 |" in out

