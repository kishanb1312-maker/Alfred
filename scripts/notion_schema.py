"""Alfred · notion_schema — single source of truth for the Notion tracker.

Pure and offline (stdlib only). Three responsibilities:
  - database_schema() -> Notion PROPERTY DEFINITIONS (for create-database).
  - row_properties(job) -> Notion PROPERTY VALUES for one enriched+tailored job
    (for create-page / update-page).
  - job_from_row(row) -> the INVERSE: a Notion row back into a job dict.

The inverse exists because Notion is the only durable record of a job's recruiter
address and tailored file paths — the enriched job object itself lives in the agent
turn that built it and is gone by the next run. Rehydrating from Notion is what lets
Alfred stage (and email) a job prepared days ago without re-running the pipeline.

Both derive their property NAMES from the same PROPERTIES table, so names can
never drift between the schema and the row mapping. The tracker subagent and any
later updater import from here rather than hard-coding strings.

No network, no Notion/MCP calls — this module only shapes dicts.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Property names (THE single source of truth). Change a name here → it changes
# everywhere. Referenced as constants so typos surface at import time.
# ---------------------------------------------------------------------------

COMPANY = "Company"
WEBSITE = "Website"
ROLE = "Role"
LOCATION = "Location"
JOB_LINK = "Job Link"
MATCH_SCORE = "Match Score"
CHANNEL = "Channel"
HR_NAME = "HR Name"
HR_EMAIL = "HR Email"
EMAIL_CONFIDENCE = "Email Confidence"
EMAIL_SOURCE = "Email Source"
RESUME_FILE = "Resume File"
COVER_LETTER_FILE = "Cover Letter File"
WHAT_I_CHANGED = "What I Changed"
STATUS = "Status"
JOB_ID = "Job ID"
APPLIED_DATE = "Applied Date"
REPLY = "Reply"
FOLLOW_UP_SENT = "Follow-up Sent"
COLD_EMAILED = "Cold Emailed"   # dual-channel: an email was sent for this job
BOUNCED = "Bounced"             # the cold email bounced (mailer-daemon)

# Ordered list (drives both the schema and the completeness check).
PROPERTIES: List[str] = [
    COMPANY, WEBSITE, ROLE, LOCATION, JOB_LINK, MATCH_SCORE, CHANNEL,
    HR_NAME, HR_EMAIL, EMAIL_CONFIDENCE, EMAIL_SOURCE, RESUME_FILE,
    COVER_LETTER_FILE, WHAT_I_CHANGED, STATUS, JOB_ID, APPLIED_DATE,
    REPLY, FOLLOW_UP_SENT, COLD_EMAILED, BOUNCED,
]

# Controlled vocabularies for the select properties.
# Channel is a MULTI-select now: a job can be BOTH portal and email (dual-channel).
CHANNEL_OPTIONS = ["portal", "email"]
EMAIL_SOURCE_OPTIONS = ["career-page", "hunter", "apollo", "linkedin", "pattern", "none"]
STATUS_OPTIONS = ["New", "Ready for Review", "Approved", "Applied", "Skipped"]

DEFAULT_STATUS = "Ready for Review"

# Notion hard limit: a single rich_text/text content chunk is max 2000 chars.
_RICH_TEXT_LIMIT = 2000


# ---------------------------------------------------------------------------
# database_schema() — property DEFINITIONS (create-database payload shape)
# ---------------------------------------------------------------------------

def _select_def(options: List[str]) -> Dict[str, Any]:
    return {"select": {"options": [{"name": o} for o in options]}}


def _multi_select_def(options: List[str]) -> Dict[str, Any]:
    return {"multi_select": {"options": [{"name": o} for o in options]}}


def database_schema() -> Dict[str, Dict[str, Any]]:
    """Return the Notion property definitions for the Alfred database.

    Shape matches Notion's `properties` object for create-database. Exactly one
    `title` property (Company), as Notion requires.
    """
    return {
        COMPANY: {"title": {}},
        WEBSITE: {"url": {}},
        ROLE: {"rich_text": {}},
        LOCATION: {"rich_text": {}},
        JOB_LINK: {"url": {}},
        MATCH_SCORE: {"number": {"format": "number"}},
        CHANNEL: _multi_select_def(CHANNEL_OPTIONS),  # dual-channel: portal AND/OR email
        HR_NAME: {"rich_text": {}},
        HR_EMAIL: {"email": {}},
        EMAIL_CONFIDENCE: {"number": {"format": "number"}},
        EMAIL_SOURCE: _select_def(EMAIL_SOURCE_OPTIONS),
        RESUME_FILE: {"rich_text": {}},
        COVER_LETTER_FILE: {"rich_text": {}},
        WHAT_I_CHANGED: {"rich_text": {}},
        STATUS: _select_def(STATUS_OPTIONS),
        JOB_ID: {"rich_text": {}},
        APPLIED_DATE: {"date": {}},
        REPLY: {"checkbox": {}},
        FOLLOW_UP_SENT: {"checkbox": {}},
        COLD_EMAILED: {"checkbox": {}},
        BOUNCED: {"checkbox": {}},
    }


# ---------------------------------------------------------------------------
# Notion property-VALUE builders (create-page / update-page payload shape)
# ---------------------------------------------------------------------------

def _title(text: Optional[str]) -> Dict[str, Any]:
    text = (text or "").strip()
    return {"title": [{"text": {"content": text}}] if text else []}


def _rich_text(text: Optional[str]) -> Dict[str, Any]:
    text = "" if text is None else str(text)
    if len(text) > _RICH_TEXT_LIMIT:
        text = text[: _RICH_TEXT_LIMIT - 1] + "…"  # ellipsis
    return {"rich_text": [{"text": {"content": text}}] if text else []}


def _url(value: Optional[str]) -> Dict[str, Any]:
    value = (value or "").strip()
    return {"url": value or None}


def _email(value: Optional[str]) -> Dict[str, Any]:
    value = (value or "").strip()
    return {"email": value or None}


def _number(value: Optional[Any]) -> Dict[str, Any]:
    if value is None or value == "":
        return {"number": None}
    try:
        return {"number": float(value) if not float(value).is_integer() else int(value)}
    except (TypeError, ValueError):
        return {"number": None}


def _select(value: Optional[str]) -> Dict[str, Any]:
    value = (value or "").strip()
    return {"select": {"name": value} if value else None}


def _multi_select(values: List[str]) -> Dict[str, Any]:
    clean = [v.strip() for v in (values or []) if v and v.strip()]
    return {"multi_select": [{"name": v} for v in clean]}


def _date(value: Optional[str]) -> Dict[str, Any]:
    value = (value or "").strip() if isinstance(value, str) else value
    return {"date": {"start": value} if value else None}


def _checkbox(value: Any) -> Dict[str, Any]:
    return {"checkbox": bool(value)}


# ---------------------------------------------------------------------------
# row_properties(job) — map an enriched+tailored job to Notion property values
# ---------------------------------------------------------------------------

def _resolve_email(job: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve the dual-channel email fields, backward-compatible with the old
    `job["email"]` block. Returns {address, source, confidence, recipient_name,
    verified_mailbox, cold_email}."""
    email = job.get("email") or {}
    address = job.get("contact_email") or email.get("address") or None
    source = job.get("email_source") or email.get("source") or ("none" if not address else "career-page")
    if "cold_email" in job:
        cold = bool(job.get("cold_email"))
    else:
        cold = bool(address and source != "none")
    return {
        "address": address,
        "source": source if address else "none",
        "confidence": email.get("confidence"),
        "recipient_name": email.get("recipient_name") or job.get("recruiter_name"),
        "verified_mailbox": job.get("verified_mailbox", email.get("verified")),
        "cold_email": cold,
    }


