"""WarmApply · docx_to_pdf — DOCX -> text-based PDF via LibreOffice headless.

Wraps `soffice --headless --convert-to pdf`. Produces a REAL text PDF (ATS-safe),
never an image. LibreOffice is a SYSTEM dependency (not pip) — see requirements.txt:
    Windows: winget install TheDocumentFoundation.LibreOffice
    macOS:   brew install --cask libreoffice
    Ubuntu:  sudo apt-get install libreoffice

Public API:
    - find_soffice() -> str | None      # path to the soffice binary, or None
    - is_available() -> bool
    - convert(docx_path, out_dir=None, timeout=120) -> str   # returns .pdf path

`convert` raises LibreOfficeNotFound if soffice isn't installed, so callers can
degrade gracefully (the dry-run reports it instead of failing hard).

No new dependencies — subprocess/shutil are stdlib.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Optional


class LibreOfficeNotFound(RuntimeError):
    """Raised when no soffice/libreoffice binary can be located."""


# Binary names searched on PATH (Windows resolves soffice.exe via shutil.which too).
_PATH_NAMES = ("soffice", "libreoffice")


def _windows_candidates() -> tuple:
    """Absolute soffice.exe locations for a standard Windows LibreOffice install.

    Built from the ProgramFiles env vars so it works whatever drive Windows is on;
    falls back to the conventional C:\\ paths when those vars aren't set.
    """
    roots = [
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        os.environ.get("LOCALAPPDATA", ""),  # per-user (winget/MSIX) installs
    ]
    return tuple(
        os.path.join(root, "LibreOffice", "program", "soffice.exe")
        for root in roots if root
    )


# Absolute fallbacks for macOS/Linux app-bundle and package locations.
_NIX_CANDIDATES = (
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    "/usr/bin/soffice",
    "/usr/local/bin/soffice",
    "/opt/homebrew/bin/soffice",
)


def find_soffice() -> Optional[str]:
    """Locate the LibreOffice binary, or return None if it isn't installed.

    Cross-platform: checks PATH first (covers most macOS/Linux installs and any
    Windows box where LibreOffice\\program is on PATH), then the well-known
    absolute install locations for the current OS.
    """
    # 1) On PATH — shutil.which finds soffice.exe on Windows and soffice elsewhere.
    for name in _PATH_NAMES:
        found = shutil.which(name)
        if found:
            return found

    # 2) Well-known absolute locations (Windows installs rarely add themselves to PATH).
    candidates = _windows_candidates() if os.name == "nt" else _NIX_CANDIDATES
    for cand in candidates:
        # os.access(..., X_OK) is unreliable on Windows; existence is enough there.
        if os.path.exists(cand) and (os.name == "nt" or os.access(cand, os.X_OK)):
            return cand
    return None


def is_available() -> bool:
    """True if a LibreOffice binary is available for conversion."""
    return find_soffice() is not None


def convert(docx_path: str, out_dir: Optional[str] = None,
            timeout: int = 120) -> str:
    """Convert `docx_path` to PDF in `out_dir` (default: alongside the docx).

    Returns the path to the produced .pdf. Raises LibreOfficeNotFound if the
    binary is missing, or RuntimeError if conversion fails.
    """
    if not os.path.exists(docx_path):
        raise FileNotFoundError(docx_path)

    soffice = find_soffice()
    if soffice is None:
        raise LibreOfficeNotFound(
            "LibreOffice (soffice) not found. Install it:\n"
            "  Windows: winget install TheDocumentFoundation.LibreOffice\n"
            "  macOS:   brew install --cask libreoffice\n"
            "  Ubuntu:  sudo apt-get install libreoffice"
        )

    out_dir = out_dir or os.path.dirname(os.path.abspath(docx_path))
    os.makedirs(out_dir, exist_ok=True)

    cmd = [soffice, "--headless", "--convert-to", "pdf",
           "--outdir", out_dir, docx_path]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"LibreOffice conversion timed out after {timeout}s") from exc

    pdf_path = os.path.join(
        out_dir, os.path.splitext(os.path.basename(docx_path))[0] + ".pdf")
    if proc.returncode != 0 or not os.path.exists(pdf_path):
        raise RuntimeError(
            "LibreOffice conversion failed "
            f"(exit {proc.returncode}).\nstdout: {proc.stdout}\nstderr: {proc.stderr}")
    return pdf_path


if __name__ == "__main__":  # tiny CLI: python docx_to_pdf.py <file.docx> [out_dir]
    import sys
    if len(sys.argv) < 2:
        print("usage: python docx_to_pdf.py <file.docx> [out_dir]")
        raise SystemExit(2)
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    try:
        print("PDF:", convert(src, dst))
    except LibreOfficeNotFound as e:
        print(e)
        raise SystemExit(3)
