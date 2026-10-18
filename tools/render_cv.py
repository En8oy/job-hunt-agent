#!/usr/bin/env python3
"""Render an ATS-friendly PDF from a CV written in Markdown, using headless Chrome/Chromium.

    python3 tools/render_cv.py me/cv_en.md me/cv_es.md      # writes me/cv_en.pdf, me/cv_es.pdf
    python3 tools/render_cv.py --paper letter me/cv_en.md   # US Letter instead of A4
    python3 tools/render_cv.py --check                      # just report which browser will be used

Supports the Markdown subset described in .claude/skills/cv-review/references/cv-template.md:
headings, paragraphs, '-' bullets, **bold**, *italic*, [links](url) and '---' rules.
The output is deliberately plain (one column, real text, standard fonts, no tables or images)
because applicant tracking systems parse that reliably.
"""
import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BROWSERS = ["google-chrome-stable", "google-chrome", "chromium", "chromium-browser", "chrome", "msedge",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]

CSS = """
@page { size: %(paper)s; margin: 14mm 16mm; }
body { font-family: Arial, Helvetica, "Liberation Sans", sans-serif; font-size: 10pt; line-height: 1.35;
       color: #111; margin: 0; }
h1 { font-size: 18pt; margin: 0 0 2px; }
.contact h3 { font-size: 11.5pt; font-weight: normal; color: #333; margin: 0 0 6px; }
h2 { font-size: 11pt; text-transform: uppercase; letter-spacing: .04em; color: #1a3d63;
     border-bottom: 1px solid #1a3d63; padding-bottom: 2px; margin: 12px 0 6px; }
h3 { font-size: 10.5pt; margin: 8px 0 1px; }
p { margin: 2px 0 4px; }
ul { margin: 2px 0 5px; padding-left: 16px; }
li { margin-bottom: 2px; }
a { color: inherit; text-decoration: none; }
hr { display: none; }
.contact p { margin: 0; color: #333; }
"""


def find_browser():
    env = os.environ.get("CHROME")
    for cand in ([env] if env else []) + BROWSERS:
        path = shutil.which(cand) or (cand if os.path.isfile(cand) else None)
        if path:
            return path
    return None


def inline(text):
    s = html.escape(text, quote=False)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: f'<a href="{html.escape(m.group(2))}">{m.group(1)}</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    return s


def md_to_html(md):
    out, para, items = [], [], []
    contact_open = False

    def flush():
        nonlocal para, items
        if para:   # header lines keep their line breaks; body paragraphs reflow
            out.append(f"<p>{('<br>' if contact_open else ' ').join(inline(x) for x in para)}</p>")
            para = []
        if items:
            out.append("<ul>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ul>")
            items = []

    for raw in md.splitlines():
        line = raw.rstrip()
        m = re.match(r"^(#{1,3})\s+(.*)$", line)
        if m:
            flush()
            level = len(m.group(1))
            if contact_open and level <= 2:
                out.append("</div>")
                contact_open = False
            out.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
            if level == 1:
                out.append('<div class="contact">')   # header block until the first section
                contact_open = True
            continue
        if re.match(r"^\s*(---+|\*\*\*+)\s*$", line):
            flush()
            if contact_open:
                out.append("</div>")
                contact_open = False
            out.append("<hr>")
        elif re.match(r"^\s*[-*+]\s+", line):
            if para:
                flush()
            items.append(re.sub(r"^\s*[-*+]\s+", "", line))
        elif not line.strip():
            flush()
        else:
            if items:
                flush()
            para.append(line.strip())
    flush()
    if contact_open:
        out.append("</div>")
    return "\n".join(out)


def render(md_path, browser, paper):
    md_path = Path(md_path)
    title = md_path.stem
    body = md_to_html(md_path.read_text(encoding="utf-8"))
    lang = "es" if title.endswith("_es") else "en"
    doc = (f'<!doctype html><html lang="{lang}"><meta charset="utf-8"><title>{html.escape(title)}</title>'
           f"<style>{CSS % {'paper': paper}}</style><body>{body}</body></html>")
    pdf = md_path.with_suffix(".pdf")
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / f"{title}.html"
        src.write_text(doc, encoding="utf-8")
        cmd = [browser, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
               "--print-to-pdf-no-header", f"--user-data-dir={tmp}/profile",
               f"--print-to-pdf={pdf.resolve()}", src.resolve().as_uri()]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    if not pdf.exists() or pdf.stat().st_size == 0:
        sys.exit(f"Chrome did not produce {pdf}")
    return pdf


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("files", nargs="*", help="CV markdown files")
    p.add_argument("--paper", default="A4", choices=["A4", "letter"])
    p.add_argument("--check", action="store_true", help="only report the browser that will be used")
    a = p.parse_args()
    browser = find_browser()
    if a.check or not a.files:
        print(browser or "NOT FOUND: install Google Chrome or Chromium, or set CHROME=/path/to/browser")
        sys.exit(0 if browser else 1)
    if not browser:
        sys.exit("No Chrome/Chromium found. Install one, or set CHROME=/path/to/browser")
    for f in a.files:
        pdf = render(f, browser, a.paper)
        print(f"{pdf} ({pdf.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
