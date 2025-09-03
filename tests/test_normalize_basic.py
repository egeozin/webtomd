from lxml import html

from webtomd.normalize.html_cleaner import to_clean_html


def test_normalize_removes_chrome_and_scripts():
    src = """
    <html><head><title>T</title><script>bad()</script></head>
    <body>
      <nav>menu</nav>
      <main>
        <article>
          Hello <span>world</span>!
          <div>Text in div</div>
          <script>alert(1)</script>
        </article>
      </main>
    </body></html>
    """
    root = to_clean_html(src)
    text = " ".join(root.text_content().split())
    assert "menu" not in text
    assert "alert(1)" not in text
    assert "Hello world !".replace(" ", "")[:5] in text.replace(" ", "")

