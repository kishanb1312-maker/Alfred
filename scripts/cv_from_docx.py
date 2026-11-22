#!/usr/bin/env python3
"""Alfred · cv_from_docx — turn the master resume .docx into a first cv.md.

career-ops tailors CVs from `cv.md` (markdown), not from the .docx. This makes a
faithful first draft: every line comes from the document, nothing is added.

    Heading styles      -> #, ##, ###
    "Title" style        -> # (the name line)
    List / bullet styles -> "- "
    bold-only short line -> **line** (job titles in most resume layouts)
    everything else      -> plain paragraph

career-ops's CV checks find jobs by heading (`## Experience`, then
`### Company — Location`, a `**Title**` line and a dates line). Resume layouts
vary, so after converting, the setup step reshapes the draft into that form
using only the text already in it, then runs `node doctor.mjs` to confirm.

Usage:  cv_from_docx.py <resume.docx> [--out cv.md] [--force]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402

_SECTION_WORDS = ("experience", "employment", "work history", "education", "skills",
                  "projects", "summary", "profile", "certifications", "languages",
                  "awards", "publications", "tools", "achievements")


def _style(par) -> str:
    try:
        return (par.style.name or "").lower()
    except Exception:  # noqa: BLE001
        return ""


def _all_bold(par) -> bool:
    runs = [r for r in par.runs if r.text.strip()]
    return bool(runs) and all(bool(r.bold) for r in runs)


def paragraph_to_md(text: str, style: str, all_bold: bool, first: bool) -> str:
    """PURE: one paragraph -> one markdown line ('' for blank)."""
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if not text:
        return ""
    m = re.match(r"heading\s*(\d)", style)
    if m:
        level = min(int(m.group(1)) + 1, 4)  # Heading 1 -> ## (the name owns #)
        return "#" * level + " " + text
    if style == "title" or (first and len(text) < 60):
        return "# " + text
    if "list" in style or text[:1] in ("•", "▪", "◦", "●", "-", "–", "*"):
        return "- " + text.lstrip("•▪◦●-–* ").strip()
    low = text.lower().rstrip(":")
    if low in _SECTION_WORDS or (text.isupper() and len(text) < 40):
        return "## " + text.title().rstrip(":")
    if all_bold and len(text) < 90:
        return f"**{text}**"
    return text


def convert(docx_path: str) -> str:
    import docx  # python-docx
    document = docx.Document(docx_path)
    lines: List[str] = []
    first = True
    for par in document.paragraphs:
        md = paragraph_to_md(par.text, _style(par), _all_bold(par), first)
        if md:
            first = False
        if md or (lines and lines[-1] != ""):
            lines.append(md)
    for table in document.tables:  # some templates put whole sections in tables
        for row in table.rows:
            cells = [re.sub(r"\s+", " ", c.text).strip() for c in row.cells]
            cells = [c for i, c in enumerate(cells) if c and c not in cells[:i]]
            if cells:
                lines.append(" · ".join(cells))
    text = "\n".join(lines).strip() + "\n"
    return re.sub(r"\n{3,}", "\n\n", text)


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("docx")
    ap.add_argument("--out", default=paths.cv_md())
    ap.add_argument("--force", action="store_true", help="overwrite an existing cv.md")
    a = ap.parse_args(argv)
    if not os.path.isfile(a.docx):
        print(f"❌ not found: {a.docx}")
        return 2
    if os.path.exists(a.out) and not a.force:
        print(f"•  {a.out} already exists — kept (use --force to replace it)")
        return 0
    md = convert(a.docx)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(f"✅ wrote {a.out} ({len(md.splitlines())} lines) from {os.path.basename(a.docx)}")
    print("   Next: reshape headings to career-ops form (## Experience / ### Company — Location /"
          " **Title** / dates) using only this text, then run the career-ops doctor.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
