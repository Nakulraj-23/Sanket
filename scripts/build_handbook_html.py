"""Build docs/CANDIDATE_HANDBOOK.html (and optionally the PDF) from docs/CANDIDATE_HANDBOOK.md.

Run:
    .venv/bin/python scripts/build_handbook_html.py          # HTML only
    .venv/bin/python scripts/build_handbook_html.py --pdf    # HTML, then an A4 PDF with page numbers

What it does, in order:
1. converts the Markdown with the `markdown` package (tables, code blocks, heading ids, table of contents);
2. turns every question in the question bank (an h4 inside the "question bank" h2) into a click-to-open <details>;
3. wraps every table so it scrolls sideways on a phone instead of widening the page;
4. inlines the CSS (screen, dark mode, print) and a tiny script, so the file needs nothing else;
5. with --pdf, prints the HTML with the pre-installed Chromium through Node's `require('playwright')`
   (from web/node_modules), with every answer opened first.
"""
import html
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs" / "CANDIDATE_HANDBOOK.md"
TARGET = ROOT / "docs" / "CANDIDATE_HANDBOOK.html"
PDF = ROOT / "docs" / "CANDIDATE_HANDBOOK.pdf"
BANK_TITLE = "question bank"  # text inside the h2 that holds the questions (case-insensitive)
TITLE = "SANKET candidate handbook"

CSS = """
:root { --ink:#1b2130; --muted:#586174; --line:#d8dde6; --accent:#1d5cb8; --bg:#ffffff; --soft:#f3f5f9;
  --mark:#fff2b3; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --ink:#e6e9ef; --muted:#a3abba; --line:#353c4a; --accent:#82b2ff;
    --bg:#14171d; --soft:#1e222b; --mark:#5a4a00; }
}
:root[data-theme="dark"] { --ink:#e6e9ef; --muted:#a3abba; --line:#353c4a; --accent:#82b2ff;
  --bg:#14171d; --soft:#1e222b; --mark:#5a4a00; }
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font: 17px/1.6 -apple-system, "Segoe UI", Roboto, "Noto Sans", "Noto Sans Devanagari", Arial, sans-serif; }
main { max-width: 880px; margin: 0 auto; padding: 24px 16px 96px; }
h1 { font-size: 2rem; line-height: 1.25; margin: 0.4em 0; }
h2 { font-size: 1.5rem; line-height: 1.3; margin-top: 2.4em; padding-top: 0.6em; border-top: 2px solid var(--line); }
h3 { font-size: 1.18rem; margin-top: 1.8em; }
h4 { font-size: 1.02rem; margin-top: 1.4em; }
a { color: var(--accent); overflow-wrap: anywhere; }
p, li, td, th { overflow-wrap: break-word; }
code { font: 0.87em/1.45 ui-monospace, Menlo, Consolas, monospace; background: var(--soft);
  padding: 0.1em 0.3em; border-radius: 4px; overflow-wrap: anywhere; }
pre { background: var(--soft); padding: 12px; border-radius: 6px; overflow-x: auto; max-width: 100%; }
pre code { padding: 0; background: none; overflow-wrap: normal; white-space: pre; }
.table-wrap { overflow-x: auto; margin: 1em 0; max-width: 100%; }
table { border-collapse: collapse; width: 100%; font-size: 0.92rem; }
th, td { border: 1px solid var(--line); padding: 6px 8px; text-align: left; vertical-align: top; }
th { background: var(--soft); }
hr { border: 0; border-top: 1px solid var(--line); margin: 2em 0; }
strong { font-weight: 650; }
nav.toc { background: var(--soft); border-radius: 8px; padding: 10px 16px; margin: 1em 0 2em; }
nav.toc summary { cursor: pointer; font-weight: 650; padding: 4px 0; }
nav.toc ul { margin: 0.2em 0; padding-left: 1.2em; }
nav.toc > details > div > .toc > ul { padding-left: 0.6em; }
nav.toc li { margin: 0.15em 0; }
details.q { border: 1px solid var(--line); border-radius: 6px; margin: 8px 0; padding: 0 12px; background: var(--bg); }
details.q > summary { cursor: pointer; font-weight: 650; padding: 10px 0; list-style-position: outside; }
details.q[open] > summary { border-bottom: 1px solid var(--line); margin-bottom: 8px; }
.tools { display: flex; gap: 8px; flex-wrap: wrap; margin: 8px 0 16px; }
.tools button, .theme button { font: inherit; font-size: 0.9rem; padding: 6px 12px; border: 1px solid var(--line);
  background: var(--soft); color: var(--ink); border-radius: 6px; cursor: pointer; }
.meta { color: var(--muted); font-size: 0.9rem; }
.top-link { position: fixed; right: 12px; bottom: 12px; background: var(--soft); color: var(--ink);
  border: 1px solid var(--line); border-radius: 18px; padding: 6px 12px; font-size: 0.85rem; text-decoration: none; }
@media (max-width: 480px) {
  body { font-size: 16px; }
  h1 { font-size: 1.6rem; }
  h2 { font-size: 1.3rem; }
  th, td { padding: 5px 6px; }
}
@media print {
  :root, :root[data-theme="dark"] { --ink:#000; --muted:#333; --line:#999; --bg:#fff; --soft:#f2f2f2;
    --accent:#000; --mark:#eee; }
  @page { size: A4; margin: 16mm 14mm 18mm 14mm; }
  body { font-size: 10.5pt; line-height: 1.45; }
  main { max-width: none; padding: 0; }
  h2 { break-before: page; page-break-before: always; border-top: 0; margin-top: 0; }
  h3, h4, summary { break-after: avoid; page-break-after: avoid; }
  tr, pre, details.q { break-inside: avoid; page-break-inside: avoid; }
  .table-wrap { overflow: visible; }
  table { font-size: 8.8pt; width: 100%; }
  td code, th code { word-break: break-all; }
  .tools, .theme, .top-link, nav.toc { display: none; }
  details.q { border: 0; padding: 0; margin: 0 0 6px; }
  details.q > summary { list-style: none; padding: 4px 0; }
  details.q > summary::-webkit-details-marker { display: none; }
  a { text-decoration: none; color: #000; }
  pre code { white-space: pre-wrap; }
}
"""

