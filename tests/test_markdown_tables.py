from lxml import html

from webtomd.normalize.html_cleaner import to_clean_html
from webtomd.convert.html_to_markdown import to_markdown


def test_table_converts_to_pipe_table():
    src = """
    <html><body>
      <article>
        <table>
          <thead><tr><th>A</th><th>B</th></tr></thead>
          <tbody>
            <tr><td>1</td><td>2</td></tr>
            <tr><td>3</td><td>4</td></tr>
          </tbody>
        </table>
      </article>
    </body></html>
    """
    root = to_clean_html(src)
    md = to_markdown(root)
    assert "| A | B |" in md
    assert "---" in md
    assert "| 1 | 2 |" in md

