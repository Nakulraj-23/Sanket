"""Build docs/SANKET_STUDY_GUIDE.pdf from docs/SANKET_STUDY_GUIDE.md.

Run (needs Python-Markdown, Node with `playwright`, the pre-installed Chromium and poppler's pdftotext):
    .venv/bin/python scripts/build_study_pdf.py [--html-out some.html]

What it does, aiming at maximum compatibility:
1. Markdown -> one self-contained HTML. No JavaScript, no web fonts, no <details>: every answer is visible.
2. System fonts only (DejaVu Sans / DejaVu Sans Mono, with FreeSans for Devanagari), all TrueType, so they embed
   as TrueType/CID fonts and not as Type 3.
3. Title page, clickable table of contents (page numbers are filled in by a second pass that finds each heading
   in the first PDF), A4, 18 mm margins, "page N of M" in the footer, PDF outline (bookmarks) and tagged PDF.
4. Code blocks wrap, tables fit the page width, headings are kept with the text that follows them.
"""
from __future__ import annotations

import argparse
import html
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "docs" / "SANKET_STUDY_GUIDE.md"
PDF = ROOT / "docs" / "SANKET_STUDY_GUIDE.pdf"
TITLE = "SANKET study guide"

CSS = r"""
@page { size: A4; margin: 18mm; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; background: #fff; color: #1a1a1a;
  font-family: "DejaVu Sans", "FreeSans", sans-serif; font-size: 9pt; line-height: 1.45; }
.dev { font-family: "FreeSans", "DejaVu Sans", sans-serif; }
h1, h2, h3, h4 { line-height: 1.25; break-after: avoid; break-inside: avoid; page-break-after: avoid; }
h2 { font-size: 15pt; margin: 0 0 8pt; padding-bottom: 3pt; border-bottom: 1.5pt solid #1f4e79;
  color: #1f4e79; break-before: page; page-break-before: always; }
h3 { font-size: 11.5pt; margin: 14pt 0 5pt; color: #1f4e79; }
h4 { font-size: 9.5pt; margin: 10pt 0 3pt; color: #222; }
p { margin: 0 0 5pt; orphans: 3; widows: 3; overflow-wrap: anywhere; }
ul, ol { margin: 0 0 6pt; padding-left: 16pt; }
li { margin: 0 0 2pt; overflow-wrap: anywhere; }
li.chk { list-style: none; margin-left: -14pt; }
a { color: #0b4f9c; text-decoration: none; overflow-wrap: anywhere; }
hr { display: none; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 0.86em; background: #f0f2f5;
  padding: 0 2pt; border-radius: 2pt; overflow-wrap: anywhere; word-break: break-word; }
pre { font-family: "DejaVu Sans Mono", monospace; font-size: 7.6pt; line-height: 1.35; background: #f5f6f8;
  border: 0.6pt solid #cfd4da; border-radius: 3pt; padding: 5pt 6pt; margin: 4pt 0 7pt;
  white-space: pre-wrap; overflow-wrap: anywhere; word-break: break-word; break-inside: auto; }
pre code { background: none; padding: 0; font-size: inherit; }
table { width: 100%; border-collapse: collapse; margin: 4pt 0 8pt; font-size: 7.8pt; line-height: 1.35;
  table-layout: auto; }
th, td { border: 0.6pt solid #b8c0c8; padding: 2.5pt 4pt; vertical-align: top; text-align: left;
  overflow-wrap: anywhere; word-break: break-word; }
th { background: #e6eef6; }
tr { break-inside: avoid; page-break-inside: avoid; }
thead { display: table-header-group; }
blockquote { margin: 4pt 0; padding: 2pt 8pt; border-left: 2.5pt solid #9ab; color: #333; }
.title-page { height: 245mm; display: flex; flex-direction: column; justify-content: center;
  break-after: page; page-break-after: always; }
.title-page h1 { font-size: 30pt; color: #1f4e79; margin: 0 0 10pt; border-bottom: 3pt solid #1f4e79; padding-bottom: 8pt; }
.title-page p { font-size: 11pt; }
.title-page table { font-size: 10pt; margin-top: 14pt; }
.toc-page { break-after: page; page-break-after: always; }
.toc-page h2 { break-before: auto; page-break-before: auto; }
.toc ul { list-style: none; padding-left: 0; margin: 0; column-count: 1; }
.toc li { margin: 0; padding: 1.2pt 0; }
.toc li.l2 { font-weight: bold; margin-top: 4pt; font-size: 9pt; }
.toc li.l3 { padding-left: 14pt; font-size: 8.3pt; }
.toc a { display: flex; color: #1a1a1a; }
.toc a .t { flex: 1 1 auto; }
.toc a .n { flex: 0 0 auto; padding-left: 6pt; color: #555; }
.s13 { font-size: 8.4pt; line-height: 1.35; }
.s13 li { margin-bottom: 1pt; }
.s13 p { margin-bottom: 3pt; }
.s13 h3 { margin-top: 6pt; }
"""

