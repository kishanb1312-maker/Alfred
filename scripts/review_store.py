#!/usr/bin/env python3
"""Alfred · review_store — the manual approval gate (replaces the Telegram gate).

Nothing is applied or emailed until YOU approve it here, in chat or in a terminal.
Two separate decisions per job, both stored on disk so they survive any session:

    job decision    approved | skipped        data/job_decisions.json
    email decision  cleared  | cancelled      data/email_decisions.json

Approving a job approves the portal application. Its cold email needs its own
yes (`approve <id> --email`, or `email-send <id>` later), because the email goes
to a person and you should read it first.

Jobs reach the review list (data/review_queue.json) once they are evaluated,
tailored and fact-checked. Approved job ids go to data/approved_queue.json, the
only list the application agent acts on.

CLI (run with the venv python):
    review_store.py list                    jobs waiting for you, best score first
    review_store.py show <job_id>           report, CV, email draft for one job
    review_store.py approve <job_id> [--email]
    review_store.py skip <job_id>
    review_store.py email-send <job_id>     clear the email for sending
    review_store.py email-cancel <job_id>
    review_store.py edit-email <job_id> <file>   first line "Subject: ..." optional
    review_store.py queue                   approved, not yet applied
    review_store.py pause | resume          global stop for the application agent

Pure stdlib + paths.py. No network.
"""

from __future__ import annotations

import glob
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402

_DATA = paths.data_dir()
PAUSE_FLAG = paths.pause_flag()
APPROVED_QUEUE = paths.approved_queue_path()
REVIEW_QUEUE = paths.review_queue_path()
JOB_DECISIONS = paths.job_decisions_path()
EMAIL_DECISIONS = paths.email_decisions_path()
EMAIL_DRAFTS = paths.email_drafts_path()

