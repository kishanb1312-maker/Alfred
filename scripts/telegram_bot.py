"""Alfred · telegram_bot — Approval Gate transport (Telegram Bot HTTP API).

Sends one review card per job (text + inline Approve/Skip + the tailored PDFs),
and polls getUpdates to collect the user's taps and /pause. Designed so a tap can
arrive hours later: the update `offset` is persisted, so a late tap is picked up
on the next run.

Secrets come ONLY from the environment:
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID   (never hardcoded, never logged)

Network boundary: EVERY HTTP call goes through the single `_api()` chokepoint.
The payload builders and update parser are PURE (no network, no file writes), so
they can be verified fully offline — the dry-run monkeypatches `_api` to prove no
real request is ever made.

Dependency: requests (already in requirements.txt). Everything else is stdlib.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

# ---------------------------------------------------------------------------
# Paths (gitignored runtime state)
# ---------------------------------------------------------------------------

import paths  # single source of truth for paths (§4); sibling import, scripts/ on sys.path

_DATA = paths.data_dir()                       # makedirs target for save_offset/set_pause
STATE_PATH = paths.telegram_state_path()
PAUSE_FLAG = paths.pause_flag()
APPROVED_QUEUE = paths.approved_queue_path()

_API_BASE = "https://api.telegram.org/bot{token}/{method}"
_HTTP_TIMEOUT = 65  # long-poll friendly


# ---------------------------------------------------------------------------
# Env / secrets (read at call time; never hardcoded)
# ---------------------------------------------------------------------------

def _token() -> str:
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not tok:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set in environment")
    return tok


def _chat_id() -> str:
    cid = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not cid:
        raise RuntimeError("TELEGRAM_CHAT_ID not set in environment")
    return cid


# ---------------------------------------------------------------------------
# Single network chokepoint. Monkeypatched in the dry-run to prove offline.
# ---------------------------------------------------------------------------

def _api(method: str, data: Optional[Dict[str, Any]] = None,
         files: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """POST to the Telegram Bot API and return the parsed JSON. The ONLY caller
    of `requests`. Raises on transport or API-level (`ok: false`) errors."""
    url = _API_BASE.format(token=_token(), method=method)
    resp = requests.post(url, data=data, files=files, timeout=_HTTP_TIMEOUT)
    resp.raise_for_status()
    payload = resp.json()
    if not payload.get("ok", False):
        raise RuntimeError(f"Telegram API error on {method}: {payload}")
    return payload


# ---------------------------------------------------------------------------
# PURE: card text, inline keyboard, attachment resolution, callback data
# ---------------------------------------------------------------------------

def _derive_channel(job: Dict[str, Any]) -> str:
    if job.get("channel") in ("portal", "email"):
        return job["channel"]
    email = job.get("email") or {}
    if email.get("address") and email.get("source") not in (None, "", "none"):
        return "email"
    return "portal"


# Card 1 (job review) answers approve/skip. Card 2 (email preview) answers
# send/cancel. Both ride the same '<decision>|<job_id>' payload, so one parser and
# one poll loop serve both gates.
_DECISIONS = ("approve", "skip", "send", "edit", "cancel")


def make_callback_data(decision: str, job_id: str) -> str:
    """Inline-button payload: '<decision>|<job_id>'. (Telegram cap: 64 bytes.)"""
    return f"{decision}|{job_id}"


def parse_callback_data(data: str) -> Optional[Dict[str, str]]:
    """Inverse of make_callback_data → {'decision','job_id'} or None if invalid."""
    if not data or "|" not in data:
        return None
    decision, job_id = data.split("|", 1)
    if decision not in _DECISIONS or not job_id:
        return None
    return {"decision": decision, "job_id": job_id}


def build_inline_keyboard(job_id: str) -> Dict[str, Any]:
    """The [✅ Approve] [⏭️ Skip] inline keyboard, carrying the Job ID."""
    return {
        "inline_keyboard": [[
            {"text": "✅ Approve", "callback_data": make_callback_data("approve", job_id)},
            {"text": "⏭️ Skip", "callback_data": make_callback_data("skip", job_id)},
        ]]
    }


def resolve_attachments(job: Dict[str, Any], resume_pdf: Optional[str],
                        cover_pdf: Optional[str]) -> Tuple[List[Tuple[str, str]], List[str]]:
    """Split intended attachments into (present, missing_labels).

    `present` is [(label, path)] for files that exist; `missing` is the labels
    of intended-but-absent files (e.g. PDF not built because LibreOffice missing).
    """
    intended = [("Resume", resume_pdf), ("Cover Letter", cover_pdf)]
    present: List[Tuple[str, str]] = []
    missing: List[str] = []
    for label, path in intended:
        if path and os.path.exists(path):
            present.append((label, path))
        else:
            missing.append(label)
    return present, missing


def build_card_text(job: Dict[str, Any], missing_attachments: Optional[List[str]] = None) -> str:
    """Render the exact review-card text for a job (per the agent definition)."""
    company_analysis = job.get("company_analysis") or {}
    match = job.get("match") or {}
    email = job.get("email") or {}
    website = company_analysis.get("website") or job.get("company_domain") or "—"
    channel = _derive_channel(job)
    what_changed = job.get("what_i_changed_summary")
    if not what_changed:
        wic = (job.get("what_i_changed") or "").strip()
        what_changed = wic.splitlines()[0] if wic else "—"

    lines = [
        f"📋 New application ready — {job.get('job_id', '—')}",
        f"🏢 {job.get('company', '—')}  ({website})",
        f"💼 {job.get('title', '—')} · {job.get('location', '—')}",
        f"🎯 Match: {match.get('score', '—')}%   |   Channel: {channel}",
        f"📝 What I changed: {what_changed}",
        f"🔗 Job: {job.get('url', '—')}       📄 Notion: {job.get('notion_url', '—')}",
    ]
    if channel == "email" and email.get("address"):
        lines.append(
            f"✉️ To: {email['address']} "
            f"(confidence {email.get('confidence', '—')}%, source {email.get('source', '—')})"
        )
    if missing_attachments:
        lines.append(f"⚠️ Not attached (file missing): {', '.join(missing_attachments)}")
    return "\n".join(lines)


def parse_updates(updates: Any, current_offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
    """PURE parse of a getUpdates response → (events, new_offset).

    Accepts either the full response dict ({'ok':..,'result':[..]}) or a bare
    result list. Each event is one of:
        {'type':'decision','job_id','decision','callback_query_id','update_id'}
        {'type':'command','command':'pause'|'resume','update_id'}
    new_offset = max(update_id)+1 so processed updates aren't re-fetched.
    """
    if isinstance(updates, dict):
        results = updates.get("result", [])
    else:
        results = updates or []

    events: List[Dict[str, Any]] = []
    max_update_id = current_offset - 1

    for upd in results:
        uid = upd.get("update_id")
        if isinstance(uid, int):
            max_update_id = max(max_update_id, uid)

        cq = upd.get("callback_query")
        if cq:
            parsed = parse_callback_data(cq.get("data", ""))
            if parsed:
                events.append({
                    "type": "decision",
                    "job_id": parsed["job_id"],
                    "decision": parsed["decision"],
                    "callback_query_id": cq.get("id"),
                    "update_id": uid,
                })
            continue

        msg = upd.get("message") or upd.get("edited_message") or {}
        text = (msg.get("text") or "").strip().lower()
        if text.startswith("/pause"):
            events.append({"type": "command", "command": "pause", "update_id": uid})
        elif text.startswith("/resume"):
            events.append({"type": "command", "command": "resume", "update_id": uid})
        elif text:
            # Any other text is a candidate edit body. The poller decides whether an
            # edit is actually awaited; parsing stays pure and keeps the raw text.
            events.append({
                "type": "text",
                "text": (msg.get("text") or "").strip(),   # raw, not lower-cased
                "reply_to": (msg.get("reply_to_message") or {}).get("message_id"),
                "update_id": uid,
            })

    new_offset = max_update_id + 1 if max_update_id >= current_offset else current_offset
    return events, new_offset


# ---------------------------------------------------------------------------
# State helpers (stdlib file I/O — used at runtime, not by the pure parser)
# ---------------------------------------------------------------------------

def load_offset() -> int:
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as fh:
            return int(json.load(fh).get("offset", 0))
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return 0


def save_offset(offset: int) -> None:
    os.makedirs(_DATA, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump({"offset": int(offset)}, fh)


def set_pause(paused: bool) -> None:
    """Create/remove the global pause flag the application agent must respect."""
    os.makedirs(_DATA, exist_ok=True)
    if paused:
        with open(PAUSE_FLAG, "w", encoding="utf-8") as fh:
            fh.write("paused\n")
    elif os.path.exists(PAUSE_FLAG):
        os.remove(PAUSE_FLAG)


def is_paused() -> bool:
    return os.path.exists(PAUSE_FLAG)


def enqueue_approved(job_id: str) -> bool:
    """Add a Job ID to the approved queue. Idempotent → False if already queued."""
    os.makedirs(_DATA, exist_ok=True)
    try:
        with open(APPROVED_QUEUE, "r", encoding="utf-8") as fh:
            queue = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        queue = []
    if job_id in queue:
        return False
    queue.append(job_id)
    with open(APPROVED_QUEUE, "w", encoding="utf-8") as fh:
        json.dump(queue, fh, indent=2)
    return True


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _attachment_names(msg: Any) -> List[str]:
    """Filenames actually attached to `msg`.

    Read here rather than imported from email_send so this module keeps its single
    dependency direction — email_send imports nothing from telegram_bot and vice
    versa, and the preview works even when SMTP config is absent.
    """
    if msg is None:
        return []
    try:
        return [part.get_filename() for part in msg.iter_attachments()
                if part.get_filename()]
    except Exception:
        return []


EMAIL_DECISIONS = os.path.join(_DATA, "email_decisions.json")
EMAIL_DRAFTS = os.path.join(_DATA, "email_drafts.json")
AWAITING_EDIT = os.path.join(_DATA, "email_awaiting_edit.json")


def _read_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json(path: str, value: Any) -> None:
    os.makedirs(_DATA, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(value, fh, indent=2, sort_keys=True)


def save_draft(job_id: str, to: str, subject: str, body: str,
               attachments: Optional[List[str]] = None) -> Dict[str, Any]:
    """Persist the email for `job_id` so Edit has something to edit.

    Without this the message existed only inside whichever agent turn built it, and
    an edit would have nothing to apply to.
    """
    drafts = _read_json(EMAIL_DRAFTS, {})
    if not isinstance(drafts, dict):
        drafts = {}
    draft = {"to": to, "subject": subject, "body": body,
             "attachments": list(attachments or []), "updated_at": _now_iso()}
    drafts[job_id] = draft
    _write_json(EMAIL_DRAFTS, drafts)
    return draft


def load_draft(job_id: str) -> Optional[Dict[str, Any]]:
    """The current draft for `job_id` — edits included — or None."""
    drafts = _read_json(EMAIL_DRAFTS, {})
    d = drafts.get(job_id) if isinstance(drafts, dict) else None
    return d if isinstance(d, dict) else None


def parse_edit_text(raw: str) -> Dict[str, Optional[str]]:
    """Split an edit reply into {subject, body}.

    A first line of "Subject: ..." retitles the email and the rest becomes the body;
    otherwise the whole text is the body and the subject is left alone (None). This
    keeps the common case — retype the body — a plain paste with no syntax to learn.
    """
    text = (raw or "").strip()
    if not text:
        return {"subject": None, "body": ""}
    first, _, rest = text.partition("\n")
    if first.strip().lower().startswith("subject:"):
        return {"subject": first.split(":", 1)[1].strip() or None,
                "body": rest.strip()}
    return {"subject": None, "body": text}


def apply_edit(job_id: str, raw: str) -> Optional[Dict[str, Any]]:
    """Apply an edit reply to the stored draft. Returns the updated draft, or None.

    Attachments are untouched: the user is editing words, and silently dropping the
    resume because they retyped the body would be the worst possible reading of an edit.
    """
    draft = load_draft(job_id)
    if draft is None:
        return None
    parsed = parse_edit_text(raw)
    if not parsed["body"]:
        return None  # an empty edit is not an instruction to send an empty email
    draft["body"] = parsed["body"]
    if parsed["subject"]:
        draft["subject"] = parsed["subject"]
    draft["updated_at"] = _now_iso()
    drafts = _read_json(EMAIL_DRAFTS, {})
    if not isinstance(drafts, dict):
        drafts = {}
    drafts[job_id] = draft
    _write_json(EMAIL_DRAFTS, drafts)
    return draft


def set_awaiting_edit(job_id: str) -> None:
    """Mark that the next plain text message is an edit for `job_id`."""
    _write_json(AWAITING_EDIT, {"job_id": job_id, "since": _now_iso()})


def get_awaiting_edit() -> Optional[str]:
    rec = _read_json(AWAITING_EDIT, {})
    return rec.get("job_id") if isinstance(rec, dict) else None


def clear_awaiting_edit() -> None:
    _write_json(AWAITING_EDIT, {})


def record_email_decision(job_id: str, decision: str) -> bool:
    """Record the second gate's answer for `job_id`. Idempotent → False if already set.

    `decision` is "cleared" (the user tapped Send) or "cancelled" (tapped Cancel).
    The first answer wins: a job whose email was cancelled cannot be un-cancelled by a
    later stray tap on the same card.
    """
    if decision not in ("cleared", "cancelled"):
        raise ValueError(f"decision must be cleared|cancelled, got {decision!r}")
    os.makedirs(_DATA, exist_ok=True)
    try:
        with open(EMAIL_DECISIONS, "r", encoding="utf-8") as fh:
            store = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        store = {}
    if not isinstance(store, dict):
        store = {}
    if job_id in store:
        return False
    store[job_id] = {"decision": decision, "ts": _now_iso()}
    with open(EMAIL_DECISIONS, "w", encoding="utf-8") as fh:
        json.dump(store, fh, indent=2, sort_keys=True)
    return True


def email_decision(job_id: str) -> Optional[str]:
    """"cleared" | "cancelled" | None (no answer yet — the email must NOT be sent)."""
    try:
        with open(EMAIL_DECISIONS, "r", encoding="utf-8") as fh:
            store = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    rec = store.get(job_id) if isinstance(store, dict) else None
    return rec.get("decision") if isinstance(rec, dict) else None


def build_email_keyboard(job_id: str) -> Dict[str, Any]:
    """The [📧 Send] [🚫 Cancel] keyboard for the email-preview card."""
    return {
        "inline_keyboard": [[
            {"text": "📧 Send", "callback_data": make_callback_data("send", job_id)},
            {"text": "✏️ Edit", "callback_data": make_callback_data("edit", job_id)},
            {"text": "🚫 Cancel", "callback_data": make_callback_data("cancel", job_id)},
        ]]
    }


def build_email_preview_text(job: Dict[str, Any], msg: Any,
                             body_limit: int = 1200) -> str:
    """Render the exact email that would go out, for the second Telegram gate.

    Shows From, To, Subject, the body, and the real attachment filenames taken from
    the built message — not from what the caller intended to attach, so a PDF that
    silently failed to build is visible here rather than discovered by the recipient.
    """
    body = ""
    if msg is not None:
        try:
            part = msg.get_body(preferencelist=("plain",))
            body = part.get_content() if part is not None else ""
        except Exception:
            body = ""
    body = (body or "").strip()
    if len(body) > body_limit:
        body = body[:body_limit].rstrip() + "\n\n… (truncated for this preview)"

    names = _attachment_names(msg)
    attach_line = ", ".join(n for n in names if n) or "⚠️ none — nothing will be attached"

    company = job.get("company") or "unknown company"
    title = job.get("title") or "unknown role"
    return (
        f"📧 READY TO SEND — {company}\n"
        f"{title}\n"
        f"{'─' * 28}\n"
        f"From:    {msg['From'] if msg is not None else '?'}\n"
        f"To:      {msg['To'] if msg is not None else '?'}\n"
        f"Subject: {msg['Subject'] if msg is not None else '?'}\n"
        f"Files:   {attach_line}\n"
        f"{'─' * 28}\n"
        f"{body}\n"
        f"{'─' * 28}\n"
        f"Tap Send to email this to the company, or Cancel to skip the email.\n"
        f"Cancel does NOT cancel the portal application."
    )


# ---------------------------------------------------------------------------
# NETWORK: send + poll + ack (all route through _api)
# ---------------------------------------------------------------------------

def send_review_card(job: Dict[str, Any], resume_pdf: Optional[str],
                     cover_pdf: Optional[str]) -> int:
    """Send the card (text + Approve/Skip buttons) then attach existing PDFs.
    Returns the sent message_id."""
    present, missing = resolve_attachments(job, resume_pdf, cover_pdf)
    text = build_card_text(job, missing)
    keyboard = build_inline_keyboard(job.get("job_id", ""))

    resp = _api("sendMessage", data={
        "chat_id": _chat_id(),
        "text": text,
        "reply_markup": json.dumps(keyboard),
        "disable_web_page_preview": True,
    })
    message_id = resp["result"]["message_id"]

    for label, path in present:
        with open(path, "rb") as fh:
            _api("sendDocument",
                 data={"chat_id": _chat_id(), "caption": f"{label} — {job.get('company', '')}"},
                 files={"document": (os.path.basename(path), fh)})
    return message_id


def send_email_preview_card(job: Dict[str, Any], msg: Any) -> int:
    """Second gate: show the exact email and ask Send/Cancel. Returns the message_id.

    Sending this card does NOT send the email. Nothing reaches the company until the
    user taps Send and `email_decision(job_id)` reads back "cleared".
    """
    resp = _api("sendMessage", data={
        "chat_id": _chat_id(),
        "text": build_email_preview_text(job, msg),
        "reply_markup": json.dumps(build_email_keyboard(job.get("job_id", ""))),
        "disable_web_page_preview": True,
    })
    return resp["result"]["message_id"]


def send_edit_prompt(job: Dict[str, Any]) -> int:
    """Ask for the replacement text after an Edit tap, and arm the edit capture."""
    job_id = job.get("job_id", "")
    set_awaiting_edit(job_id)
    text = (
        f"✏️ EDITING — {job.get('company') or 'this email'}\n"
        f"{'─' * 28}\n"
        "Reply to this message with the new email.\n\n"
        "• Plain text replaces the body.\n"
        "• To change the subject too, make the FIRST line:\n"
        "  Subject: your new subject\n\n"
        "Attachments stay as they are. I'll show you the updated email with "
        "Send / Edit / Cancel again — nothing goes out until you tap Send."
    )
    resp = _api("sendMessage", data={
        "chat_id": _chat_id(),
        "text": text,
        "reply_markup": json.dumps({"force_reply": True}),
        "disable_web_page_preview": True,
    })
    return resp["result"]["message_id"]


def send_result_notice(job: Dict[str, Any], result: Dict[str, Any]) -> int:
    """Report what actually happened to a Send tap — success or the real error."""
    status = (result or {}).get("status", "UNKNOWN")
    company = job.get("company") or "the company"
    to = (result or {}).get("to") or "?"
    subject = (result or {}).get("subject") or "?"
    files = ", ".join(f for f in ((result or {}).get("attachments") or []) if f) or "none"

    if status == "SENT":
        head = f"✅ SENT — {company}"
        tail = f"Delivered to {to} at {_now_iso()}."
    elif status == "DRY_RUN":
        head = f"🧪 DRY RUN — {company}"
        tail = ("Nothing was sent: dry_run is ON in config/search.yaml. "
                "This is exactly what WOULD have gone out.")
    elif status == "EMAIL_PAUSED":
        head = f"⏸️ NOT SENT — {company}"
        tail = ((result or {}).get("reason")
                or "email channel auto-paused; clear data/email_paused.flag")
    else:
        head = f"❌ FAILED — {company}"
        tail = (f"{(result or {}).get('error') or 'unknown error'}\n\n"
                "The email was NOT sent. The draft is kept, so you can tap Edit "
                "and try again once the cause is fixed.")

    text = (f"{head}\n{'─' * 28}\n"
            f"To:      {to}\n"
            f"Subject: {subject}\n"
            f"Files:   {files}\n"
            f"{'─' * 28}\n{tail}")
    resp = _api("sendMessage", data={
        "chat_id": _chat_id(), "text": text, "disable_web_page_preview": True})
    return resp["result"]["message_id"]


def poll_responses(offset: Optional[int] = None) -> Tuple[List[Dict[str, Any]], int]:
    """Fetch updates from `offset`, parse them, apply /pause, persist the offset.

    Returns (events, new_offset). Callers act on the events (update Notion,
    enqueue approved). /pause is applied here so the flag is set immediately.
    """
    if offset is None:
        offset = load_offset()
    resp = _api("getUpdates", data={"offset": offset, "timeout": 0})
    events, new_offset = parse_updates(resp, offset)

    for ev in events:
        if ev.get("type") == "command" and ev.get("command") == "pause":
            set_pause(True)
        elif ev.get("type") == "command" and ev.get("command") == "resume":
            set_pause(False)

    save_offset(new_offset)
    return events, new_offset


def answer_callback(callback_query_id: str, text: str = "Got it ✅") -> Dict[str, Any]:
    """Acknowledge a button tap so Telegram stops the client's spinner."""
    return _api("answerCallbackQuery",
                data={"callback_query_id": callback_query_id, "text": text})