DEV_RE = re.compile(r"[ऀ-ॿ]+")


def slugify(value: str, separator: str = "-") -> str:
    """Same rule as GitHub's anchors, so the Markdown table of contents also works on GitHub."""
    value = value.replace("`", "").strip().lower()
    value = re.sub(r"[^\w\- ]", "", value, flags=re.U)
    return value.replace(" ", separator)


def split_md(text: str) -> tuple[str, str]:
    """(front matter before the Markdown table of contents, everything after it)."""
    m = re.search(r"<!-- toc:start -->.*?<!-- toc:end -->\n?", text, flags=re.S)
    if not m:
        raise SystemExit("toc markers not found in the Markdown file")
    return text[: m.start()], text[m.end():]


def convert(md_text: str) -> tuple[str, list[dict]]:
    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "sane_lists", "toc"],
        extension_configs={"toc": {"slugify": slugify, "permalink": False}},
    )
    out = md.convert(md_text)
    # task-list boxes (section 13): "[ ]" at the start of a list item becomes a drawn box
    out = re.sub(r"<li>\[ \] ", '<li class="chk">☐ ', out)
    return out, md.toc_tokens


def flatten(tokens: list[dict], levels=(2, 3)) -> list[dict]:
    res: list[dict] = []
    for t in tokens:
        if t["level"] in levels:
            res.append({"level": t["level"], "id": t["id"], "name": re.sub(r"<[^>]+>", "", html.unescape(t["name"]))})
        res.extend(flatten(t.get("children", []), levels))
    return res


def mark_devanagari(body: str) -> str:
    """Wrap Devanagari runs in a span (outside tags) so they use the Devanagari-capable font."""
    parts = re.split(r"(<[^>]+>)", body)
    for i, p in enumerate(parts):
        if not p.startswith("<"):
            parts[i] = DEV_RE.sub(lambda m: f'<span class="dev">{m.group(0)}</span>', p)
    return "".join(parts)


def toc_html(entries: list[dict], pages: dict[str, int] | None) -> str:
    rows = []
    for e in entries:
        n = f'<span class="n">{pages[e["id"]]}</span>' if pages and e["id"] in pages else ""
        rows.append(
            f'<li class="l{e["level"]}"><a href="#{e["id"]}"><span class="t">{html.escape(e["name"])}</span>{n}</a></li>'
        )
    return '<div class="toc-page toc"><h2>Table of contents</h2><ul>' + "".join(rows) + "</ul></div>"