def _derive_channels(job: Dict[str, Any], resolved_email: Dict[str, Any]) -> List[str]:
    """Dual-channel: portal is always on for a surviving job; email if a cold email
    will go out. Returns a multi_select list like ["portal", "email"]."""
    channels: List[str] = []
    if job.get("apply_portal", True):
        channels.append("portal")
    if resolved_email.get("cold_email"):
        channels.append("email")
    return channels or ["portal"]


def row_properties(job: Dict[str, Any],
                   status: str = DEFAULT_STATUS) -> Dict[str, Dict[str, Any]]:
    """Map one enriched+tailored job dict to Notion property VALUES.

    Always emits ALL properties (null-valued where not yet known), so the row is
    schema-complete and later updates only need to change specific fields.

    Expected job shape (best-effort; missing keys degrade to null):
        job["company"], job["title"], job["location"], job["url"], job["job_id"]
        job["company_analysis"]["website"]
        job["match"]["score"]
        job["email"] = {address, recipient_name, confidence, source}
        job["files"] = {resume, cover_letter}   # local paths in output/
        job["what_i_changed"]                    # text (from what_i_changed.md)
    """
    company_analysis = job.get("company_analysis") or {}
    match = job.get("match") or {}
    files = job.get("files") or {}
    email = _resolve_email(job)

    website = company_analysis.get("website") or job.get("company_domain")

    return {
        COMPANY: _title(job.get("company")),
        WEBSITE: _url(website),
        ROLE: _rich_text(job.get("title")),
        LOCATION: _rich_text(job.get("location")),
        JOB_LINK: _url(job.get("url")),
        MATCH_SCORE: _number(match.get("score")),
        CHANNEL: _multi_select(_derive_channels(job, email)),
        HR_NAME: _rich_text(email.get("recipient_name")),
        HR_EMAIL: _email(email.get("address")),
        EMAIL_CONFIDENCE: _number(email.get("confidence")),
        EMAIL_SOURCE: _select(email.get("source") or "none"),
        RESUME_FILE: _rich_text(files.get("resume") or job.get("resume_file")),
        COVER_LETTER_FILE: _rich_text(
            files.get("cover_letter") or job.get("cover_letter_file")),
        WHAT_I_CHANGED: _rich_text(job.get("what_i_changed")),
        STATUS: _select(status),
        JOB_ID: _rich_text(job.get("job_id")),
        APPLIED_DATE: _date(job.get("applied_date")),
        REPLY: _checkbox(job.get("reply", False)),
        FOLLOW_UP_SENT: _checkbox(job.get("follow_up_sent", False)),
        COLD_EMAILED: _checkbox(email.get("cold_email")),
        BOUNCED: _checkbox(job.get("bounced", False)),
    }


