"""Alfred · email_gate — the ONE place a "cleared" email decision becomes a sent email.

Clearing an email (`review_store.py email-send <id>`, or `approve <id> --email`)
records a decision; it does not send. The application agent calls perform_send(),
which checks every guardrail and hands the message to SMTP, with one idempotency
record so the same email cannot go out twice.

Every guardrail the application agent enforces is enforced here, in this order:

    already sent   -> never twice (data/email_sent.json)
    decision       -> must read back "cleared"; None and "cancelled" both refuse
    /pause         -> global halt, nothing leaves
    email throttle -> data/email_paused.flag (bounce storm), via email_send.send()
    daily cap      -> caps.emails_per_day from config/search.yaml
    dry_run        -> config/search.yaml; logs what WOULD go, connects to nothing

and the outcome is returned either way — a refusal nobody sees is the same bug as an
email that silently never sends.

The portal channel is NOT here and cannot be: it needs the signed-in browser on the
user's own machine. This module is the email half only.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import paths  # single source of truth for paths (§4)
import bounce_check
import daily_caps
import email_send
import review_store as tb

EMAIL_SENT = os.path.join(paths.data_dir(), "email_sent.json")
EMAIL_FAILURES = os.path.join(paths.data_dir(), "email_send_failures.json")

_DEFAULT_EMAIL_CAP = 10  # only used if config/search.yaml cannot be read

# A permanently broken send (bad app password, refused recipient) is tried three
# times across runs, then stays refused until a human clears the failure.
MAX_SEND_ATTEMPTS = 3


# ---------------------------------------------------------------------------
# Idempotency — the record that stops a second send
# ---------------------------------------------------------------------------

def already_sent(job_id: str) -> Optional[Dict[str, Any]]:
    """The record of a previous send for `job_id`, or None. Checked FIRST, always."""
    store = tb._read_json(EMAIL_SENT, {})
    rec = store.get(job_id) if isinstance(store, dict) else None
    return rec if isinstance(rec, dict) else None


def record_sent(job_id: str, status: str, to: Optional[str] = None) -> bool:
    """Record that `job_id`'s email left (or was dry-run). Idempotent -> False if set.

    A FAILED attempt is deliberately NOT recorded: the user is told what broke and the
    draft is kept, so fixing the cause and running again must be able to actually send.
    """
    store = tb._read_json(EMAIL_SENT, {})
    if not isinstance(store, dict):
        store = {}
    if job_id in store:
        return False
    store[job_id] = {"status": status, "to": to, "ts": tb._now_iso()}
    tb._write_json(EMAIL_SENT, store)
    return True


def failure_count(job_id: str) -> int:
    store = tb._read_json(EMAIL_FAILURES, {})
    rec = store.get(job_id) if isinstance(store, dict) else None
    return int(rec.get("count", 0)) if isinstance(rec, dict) else 0


def record_failure(job_id: str, error: Optional[str]) -> int:
    """Count a failed attempt so the retry loop gives up instead of spamming."""
    store = tb._read_json(EMAIL_FAILURES, {})
    if not isinstance(store, dict):
        store = {}
    rec = store.get(job_id) if isinstance(store.get(job_id), dict) else {}
    rec = {"count": int(rec.get("count", 0)) + 1, "last_error": error,
           "last_ts": tb._now_iso()}
    store[job_id] = rec
    tb._write_json(EMAIL_FAILURES, store)
    return rec["count"]


def clear_failures(job_id: str) -> None:
    """Forget a job's failed attempts — call after fixing the cause, to re-arm it."""
    store = tb._read_json(EMAIL_FAILURES, {})
    if isinstance(store, dict) and store.pop(job_id, None) is not None:
        tb._write_json(EMAIL_FAILURES, store)


# ---------------------------------------------------------------------------
# Limits from config/search.yaml (read at call time — an edit takes effect at once)
# ---------------------------------------------------------------------------

