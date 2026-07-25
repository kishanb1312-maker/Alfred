"""WarmApply · email_send — direct-recruiter email via Gmail SMTP (stdlib only).

Used by the application-agent's email channel. Builds a MIME message with the
tailored resume + cover letter attached and sends it through Gmail SMTP.

Guardrails baked in:
  - dry_run=True NEVER connects — it returns the serialized message + "DRY_RUN".
  - Gmail credentials come ONLY from the environment (GMAIL_ADDRESS,
    GMAIL_APP_PASSWORD); the password is never logged or returned.
  - All real network I/O goes through the single `_smtp_send()` chokepoint, so a
    dry-run can prove offline by monkeypatching it.

Stdlib only (smtplib, email, mimetypes) — NO new dependency.
"""

from __future__ import annotations

import mimetypes
import os
import smtplib
from email.message import EmailMessage
from typing import Any, Dict, List, Optional

_SMTP_HOST = "smtp.gmail.com"
_SMTP_SSL_PORT = 465


# ---------------------------------------------------------------------------
# Env / secrets (read at call time; never hardcoded, never logged)
# ---------------------------------------------------------------------------

def _gmail_address() -> str:
    addr = os.environ.get("GMAIL_ADDRESS", "").strip()
    if not addr:
        raise RuntimeError("GMAIL_ADDRESS not set in environment")
    return addr


def _gmail_app_password() -> str:
    pw = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    if not pw:
        raise RuntimeError("GMAIL_APP_PASSWORD not set in environment")
    return pw


# ---------------------------------------------------------------------------
# Build (pure — no network)
# ---------------------------------------------------------------------------

def build_message(to: str, subject: str, body: str,
                  attachments: Optional[List[str]] = None,
                  from_addr: Optional[str] = None) -> EmailMessage:
    """Construct an EmailMessage with `body` and any existing file attachments.

    `from_addr` defaults to the GMAIL_ADDRESS env value. Attachments that don't
    exist on disk are skipped (e.g. a PDF not built because LibreOffice is
    missing) — the caller decides whether that's acceptable.
    """
    msg = EmailMessage()
    msg["From"] = from_addr or os.environ.get("GMAIL_ADDRESS", "").strip() or "GMAIL_ADDRESS-not-set"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    for path in attachments or []:
        if not path or not os.path.exists(path):
            continue  # skip absent attachment; caller/card notes it separately
        ctype, encoding = mimetypes.guess_type(path)
        if ctype is None or encoding is not None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)
        with open(path, "rb") as fh:
            msg.add_attachment(fh.read(), maintype=maintype, subtype=subtype,
                              filename=os.path.basename(path))
    return msg


def attached_filenames(msg: EmailMessage) -> List[str]:
    """Names of the files attached to `msg` (for reporting/verification)."""
    return [part.get_filename() for part in msg.iter_attachments()
            if part.get_filename()]


# ---------------------------------------------------------------------------
# Send (network chokepoint — monkeypatched in the dry-run)
# ---------------------------------------------------------------------------

def _smtp_send(msg: EmailMessage) -> None:
    """The ONLY function that opens a network connection. Logs in and sends.

    Reads credentials from env at call time; never logs the password.
    """
    address = _gmail_address()
    password = _gmail_app_password()
    with smtplib.SMTP_SSL(_SMTP_HOST, _SMTP_SSL_PORT) as smtp:
        smtp.login(address, password)
        smtp.send_message(msg)


def send(msg: EmailMessage, dry_run: bool = True) -> Dict[str, Any]:
    """Send `msg`, or (dry_run) return what WOULD be sent without connecting.

    dry_run=True  → NO connection; returns {status: "DRY_RUN", ...serialized...}.
    dry_run=False → sends via Gmail SMTP; returns {status: "SENT", ...}.

    Defaults to dry_run=True so an accidental call never sends.
    """
    summary = {
        "to": msg["To"],
        "subject": msg["Subject"],
        "attachments": attached_filenames(msg),
        "size_bytes": len(msg.as_bytes()),
    }
    if dry_run:
        return {"status": "DRY_RUN", "serialized": msg.as_string(), **summary}

    _smtp_send(msg)
    return {"status": "SENT", **summary}
