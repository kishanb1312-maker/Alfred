"""WarmApply · bounce_check — cold-email bounce detection + auto-throttle safety.

Dual-channel outreach cold-emails every company, including single best-guess
addresses the user accepted the bounce risk for. To protect their Gmail, after a
run we check the sending inbox for bounce-backs (mailer-daemon) and, if a run
bounces too hard, **auto-pause the EMAIL channel only** (portal applications keep
going) and warn the user on Telegram. This never lowers the user's chosen cap — it
only halts a bounce-storm.

Channel-specific pause: this sets `data/email_paused.flag` (distinct from the global
`data/paused.flag` that `/pause` sets). The application-agent's email channel must
respect BOTH; the portal channel ignores the email flag.

Network boundary: the IMAP fetch (`_fetch_bounce_messages`) is the ONLY network
call and is isolated so the throttle logic (`is_bounce`, `detect_bounced`,
`evaluate_throttle`) is pure and offline-testable.

Threshold: trip if a run has >30% bounces OR >= 3 bounces.

stdlib only (imaplib, email) — no new dependency.
"""

from __future__ import annotations

import email as email_pkg
import imaplib
import os
from typing import Any, Dict, List, Optional

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_REPO_ROOT, "data")
EMAIL_PAUSE_FLAG = os.path.join(_DATA, "email_paused.flag")

_RATE_THRESHOLD = 0.30   # >30% of a run bouncing trips the throttle
_MIN_BOUNCES = 3         # ...or 3+ bounces regardless of rate

_BOUNCE_FROM_HINTS = ("mailer-daemon", "postmaster")
_BOUNCE_SUBJECT_HINTS = (
    "delivery status notification", "undeliverable", "delivery has failed",
    "returned mail", "mail delivery failed", "failure notice",
    "undelivered mail returned to sender",
)


# ---------------------------------------------------------------------------
# Pure classification / throttle logic (no network)
# ---------------------------------------------------------------------------

def is_bounce(subject: Optional[str], from_addr: Optional[str]) -> bool:
    """True if a message looks like a bounce / non-delivery report."""
    fa = (from_addr or "").lower()
    subj = (subject or "").lower()
    if any(h in fa for h in _BOUNCE_FROM_HINTS):
        return True
    return any(h in subj for h in _BOUNCE_SUBJECT_HINTS)


def detect_bounced(sent_recipients: List[str],
                   bounce_messages: List[Dict[str, Any]]) -> List[str]:
    """Which of `sent_recipients` appear in the bounce messages.

    Each bounce message is {subject, from, body}. A recipient counts as bounced if a
    bounce-classified message mentions its address in the subject/body (bounces echo
    the failed recipient). De-duplicated, order-preserving over sent_recipients.
    """
    bounced: List[str] = []
    for recipient in sent_recipients:
        r = (recipient or "").lower().strip()
        if not r:
            continue
        for msg in bounce_messages:
            if not is_bounce(msg.get("subject"), msg.get("from")):
                continue
            haystack = f"{msg.get('subject', '')} {msg.get('body', '')} {msg.get('recipient', '')}".lower()
            if r in haystack:
                bounced.append(recipient)
                break
    return bounced


def evaluate_throttle(sent_count: int, bounce_count: int, *,
                      rate_threshold: float = _RATE_THRESHOLD,
                      min_bounces: int = _MIN_BOUNCES) -> Dict[str, Any]:
    """Decide whether the email channel should auto-pause for this run."""
    sent_count = max(0, int(sent_count))
    bounce_count = max(0, int(bounce_count))
    rate = (bounce_count / sent_count) if sent_count > 0 else 0.0
    tripped = bounce_count >= min_bounces or rate > rate_threshold
    if tripped:
        reason = (f"{bounce_count} bounce(s) in {sent_count} send(s) "
                  f"(rate {rate:.0%}; trips at >{rate_threshold:.0%} or >= {min_bounces})")
    else:
        reason = "within safe bounds"
    return {"tripped": tripped, "sent_count": sent_count, "bounce_count": bounce_count,
            "bounce_rate": round(rate, 3), "rate_threshold": rate_threshold,
            "min_bounces": min_bounces, "reason": reason}


def throttle_warning(evaluation: Dict[str, Any]) -> str:
    """Telegram warning text when the throttle trips."""
    return (
        "⚠️ WarmApply auto-paused the EMAIL channel: " + evaluation["reason"] + ".\n"
        "Cold emails are halted to protect your Gmail — portal applications continue.\n"
        "Clear `data/email_paused.flag` (or send /resume) once the address list is cleaned up."
    )


# ---------------------------------------------------------------------------
# Email-channel pause flag (channel-specific; distinct from global /pause)
# ---------------------------------------------------------------------------

def set_email_pause(paused: bool = True, *, path: str = EMAIL_PAUSE_FLAG) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if paused:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("email-paused (bounce auto-throttle)\n")
    elif os.path.exists(path):
        os.remove(path)


def is_email_paused(*, path: str = EMAIL_PAUSE_FLAG) -> bool:
    return os.path.exists(path)


# ---------------------------------------------------------------------------
# Orchestration (pure given bounce_messages; used with the fetch below at runtime)
# ---------------------------------------------------------------------------

def apply_throttle(sent_recipients: List[str], bounce_messages: List[Dict[str, Any]], *,
                   path: str = EMAIL_PAUSE_FLAG) -> Dict[str, Any]:
    """Classify bounces for a run, evaluate the throttle, and pause email if tripped.

    Returns a report {bounced, throttle, paused_set, warning}. Pure except for the
    flag write when tripped — no network (bounce_messages are supplied by the caller,
    fetched via `_fetch_bounce_messages` at runtime or injected in tests).
    """
    bounced = detect_bounced(sent_recipients, bounce_messages)
    evaluation = evaluate_throttle(len(sent_recipients), len(bounced))
    warning = None
    if evaluation["tripped"]:
        set_email_pause(True, path=path)
        warning = throttle_warning(evaluation)
    return {"bounced": bounced, "throttle": evaluation,
            "paused_set": evaluation["tripped"], "warning": warning}


# ---------------------------------------------------------------------------
# Network chokepoint — IMAP fetch of recent bounce messages (runtime only)
# ---------------------------------------------------------------------------

def _fetch_bounce_messages(limit: int = 50) -> List[Dict[str, Any]]:
    """Read recent likely-bounce messages from the sending Gmail via IMAP.

    Credentials from env only (GMAIL_ADDRESS / GMAIL_APP_PASSWORD). The ONLY network
    call in this module; the dry-run never invokes it. Returns [] on any error.
    """
    address = os.environ.get("GMAIL_ADDRESS", "").strip()
    password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    if not address or not password:
        return []
    out: List[Dict[str, Any]] = []
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(address, password)
        imap.select("INBOX")
        typ, data = imap.search(None, '(FROM "mailer-daemon")')
        ids = data[0].split() if data and data[0] else []
        for msg_id in ids[-limit:]:
            typ, msg_data = imap.fetch(msg_id, "(RFC822)")
            if not msg_data or not msg_data[0]:
                continue
            msg = email_pkg.message_from_bytes(msg_data[0][1])
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body += part.get_payload(decode=True).decode("utf-8", "ignore")
            else:
                payload = msg.get_payload(decode=True)
                body = payload.decode("utf-8", "ignore") if payload else ""
            out.append({"subject": msg.get("Subject", ""), "from": msg.get("From", ""),
                        "body": body})
        imap.logout()
    except Exception:
        return out
    return out