_EMAIL_MESSAGE_FILE = "email_message.txt"


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json(path: str, value: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(value, fh, indent=2, sort_keys=True)
    os.replace(tmp, path)


def _home() -> str:
    return os.path.dirname(_DATA)


def _portable(path: str) -> str:
    """Store paths inside the Alfred home relative to it, so the store can move."""
    if not path:
        return path
    try:
        rel = os.path.relpath(os.path.abspath(path), _home())
    except ValueError:
        return path
    return path if rel.startswith(os.pardir) else rel


def _resolved(path: str) -> str:
    if not path or os.path.isabs(path):
        return path
    return os.path.join(_home(), path)


# ---------------------------------------------------------------------------
# /pause
# ---------------------------------------------------------------------------

def set_pause(paused: bool) -> None:
    os.makedirs(_DATA, exist_ok=True)
    if paused:
        with open(PAUSE_FLAG, "w", encoding="utf-8") as fh:
            fh.write("paused\n")
    elif os.path.exists(PAUSE_FLAG):
        os.remove(PAUSE_FLAG)


def is_paused() -> bool:
    return os.path.exists(PAUSE_FLAG)


# ---------------------------------------------------------------------------
# Review list — what is waiting for you
# ---------------------------------------------------------------------------

_REVIEW_KEYS = ("job_id", "source", "title", "company", "location", "url", "employer_url",
                "score", "recommendation", "legitimacy", "report", "tracker_num",
                "cv_pdf", "fact_check", "channel", "easy_apply", "contact_email",
                "email_source", "verified_mailbox", "repost", "liveness", "output_dir",
                "apply_url", "ats", "workplace", "workplace_type", "region")


def add_for_review(job: Dict[str, Any]) -> Dict[str, Any]:
    """Put one evaluated + tailored job on the review list (idempotent by job_id)."""
    job_id = job.get("job_id")
    if not job_id:
        raise ValueError("job has no job_id")
    store = _read_json(REVIEW_QUEUE, {})
    if not isinstance(store, dict):
        store = {}
    rec = {k: job.get(k) for k in _REVIEW_KEYS if job.get(k) is not None}
    for k in ("report", "cv_pdf", "output_dir"):
        if rec.get(k):
            rec[k] = _portable(rec[k])
    rec["queued_at"] = (store.get(job_id) or {}).get("queued_at") or _now_iso()
    store[job_id] = rec
    _write_json(REVIEW_QUEUE, store)
    return rec


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    store = _read_json(REVIEW_QUEUE, {})
    rec = store.get(job_id) if isinstance(store, dict) else None
    if not isinstance(rec, dict):
        return None
    rec = dict(rec)
    for k in ("report", "cv_pdf", "output_dir"):
        if rec.get(k):
            rec[k] = _resolved(rec[k])
    return rec


_INDIA_WORDS = ("india", "bengaluru", "bangalore", "mumbai", "pune", "gurugram", "gurgaon",
                "ahmedabad", "delhi", "noida", "hyderabad", "chennai", "kolkata", "jaipur",
                "kochi", "indore", "chandigarh")
_REMOTE_WORDS = ("remote", "anywhere", "work from home", "wfh", "distributed")
DEFAULT_PRIORITY = ("remote_abroad", "india", "onsite_abroad")


def location_bucket(job: Dict[str, Any]) -> str:
    """PURE: remote_abroad | india | onsite_abroad | unknown, from the job's own fields.

    Uses the finder's `workplace`/`region` tags when present, else the location text.
    A remote role that names India ("Remote, India") is `india`, not `remote_abroad`.
    """
    loc = str(job.get("location") or "").lower()
    workplace = str(job.get("workplace") or job.get("workplace_type") or "").lower()
    region = str(job.get("region") or "").lower()
    remote = "remote" in workplace or any(w in loc for w in _REMOTE_WORDS)
    in_india = region == "india" or (region != "abroad" and any(w in loc for w in _INDIA_WORDS))
    if in_india:
        return "india"
    if not loc and not workplace and not region:
        return "unknown"
    return "remote_abroad" if remote else "onsite_abroad"


def _priority_order() -> List[str]:
    try:
        import yaml
        with open(paths.search_config(), "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
        order = cfg.get("location_priority")
        if isinstance(order, list) and order:
            return [str(o) for o in order]
    except Exception:  # noqa: BLE001 — unreadable config falls back to the default order
        pass
    return list(DEFAULT_PRIORITY)


def _score(j: Dict[str, Any]) -> float:
    try:
        return float(str(j.get("score", "0")).split("/")[0])
    except ValueError:
        return 0.0


def pending_review(priority: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Jobs with no Approve/Skip yet, ordered by location priority, then best score.

    Default priority (config/search.yaml -> location_priority): remote jobs outside
    India, then India, then on-site abroad; jobs with no location signal come last.
    """
    store = _read_json(REVIEW_QUEUE, {})
    if not isinstance(store, dict):
        return []
    jobs = [get_job(j) for j in store if job_decision(j) is None]
    jobs = [j for j in jobs if j]
    order = list(priority or _priority_order())
    rank = {b: i for i, b in enumerate(order)}

    def key(j: Dict[str, Any]):
        return (rank.get(location_bucket(j), len(order)), -_score(j))
    return sorted(jobs, key=key)


# ---------------------------------------------------------------------------
# Job decision (portal application)
# ---------------------------------------------------------------------------

def record_job_decision(job_id: str, decision: str) -> bool:
    """First answer wins. Idempotent -> False if already decided."""
    if decision not in ("approved", "skipped"):
        raise ValueError(f"decision must be approved|skipped, got {decision!r}")
    store = _read_json(JOB_DECISIONS, {})
    if not isinstance(store, dict):
        store = {}
    if job_id in store:
        return False
    store[job_id] = {"decision": decision, "ts": _now_iso()}
    _write_json(JOB_DECISIONS, store)
    return True


def job_decision(job_id: str) -> Optional[str]:
    store = _read_json(JOB_DECISIONS, {})
    rec = store.get(job_id) if isinstance(store, dict) else None
    return rec.get("decision") if isinstance(rec, dict) else None


def approved_queue() -> List[str]:
    queue = _read_json(APPROVED_QUEUE, [])
    return [j for j in queue if isinstance(j, str)] if isinstance(queue, list) else []


def enqueue_approved(job_id: str) -> bool:
    queue = approved_queue()
    if job_id in queue:
        return False
    queue.append(job_id)
    _write_json(APPROVED_QUEUE, queue)
    return True


def remove_from_queue(job_id: str) -> bool:
    queue = approved_queue()
    if job_id not in queue:
        return False
    _write_json(APPROVED_QUEUE, [j for j in queue if j != job_id])
    return True


def is_approved(job_id: str) -> bool:
    return job_decision(job_id) == "approved" or job_id in approved_queue()


def approve(job_id: str, with_email: bool = False) -> Dict[str, Any]:
    if get_job(job_id) is None:
        return {"ok": False, "error": f"{job_id} is not on the review list"}
    prior = job_decision(job_id)
    if prior == "skipped":
        return {"ok": False, "error": f"{job_id} was already skipped"}
    record_job_decision(job_id, "approved")
    enqueue_approved(job_id)
    out: Dict[str, Any] = {"ok": True, "job_id": job_id, "portal": "approved"}
    if with_email:
        if load_draft(job_id) is None:
            out["email"] = "no email draft for this job"
        else:
            record_email_decision(job_id, "cleared")
            out["email"] = "cleared"
    return out


def skip(job_id: str) -> Dict[str, Any]:
    if job_decision(job_id) == "approved":
        return {"ok": False, "error": f"{job_id} was already approved"}
    record_job_decision(job_id, "skipped")
    remove_from_queue(job_id)
    if load_draft(job_id) is not None and email_decision(job_id) is None:
        record_email_decision(job_id, "cancelled")
    return {"ok": True, "job_id": job_id, "decision": "skipped"}


# ---------------------------------------------------------------------------
# Email drafts + email decision
# ---------------------------------------------------------------------------

def save_draft(job_id: str, to: str, subject: str, body: str,
               attachments: Optional[List[str]] = None,
               job: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    drafts = _read_json(EMAIL_DRAFTS, {})
    if not isinstance(drafts, dict):
        drafts = {}
    draft = {"to": to, "subject": subject, "body": body,
             "attachments": [_portable(a) for a in (attachments or [])],
             "updated_at": _now_iso()}
    if isinstance(job, dict):
        draft["job"] = {k: job.get(k) for k in ("job_id", "company", "title", "url")
                        if job.get(k) is not None}
    drafts[job_id] = draft
    _write_json(EMAIL_DRAFTS, drafts)
    return draft


def load_draft(job_id: str) -> Optional[Dict[str, Any]]:
    drafts = _read_json(EMAIL_DRAFTS, {})
    d = drafts.get(job_id) if isinstance(drafts, dict) else None
    if not isinstance(d, dict):
        return None
    d = dict(d)
    d["attachments"] = [_resolved(a) for a in (d.get("attachments") or [])]
    return d


def draft_job(job_id: str) -> Dict[str, Any]:
    d = load_draft(job_id) or {}
    return dict(d.get("job") or {"job_id": job_id})


def parse_email_text(raw: str) -> Dict[str, Optional[str]]:
    """`Subject: ...` on the first line (optional), the rest is the body."""
    text = (raw or "").strip()
    if not text:
        return {"subject": None, "body": ""}
    first, _, rest = text.partition("\n")
    if first.strip().lower().startswith("subject:"):
        return {"subject": first.split(":", 1)[1].strip() or None, "body": rest.strip()}
    return {"subject": None, "body": text}


def apply_edit(job_id: str, raw: str) -> Optional[Dict[str, Any]]:
    draft = load_draft(job_id)
    if draft is None:
        return None
    parsed = parse_email_text(raw)
    if not parsed["body"]:
        return None  # an empty edit is not an instruction to send an empty email
    return save_draft(job_id, draft["to"], parsed["subject"] or draft["subject"],
                      parsed["body"], draft.get("attachments"), draft.get("job"))


def resume_attachments(job: Dict[str, Any]) -> List[str]:
    """The tailored CV PDF for the email. Cover letters are not part of Alfred."""
    pdf = job.get("cv_pdf")
    if pdf and os.path.exists(_resolved(pdf)):
        return [_resolved(pdf)]
    out = job.get("output_dir")
    if out and os.path.isdir(_resolved(out)):
        found = sorted(glob.glob(os.path.join(_resolved(out), "*.pdf")))
        return found[:1]
    return []


def stage_email_draft(job: Dict[str, Any], subject: Optional[str] = None,
                      body: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Save the cold email for `job` from its output dir. None if there is no
    contact address or no email text. Never overwrites an edited draft."""
    job_id = job.get("job_id")
    to = (job.get("contact_email") or (job.get("email") or {}).get("address") or "").strip()
    if not job_id or not to:
        return None
    existing = load_draft(job_id)
    if existing is not None:
        return existing
    out = job.get("output_dir")
    if body is None and out:
        try:
            with open(os.path.join(_resolved(out), _EMAIL_MESSAGE_FILE), "r", encoding="utf-8") as fh:
                parsed = parse_email_text(fh.read())
            body, subject = parsed["body"], subject or parsed["subject"]
        except OSError:
            body = None
    if not body:
        return None  # never invent an email body
    subject = subject or f"Application: {job.get('title') or 'your open role'}"
    return save_draft(job_id, to, subject, body, resume_attachments(job), job)


def record_email_decision(job_id: str, decision: str) -> bool:
    if decision not in ("cleared", "cancelled"):
        raise ValueError(f"decision must be cleared|cancelled, got {decision!r}")
    store = _read_json(EMAIL_DECISIONS, {})
    if not isinstance(store, dict):
        store = {}
    if job_id in store:
        return False
    store[job_id] = {"decision": decision, "ts": _now_iso()}
    _write_json(EMAIL_DECISIONS, store)
    return True


def email_decision(job_id: str) -> Optional[str]:
    store = _read_json(EMAIL_DECISIONS, {})
    rec = store.get(job_id) if isinstance(store, dict) else None
    return rec.get("decision") if isinstance(rec, dict) else None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _line(j: Dict[str, Any]) -> str:
    flags = []
    if j.get("repost"):
        flags.append("repost")
    if j.get("fact_check") and j["fact_check"] != "pass":
        flags.append(f"facts:{j['fact_check']}")
    if j.get("contact_email"):
        flags.append("email" + ("?" if j.get("verified_mailbox") is False else ""))
    return (f"{str(j.get('score', '?')):>6}  [{location_bucket(j)}]  {j.get('job_id')}\n"
            f"        {j.get('title')} · {j.get('company')} · {j.get('location') or '—'}"
            f"{'  [' + ', '.join(flags) + ']' if flags else ''}")


def _cli(argv: List[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "list":
        jobs = pending_review()
        print(f"{len(jobs)} job(s) waiting for review" + (" — /pause is SET" if is_paused() else ""))
        for j in jobs:
            print(_line(j))
        return 0
    if cmd == "show" and rest:
        job = get_job(rest[0])
        if not job:
            print(f"not found: {rest[0]}")
            return 1
        print(json.dumps(job, indent=2))
        d = load_draft(rest[0])
        if d:
            print(f"\n--- email to {d['to']} ---\nSubject: {d['subject']}\n\n{d['body']}\n"
                  f"attachments: {[os.path.basename(a) for a in d['attachments']]}")
        return 0
    if cmd == "approve" and rest:
        print(json.dumps(approve(rest[0], with_email="--email" in rest), indent=2))
        return 0
    if cmd == "skip" and rest:
        print(json.dumps(skip(rest[0]), indent=2))
        return 0
    if cmd in ("email-send", "email-cancel") and rest:
        if load_draft(rest[0]) is None:
            print(f"no email draft for {rest[0]}")
            return 1
        changed = record_email_decision(rest[0], "cleared" if cmd == "email-send" else "cancelled")
        print(("recorded: " if changed else "already decided: ") + str(email_decision(rest[0])))
        return 0
    if cmd == "edit-email" and len(rest) >= 2:
        with open(rest[1], "r", encoding="utf-8") as fh:
            d = apply_edit(rest[0], fh.read())
        print("updated" if d else "no draft, or the new text was empty")
        return 0 if d else 1
    if cmd == "queue":
        for j in approved_queue():
            print(j)
        return 0
    if cmd == "pause":
        set_pause(True)
        print("paused — the application agent will not act")
        return 0
    if cmd == "resume":
        set_pause(False)
        print("resumed")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