SCRIPT = """
function setAll(open) { document.querySelectorAll('details.q').forEach(function (d) { d.open = open; }); }
window.addEventListener('beforeprint', function () { setAll(true); });
function setTheme(t) {
  try { if (t) { document.documentElement.setAttribute('data-theme', t); localStorage.setItem('hb-theme', t); }
        else { document.documentElement.removeAttribute('data-theme'); localStorage.removeItem('hb-theme'); } }
  catch (e) { if (t) document.documentElement.setAttribute('data-theme', t); }
}
try { var saved = localStorage.getItem('hb-theme'); if (saved) document.documentElement.setAttribute('data-theme', saved); }
catch (e) {}
"""


def convert(md_text: str) -> tuple[str, str]:
    """Markdown to HTML; returns (body, table of contents for h2 and h3)."""
    md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists", "toc"],
                           extension_configs={"toc": {"toc_depth": "2-3"}})
    return md.convert(md_text), md.toc


def collapse_questions(body: str) -> tuple[str, int]:
    """Inside the question bank, wrap each <h4> question and its answer in <details>."""
    found = re.search(r'<h2 id="[^"]+">[^<]*' + BANK_TITLE, body, re.IGNORECASE)
    if found is None:
        raise SystemExit("question bank heading not found")
    start = found.start()
    end = body.find("<h2", start + 4)
    end = len(body) if end < 0 else end
    bank = body[start:end]
    pattern = re.compile(r'<h4 id="([^"]+)">(.*?)</h4>(.*?)(?=<h4 |<h3 |\Z)', re.DOTALL)
    count = len(pattern.findall(bank))

    def wrap(m: re.Match) -> str:
        return (f'<details class="q" id="{m.group(1)}"><summary>{m.group(2)}</summary>'
                f"{m.group(3).strip()}</details>\n")

    bank = pattern.sub(wrap, bank)
    tools = ('<div class="tools"><button type="button" onclick="setAll(true)">Open all answers</button>'
             '<button type="button" onclick="setAll(false)">Close all answers</button></div>')
    bank = bank.replace("</h2>", "</h2>" + tools, 1)
    return body[:start] + bank + body[end:], count


