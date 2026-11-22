"""Alfred · cv_from_docx DRY-RUN (OFFLINE).

Builds a small FAKE resume .docx with python-docx, converts it, and proves:
  - every line of the output comes from the document (nothing added),
  - name -> '#', section words / headings -> '##', bullets -> '- ', bold title -> **…**,
  - an existing cv.md is kept unless --force.
"""

from __future__ import annotations

import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["ALFRED_HOME"] = tempfile.mkdtemp(prefix="alfred_cv_")

import cv_from_docx  # noqa: E402


def build(path: str) -> list:
    import docx
    d = docx.Document()
    d.add_paragraph("Fake Person")
    d.add_paragraph("Bengaluru · fake@example.com")
    d.add_paragraph("EXPERIENCE")
    p = d.add_paragraph()
    p.add_run("Senior Product Designer").bold = True
    d.add_paragraph("Acme — Bengaluru · 2022–Present")
    d.add_paragraph("Redesigned onboarding flow for a fake app", style="List Bullet")
    d.add_heading("Skills", level=1)
    d.add_paragraph("Figma, prototyping, user research")
    d.save(path)
    return ["Fake Person", "Bengaluru · fake@example.com", "Experience", "Senior Product Designer",
            "Acme — Bengaluru · 2022–Present", "Redesigned onboarding flow for a fake app", "Skills",
            "Figma, prototyping, user research"]


def main() -> int:
    print("=" * 70)
    print("Alfred · cv_from_docx — DRY RUN (offline, fake resume)")
    print("=" * 70)
    failures = []

    def check(ok, label):
        failures.extend([] if ok else [label])
        print(f"  [{'OK' if ok else 'XX'}] {label}")

    tmp = tempfile.mkdtemp()
    src = os.path.join(tmp, "fake.docx")
    source_lines = build(src)
    md = cv_from_docx.convert(src)
    print(md)
    lines = [l for l in md.splitlines() if l.strip()]
    stripped = [re.sub(r"^(#+ |- )|\*\*", "", l).strip() for l in lines]
    check(all(any(s.lower() == x.lower() for x in source_lines) for s in stripped),
          "every output line comes from the document (nothing invented)")
    check(lines[0] == "# Fake Person", "name → '# '")
    check("## Experience" in lines and any(l.startswith("##") and "Skills" in l for l in lines),
          "section words and headings → '##'")
    check("**Senior Product Designer**" in lines, "bold short line → **title**")
    check("- Redesigned onboarding flow for a fake app" in lines, "list bullet → '- '")

    out = os.path.join(tmp, "cv.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("mine\n")
    cv_from_docx.main([src, "--out", out])
    kept = open(out, encoding="utf-8").read() == "mine\n"
    cv_from_docx.main([src, "--out", out, "--force"])
    replaced = open(out, encoding="utf-8").read().startswith("# Fake Person")
    check(kept and replaced, "existing cv.md kept; --force replaces it")

    print("\n" + "=" * 70)
    if failures:
        print("RESULT: FAIL ❌")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("RESULT: PASS ✅ — faithful docx → cv.md draft; offline.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