def load_limits() -> Dict[str, Any]:
    """`dry_run` and `caps.emails_per_day`. Unreadable config -> the SAFE reading:
    dry_run ON, so a broken config can never be the reason a real email went out."""
    try:
        import yaml
        with open(paths.search_config(), "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
    except Exception:  # noqa: BLE001 — missing, unparseable, or PyYAML absent
        return {"dry_run": True, "emails_per_day": _DEFAULT_EMAIL_CAP, "config_read": False}
    caps = cfg.get("caps") or {}
    return {
        "dry_run": bool(cfg.get("dry_run", True)),
        "emails_per_day": int(caps.get("emails_per_day", _DEFAULT_EMAIL_CAP)),
        "config_read": True,
    }


# ---------------------------------------------------------------------------
# The send itself
# ---------------------------------------------------------------------------

def _refusal(job_id: str, reason: str, **extra: Any) -> Dict[str, Any]:
    return {"job_id": job_id, "sent": False, "reason": reason, **extra}


def perform_send(job_id: str, job: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Send `job_id`'s approved email if every guardrail allows it.

    Returns a result record; `sent` is True only when SMTP actually accepted it.
    Refusals are returned, never raised — one blocked job must not stop the rest.
    """
    prior = already_sent(job_id)
    if prior:
        return _refusal(job_id, f"already {prior.get('status', 'sent')}", when=prior.get("ts"))

    decision = tb.email_decision(job_id)
    if decision != "cleared":
        return _refusal(job_id, "not cleared by the user" if decision is None
                        else f"user {decision} this email")

    if tb.is_paused():
        return _refusal(job_id, "/pause is set — nothing leaves until you resume")

    if bounce_check.is_email_paused():
        return _refusal(job_id, "email channel throttled after bounces "
                                "— clear data/email_paused.flag")

    attempts = failure_count(job_id)
    if attempts >= MAX_SEND_ATTEMPTS:
        return _refusal(job_id, f"gave up after {attempts} failed attempts "
                                "— fix the cause, then clear_failures(job_id)")

    draft = tb.load_draft(job_id)
    if draft is None:
        return _refusal(job_id, "no draft to send")

    limits = load_limits()
    dry_run = limits["dry_run"]
    if not dry_run and daily_caps.remaining("email", limits["emails_per_day"]) <= 0:
        return _refusal(job_id, f"daily email cap reached ({limits['emails_per_day']})")

    missing = [a for a in (draft.get("attachments") or []) if not os.path.exists(a)]
    msg = email_send.build_message(
        to=draft.get("to", ""), subject=draft.get("subject", ""),
        body=draft.get("body", ""), attachments=draft.get("attachments") or [])

    result = email_send.send_safe(msg, dry_run=dry_run)
    status = result.get("status")

    if status in ("SENT", "DRY_RUN"):
        record_sent(job_id, status, draft.get("to"))
        clear_failures(job_id)
        if status == "SENT":
            daily_caps.record("email")
    else:
        attempts = record_failure(job_id, result.get("error") or result.get("reason"))

    return {"job_id": job_id, "sent": status == "SENT", "status": status,
            "to": result.get("to"), "attachments": result.get("attachments"),
            "missing_attachments": missing, "error": result.get("error"),
            "reason": result.get("reason"), "attempts": attempts}


def cleared_unsent() -> List[str]:
    """Jobs the user cleared for sending that have not been sent yet.

    Reads the decision store rather than a queue, so it survives any run that drained one.
    """
    store = tb._read_json(tb.EMAIL_DECISIONS, {})
    if not isinstance(store, dict):
        return []
    return sorted(job_id for job_id, rec in store.items()
                  if isinstance(rec, dict) and rec.get("decision") == "cleared"
                  and already_sent(job_id) is None)


def send_cleared() -> List[Dict[str, Any]]:
    """Send every cleared-but-unsent email.

    A success drops the job for good; a refusal is re-evaluated next run (the cap rolls
    over, /pause is cleared); a failure is counted and gives up after MAX_SEND_ATTEMPTS.
    """
    return [perform_send(job_id) for job_id in cleared_unsent()]
