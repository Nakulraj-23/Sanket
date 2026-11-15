"""Build docs/INTERVIEW_GUIDE.html from docs/INTERVIEW_GUIDE.md (one self-contained file).

Run: .venv/bin/python scripts/build_guide_html.py
What it does, in order:
1. converts the Markdown with the `markdown` package (tables, code blocks, heading ids, table of contents);
2. turns each question in the question bank (an h4 heading) into a click-to-open <details> block;
3. wraps every table so it scrolls sideways on a phone instead of widening the page;
4. inlines the CSS (screen and print) so the file needs nothing else to display.
"""
import html
import re
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs" / "INTERVIEW_GUIDE.md"
TARGET = ROOT / "docs" / "INTERVIEW_GUIDE.html"
BANK_TITLE = "Question bank"  # text of the h2 that holds the questions

CSS = """
:root { --ink:#1d2330; --muted:#5b6475; --line:#d9dee7; --accent:#1f5fbf; --bg:#ffffff; --soft:#f4f6fa; }
@media (prefers-color-scheme: dark) {
  :root { --ink:#e6e9ef; --muted:#a3abba; --line:#353c4a; --accent:#7fb0ff; --bg:#14171d; --soft:#1d212a; }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font: 17px/1.6 -apple-system, "Segoe UI", Roboto, "Noto Sans", Arial, sans-serif; }
main { max-width: 860px; margin: 0 auto; padding: 24px 16px 80px; }
h1 { font-size: 1.9rem; line-height: 1.25; margin: 0.4em 0; }
h2 { font-size: 1.45rem; margin-top: 2.2em; padding-top: 0.6em; border-top: 2px solid var(--line); }
h3 { font-size: 1.15rem; margin-top: 1.6em; }
h4 { font-size: 1rem; }
a { color: var(--accent); overflow-wrap: anywhere; }
p, li { overflow-wrap: break-word; }
code { font: 0.88em/1.4 ui-monospace, Menlo, Consolas, monospace; background: var(--soft);
  padding: 0.1em 0.3em; border-radius: 4px; overflow-wrap: anywhere; }
pre { background: var(--soft); padding: 12px; border-radius: 6px; overflow-x: auto; }
pre code { padding: 0; background: none; overflow-wrap: normal; }
.table-wrap { overflow-x: auto; margin: 1em 0; }
table { border-collapse: collapse; width: 100%; font-size: 0.93rem; }
th, td { border: 1px solid var(--line); padding: 6px 8px; text-align: left; vertical-align: top; }
th { background: var(--soft); }
hr { border: 0; border-top: 1px solid var(--line); margin: 2em 0; }
nav.toc { background: var(--soft); border-radius: 8px; padding: 12px 16px; margin: 1em 0 2em; }
nav.toc ul { margin: 0.2em 0; padding-left: 1.2em; }
details.q { border: 1px solid var(--line); border-radius: 6px; margin: 8px 0; padding: 0 12px; }
details.q > summary { cursor: pointer; font-weight: 600; padding: 10px 0; list-style-position: outside; }
details.q[open] > summary { border-bottom: 1px solid var(--line); margin-bottom: 8px; }
.tools { display: flex; gap: 8px; flex-wrap: wrap; margin: 8px 0 16px; }
.tools button { font: inherit; font-size: 0.9rem; padding: 6px 12px; border: 1px solid var(--line);
  background: var(--soft); color: var(--ink); border-radius: 6px; cursor: pointer; }
.meta { color: var(--muted); font-size: 0.9rem; }
@media print {
  :root { --ink:#000; --muted:#333; --line:#999; --bg:#fff; --soft:#f2f2f2; --accent:#000; }
  body { font-size: 11pt; }
  main { max-width: none; padding: 0; }
  h2 { break-before: page; page-break-before: always; border-top: 0; }
  h3, h4, summary { break-after: avoid; page-break-after: avoid; }
  table, pre, details.q { break-inside: avoid; page-break-inside: avoid; }
  .tools, nav.toc { display: none; }
  details.q { border: 0; padding: 0; }
  a { text-decoration: none; }
}
"""

SCRIPT = """
function setAll(open) { document.querySelectorAll('details.q').forEach(d => { d.open = open; }); }
window.addEventListener('beforeprint', () => setAll(true));
"""


def convert(md_text: str) -> tuple[str, str]:
    """Markdown to HTML; returns (body, table of contents)."""
    md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists", "toc"],
                           extension_configs={"toc": {"toc_depth": "2-2"}})
    body = md.convert(md_text)
    return body, md.toc


def collapse_questions(body: str) -> str:
    """Inside the question bank, wrap each <h4> question and its answer in <details>."""
    found = re.search(rf'<h2 id="[^"]+">[^<]*{BANK_TITLE}', body)
    if found is None:
        raise SystemExit("question bank heading not found")
    start = found.start()
    end = body.find("<h2", start + 4)
    end = len(body) if end < 0 else end
    bank = body[start:end]
    pattern = re.compile(r'<h4 id="([^"]+)">(.*?)</h4>(.*?)(?=<h4 |<h3 |\Z)', re.DOTALL)

    def wrap(m: re.Match) -> str:
        return (f'<details class="q" id="{m.group(1)}"><summary>{m.group(2)}</summary>'
                f"{m.group(3).strip()}</details>\n")

    bank = pattern.sub(wrap, bank)
    tools = ('<div class="tools"><button type="button" onclick="setAll(true)">Open all answers</button>'
             '<button type="button" onclick="setAll(false)">Close all answers</button></div>')
    bank = bank.replace("</h2>", "</h2>" + tools, 1)
    return body[:start] + bank + body[end:]


def wrap_tables(body: str) -> str:
    """Let wide tables scroll inside their own box on small screens."""
    return body.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")


def build() -> Path:
    """Write the HTML file next to the Markdown and return its path."""
    body, toc = convert(SOURCE.read_text(encoding="utf-8"))
    body = wrap_tables(collapse_questions(body))
    title = "SANKET interview guide"
    page = (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{html.escape(title)}</title>\n<style>{CSS}</style>\n</head>\n<body>\n<main>\n"
        f"<p class=\"meta\">Generated from docs/INTERVIEW_GUIDE.md by scripts/build_guide_html.py. "
        "Print it: every section starts on a new page and all answers open.</p>\n"
        f"<nav class=\"toc\"><strong>Contents</strong>{toc}</nav>\n{body}\n</main>\n"
        f"<script>{SCRIPT}</script>\n</body>\n</html>\n"
    )
    TARGET.write_text(page, encoding="utf-8")
    return TARGET


if __name__ == "__main__":
    print(build())