def build_html(pages: dict[str, int] | None = None) -> str:
    text = MD.read_text(encoding="utf-8")
    front, rest = split_md(text)
    front_html, _ = convert(front)
    body, tokens = convert(rest)
    entries = flatten(tokens)
    # the title page holds the front matter; the heading "SANKET study guide" is its h1
    # section 13 gets a compact style so that it stays on one page
    body = re.sub(r'(<h2 id="13-[^"]*">)', r'<div class="s13">\1', body)
    if '<div class="s13">' in body:
        body = body + "</div>"
    page = (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{TITLE}</title><style>{CSS}</style></head><body>"
        f'<div class="title-page">{front_html}'
        "<p>SANKET-only edition of <code>docs/CANDIDATE_HANDBOOK.md</code>. Every answer is visible. "
        "Use the table of contents on the next page (each line is a link) or the PDF bookmarks.</p></div>"
        f"{toc_html(entries, pages)}{body}</body></html>"
    )
    return mark_devanagari(page), entries


PDF_JS = r"""
const { chromium } = require('playwright');
(async () => {
  const [src, out, exe] = process.argv.slice(2);
  const browser = await chromium.launch({ executablePath: exe || undefined, args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.goto('file://' + src, { waitUntil: 'load' });
  await page.emulateMedia({ media: 'print' });
  await page.pdf({
    path: out, format: 'A4', printBackground: true, preferCSSPageSize: true,
    displayHeaderFooter: true, outline: true, tagged: true,
    headerTemplate: '<span></span>',
    footerTemplate: '<div style="font-family:DejaVu Sans,sans-serif;font-size:7.5px;width:100%;text-align:center;color:#555;">' +
      'SANKET study guide &middot; page <span class="pageNumber"></span> of <span class="totalPages"></span></div>',
    margin: { top: '18mm', bottom: '18mm', left: '18mm', right: '18mm' },
  });
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
"""


def find_chromium() -> str:
    root = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"))
    if root.exists():
        for d in sorted(root.iterdir()):
            exe = d / "chrome-linux64" / "chrome"
            if re.fullmatch(r"chromium-\d+", d.name) and exe.exists():
                return str(exe)
    return ""


def print_pdf(html_text: str, out: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_p = Path(tmp)
        (tmp_p / "guide.html").write_text(html_text, encoding="utf-8")
        (tmp_p / "print_pdf.js").write_text(PDF_JS, encoding="utf-8")
        env = dict(os.environ)
        nm = ROOT / "web" / "node_modules"
        if (nm / "playwright").exists():
            env["NODE_PATH"] = str(nm) + os.pathsep + env.get("NODE_PATH", "")
        subprocess.run(
            ["node", str(tmp_p / "print_pdf.js"), str(tmp_p / "guide.html"), str(out), find_chromium()],
            check=True, env=env, cwd=tmp,
        )


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("`", "")).strip().lower()


def find_pages(entries: list[dict], pdf: Path) -> dict[str, int]:
    """Page of each heading, found in the first PDF's text (first match after the table of contents)."""
    txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    pages = txt.split("\f")
    flat = [norm(p) for p in pages]
    found: dict[str, int] = {}
    start = 2  # skip the title page and the table of contents (0-based index of the first body page candidate)
    for i, p in enumerate(flat):
        if "table of contents" in p[:200]:
            start = i + 1
    last = start
    for e in entries:
        for size in (45, 24, 14):  # shorter keys if a long heading wraps in the text layer
            key = norm(e["name"])[:size]
            hit = next((i for i in range(last, len(flat)) if key in flat[i]), None)
            if hit is not None:
                found[e["id"]] = hit + 1
                last = hit
                break
    return found


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html-out", help="also write the self-contained HTML here")
    args = ap.parse_args()
    page, entries = build_html()
    print_pdf(page, PDF)  # pass 1: find the heading pages
    pages = find_pages(entries, PDF)
    page, entries = build_html(pages)  # pass 2: same layout, with page numbers in the table of contents
    print_pdf(page, PDF)
    if args.html_out:
        Path(args.html_out).write_text(page, encoding="utf-8")
    missing = [e["name"] for e in entries if e["id"] not in pages]
    print(f"wrote {PDF} ({PDF.stat().st_size} bytes); headings without a page number: {len(missing)}")
    for m in missing:
        print("  missing:", m, file=sys.stderr)


if __name__ == "__main__":
    main()