# ---------------------------------------------------------------------------
# job_from_row(row) — the INVERSE of row_properties
# ---------------------------------------------------------------------------

def _read_text(prop: Optional[Dict[str, Any]]) -> Optional[str]:
    """Plain text out of a Notion title/rich_text property value."""
    if not isinstance(prop, dict):
        return None
    for key in ("title", "rich_text"):
        chunks = prop.get(key)
        if isinstance(chunks, list):
            text = "".join(
                (c.get("plain_text") or (c.get("text") or {}).get("content") or "")
                for c in chunks if isinstance(c, dict))
            return text or None
    return None


def _read_scalar(prop: Optional[Dict[str, Any]], key: str) -> Optional[Any]:
    return prop.get(key) if isinstance(prop, dict) else None


def _read_select(prop: Optional[Dict[str, Any]]) -> Optional[str]:
    sel = _read_scalar(prop, "select")
    return sel.get("name") if isinstance(sel, dict) else None


def _read_multi_select(prop: Optional[Dict[str, Any]]) -> List[str]:
    items = _read_scalar(prop, "multi_select")
    return [i.get("name") for i in items
            if isinstance(i, dict) and i.get("name")] if isinstance(items, list) else []


def job_from_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Rebuild a job dict from one Notion page (or its bare `properties` map).

    Best-effort and lossless where it matters: the Job ID, the recruiter address and
    the tailored file paths — everything needed to stage an email draft and preview it.
    `status` rides along so a caller can tell an already-Approved job from a new one.

    Accepts either a full page object or just its properties, because Notion's query
    and fetch responses differ in shape and neither is worth making the caller unwrap.
    """
    props = row.get("properties") if isinstance(row.get("properties"), dict) else row
    props = props if isinstance(props, dict) else {}

    address = _read_scalar(props.get(HR_EMAIL), "email")
    channels = _read_multi_select(props.get(CHANNEL))
    resume = _read_text(props.get(RESUME_FILE))
    cover = _read_text(props.get(COVER_LETTER_FILE))
    website = _read_scalar(props.get(WEBSITE), "url")

    return {
        "job_id": _read_text(props.get(JOB_ID)),
        "company": _read_text(props.get(COMPANY)),
        "title": _read_text(props.get(ROLE)),
        "location": _read_text(props.get(LOCATION)),
        "url": _read_scalar(props.get(JOB_LINK), "url"),
        "notion_url": row.get("url") if isinstance(row.get("url"), str) else None,
        "company_analysis": {"website": website} if website else None,
        "match": {"score": _read_scalar(props.get(MATCH_SCORE), "number")},
        "email": {
            "address": address,
            "recipient_name": _read_text(props.get(HR_NAME)),
            "confidence": _read_scalar(props.get(EMAIL_CONFIDENCE), "number"),
            "source": _read_select(props.get(EMAIL_SOURCE)) or ("none" if not address else None),
        },
        "channel": "email" if "email" in channels else "portal",
        "files": {"resume": resume, "cover_letter": cover},
        "what_i_changed": _read_text(props.get(WHAT_I_CHANGED)),
        "status": _read_select(props.get(STATUS)),
        "cold_emailed": bool(_read_scalar(props.get(COLD_EMAILED), "checkbox")),
    }


def jobs_from_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """`job_from_row` over a query result, dropping rows with no Job ID — a row Alfred
    cannot key on is one it cannot stage, enqueue, or avoid emailing twice."""
    jobs = [job_from_row(r) for r in rows or [] if isinstance(r, dict)]
    return [j for j in jobs if j.get("job_id")]