def wrap_tables(body: str) -> str:
    """Let wide tables scroll inside their own box on small screens."""
    return body.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")


def build_html() -> tuple[Path, int]:
    """Write the HTML file next to the Markdown; return its path and the number of questions."""
    body, toc = convert(SOURCE.read_text(encoding="utf-8"))
    body, n_questions = collapse_questions(body)
    body = wrap_tables(body)
    page = (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{html.escape(TITLE)}</title>\n<style>{CSS}</style>\n<script>{SCRIPT}</script>\n"
        "</head>\n<body>\n<main id=\"top\">\n"
        "<p class=\"meta\">Generated from docs/CANDIDATE_HANDBOOK.md by scripts/build_handbook_html.py. "
        f"{n_questions} questions; click one to open its answer. Printing opens every answer and starts each "
        "section on a new page.</p>\n"
        "<p class=\"theme meta\">Theme: <button type=\"button\" onclick=\"setTheme('light')\">Light</button> "
        "<button type=\"button\" onclick=\"setTheme('dark')\">Dark</button> "
        "<button type=\"button\" onclick=\"setTheme(null)\">System</button></p>\n"
        f"<nav class=\"toc\"><details open><summary>Contents</summary><div>{toc}</div></details></nav>\n"
        f"{body}\n</main>\n<a class=\"top-link\" href=\"#top\">Top</a>\n</body>\n</html>\n"
    )
    TARGET.write_text(page, encoding="utf-8")
    return TARGET, n_questions


def find_chromium() -> str | None:
    """The pre-installed Chromium under PLAYWRIGHT_BROWSERS_PATH (default /opt/pw-browsers), if any."""
    root = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"))
    if not root.exists():
        return None
    for d in sorted(root.iterdir()):
        exe = d / "chrome-linux64" / "chrome"
        if re.fullmatch(r"chromium-\d+", d.name) and exe.exists():
            return str(exe)
    return None


PDF_JS = r"""
const { chromium } = require('playwright');
(async () => {
  const [src, out, exe] = process.argv.slice(2);
  const browser = await chromium.launch({ executablePath: exe || undefined, args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.goto('file://' + src, { waitUntil: 'load' });
  await page.evaluate(() => document.querySelectorAll('details').forEach((d) => { d.open = true; }));
  await page.emulateMedia({ media: 'print' });
  await page.pdf({
    path: out, format: 'A4', printBackground: true, preferCSSPageSize: true,
    displayHeaderFooter: true,
    headerTemplate: '<div></div>',
    footerTemplate: '<div style="font-size:8px;width:100%;text-align:center;color:#555;">' +
      'SANKET candidate handbook &middot; page <span class="pageNumber"></span> of <span class="totalPages"></span></div>',
    margin: { top: '16mm', bottom: '18mm', left: '14mm', right: '14mm' },
  });
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
"""


def build_pdf() -> Path:
    """Print the HTML to an A4 PDF with page numbers, using Node + playwright from web/node_modules."""
    node_modules = ROOT / "web" / "node_modules"
    if not (node_modules / "playwright").exists():
        raise SystemExit("web/node_modules/playwright is missing: run `cd web && npm install` first")
    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "print_pdf.js"
        script.write_text(PDF_JS, encoding="utf-8")
        env = {**os.environ, "NODE_PATH": str(node_modules)}
        cmd = ["node", str(script), str(TARGET), str(PDF), find_chromium() or ""]
        subprocess.run(cmd, check=True, env=env, cwd=tmp)
    return PDF


if __name__ == "__main__":
    path, n = build_html()
    print(json.dumps({"html": str(path), "questions": n}))
    if "--pdf" in sys.argv[1:]:
        print(json.dumps({"pdf": str(build_pdf())}))
