"""Alfred · email_send — direct-recruiter email via Gmail SMTP (stdlib only).

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
_IMAP_HOST = "imap.gmail.com"
_IMAP_SSL_PORT = 993

# Gmail localises the Drafts folder ("[Gmail]/Drafts" in English, "[Google Mail]/…"
# on older UK accounts, translated elsewhere), so the name is discovered from the
# server's \Drafts special-use flag and these are only the fallback guesses.
_DRAFT_FOLDER_FALLBACKS = ("[Gmail]/Drafts", "[Google Mail]/Drafts", "Drafts")


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


def resume_only(paths: Optional[List[str]]) -> List[str]:
    """Just the resume out of a job's attachment list.

    Alfred names tailored files `Resume_<Company>.pdf` and
    `CoverLetter_<Company>.pdf` — the same convention `telegram_bot.draft_attachments`
    globs for — so the resume is identified by name rather than by position. Position
    would be wrong exactly when it matters: a job whose resume failed to build leaves
    the cover letter at index 0, and "attach the first file" would then attach the
    cover letter to an email the user asked to carry a resume.

    Returns an empty list when no file matches. That is deliberate: a caller that
    wanted a resume and got none should report it, not quietly attach something else.
    """
    return [p for p in (paths or [])
            if os.path.basename(p).lower().startswith("resume")]


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

    # Bounce auto-throttle: if the email channel was auto-paused (bounce-storm),
    # refuse to send. Portal applications are unaffected (they use a different path).
    import bounce_check  # local import to avoid a hard dependency at module load
    if bounce_check.is_email_paused():
        return {"status": "EMAIL_PAUSED",
                "reason": "email channel auto-paused (bounce throttle); clear data/email_paused.flag",
                **summary}

    _smtp_send(msg)
    return {"status": "SENT", **summary}


def send_safe(msg: EmailMessage, dry_run: bool = True) -> Dict[str, Any]:
    """`send`, but an SMTP failure becomes a FAILED result instead of an exception.

    The Telegram flow reports the outcome of every Send tap back to the user, so a
    refused login or a rejected recipient has to arrive as a message they can read —
    not as a traceback that ends the run and leaves the other approved jobs unsent.
    """
    try:
        return send(msg, dry_run=dry_run)
    except Exception as exc:  # noqa: BLE001 — every failure mode is reportable
        return {
            "status": "FAILED",
            "error": f"{type(exc).__name__}: {exc}",
            "to": msg["To"],
            "subject": msg["Subject"],
            "attachments": attached_filenames(msg),
        }


# ---------------------------------------------------------------------------
# Drafts (network chokepoint — monkeypatched in the dry-run)
#
# Why IMAP rather than the Gmail API: the user already has GMAIL_ADDRESS and
# GMAIL_APP_PASSWORD in their .env for SMTP, and IMAP APPEND takes exactly the
# same credentials. The API route would mean an OAuth client, a consent screen and
# a second secret to store, to land the same message in the same folder.
# ---------------------------------------------------------------------------

def _imap_draft_folder(imap: Any) -> str:
    """The mailbox flagged \\Drafts on this account, else a fallback guess.

    Asking the server beats hardcoding "[Gmail]/Drafts": that string is localised,
    and appending to a folder that does not exist creates a stray top-level one
    rather than failing loudly.
    """
    try:
        typ, data = imap.list()
        if typ == "OK":
            for raw in data or []:
                line = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
                if "\\Drafts" in line:
                    return line.rsplit(' "/" ', 1)[-1].strip().strip('"')
    except Exception:  # noqa: BLE001 — discovery is best effort; fallbacks follow
        pass
    return _DRAFT_FOLDER_FALLBACKS[0]


def _imap_append(msg: EmailMessage) -> str:
    """The ONLY function that opens an IMAP connection. Returns the folder used.

    Reads credentials from env at call time; never logs the password.
    """
    import imaplib
    import time

    address = _gmail_address()
    password = _gmail_app_password()
    imap = imaplib.IMAP4_SSL(_IMAP_HOST, _IMAP_SSL_PORT)
    try:
        imap.login(address, password)
        folder = _imap_draft_folder(imap)
        typ, data = imap.append(f'"{folder}"', "\\Draft",
                                imaplib.Time2Internaldate(time.time()),
                                msg.as_bytes())
        if typ != "OK":
            raise RuntimeError(f"IMAP APPEND to {folder!r} failed: {typ} {data!r}")
        return folder
    finally:
        try:
            imap.logout()
        except Exception:  # noqa: BLE001 — a failed logout must not mask the result
            pass


def save_draft(msg: EmailMessage) -> Dict[str, Any]:
    """Put `msg` in the user's Gmail Drafts folder. Returns a result record.

    **Deliberately not gated by `dry_run`.** That flag means "simulate, never send",
    and a draft is not a send: it lands in the user's own mailbox, reaches no
    company, and is deleted with one click. Gating it would make the feature
    useless for exactly the users the flag protects — the ones who, correctly, keep
    dry_run on while they build trust in the pipeline. The send path is untouched
    and keeps every guardrail.

    `/pause` IS honoured. Pause means the user wants Alfred to stop doing things,
    and quietly filling their Drafts folder while they think it is stopped is the
    kind of surprise the flag exists to prevent.
    """
    summary = {
        "to": msg["To"],
        "subject": msg["Subject"],
        "attachments": attached_filenames(msg),
        "size_bytes": len(msg.as_bytes()),
    }

    import telegram_bot as tb  # local import: keeps the module importable without it
    if tb.is_paused():
        return {"status": "PAUSED",
                "reason": "/pause is set — no drafts written; send /resume to Alfred",
                **summary}

    folder = _imap_append(msg)
    return {"status": "DRAFTED", "folder": folder, **summary}


def save_draft_safe(msg: EmailMessage) -> Dict[str, Any]:
    """`save_draft`, but an IMAP failure becomes a FAILED result, not an exception.

    One unreachable mailbox, one rejected login, one oversized attachment must not
    end the pass and leave the remaining jobs undrafted with no explanation.
    """
    try:
        return save_draft(msg)
    except Exception as exc:  # noqa: BLE001 — every failure mode is reportable
        return {
            "status": "FAILED",
            "error": f"{type(exc).__name__}: {exc}",
            "to": msg["To"],
            "subject": msg["Subject"],
            "attachments": attached_filenames(msg),
        }
