"""WarmApply · source adapter — LinkedIn Feed Hunter (BROWSER source; pure normalizer).

WarmApply's signature feature. LinkedIn "we're hiring" posts don't go through job
portals — the poster wants a DM, a comment, or an email. So the job-finder subagent
scans the LinkedIn feed (in the user's logged-in Chrome), reads each hiring post, and
passes it to `normalize()` here, which produces a **lead**: the canonical job shape
PLUS outreach fields so the application-agent knows HOW to reach out.

This module is PURE — no network, no requests, no browsing. It is a browser source
(BROWSER=True), so source_dispatch skips it; the subagent drives Chrome.

Lead shape = canonical job shape + :
    outreach_method   "email" | "dm" | "comment" | "link"
    recruiter_name    poster's name (or null)
    recruiter_profile poster's profile URL (or null)
    contact_email     email stated in the post (or null)
Missing fields → null (never fabricated). stdlib only; no new dependency.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

SOURCE = "linkedin_feed"
BROWSER = True  # source_dispatch: skip Python fetch; the subagent browses instead.
_SNIPPET_LEN = 300

_OUTREACH_METHODS = ("email", "dm", "comment", "link")

# Detect an email address anywhere in the post text.
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-zA-Z#0-9]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokens(text: str) -> set:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def _slug(value: Optional[str]) -> str:
    if not value:
        return ""
    v = str(value).split("?", 1)[0].split("#", 1)[0].rstrip("/")
    return v.rsplit("/", 1)[-1] if "/" in v else v


def _email_in(text: str) -> Optional[str]:
    if not text:
        return None
    m = _EMAIL_RE.search(text)
    return m.group(0) if m else None


def decide_outreach_method(text: str, contact_email: Optional[str],
                           has_link: bool, explicit: Optional[str] = None) -> str:
    """Choose how to respond to a hiring post.

    Priority: an explicit, valid hint from the card → an email in the post → an
    application link → "comment below" → "DM me". Default to "dm" if unclear.
    Never invents contact details; only classifies the intended channel.
    """
    if explicit in _OUTREACH_METHODS:
        return explicit
    low = (text or "").lower()
    if contact_email or "email me" in low or "email your" in low or "send your" in low and "@" in low:
        return "email"
    if contact_email:
        return "email"
    if has_link or "apply here" in low or "application link" in low or "link in" in low:
        return "link"
    if "comment below" in low or "comment your" in low or "drop a comment" in low:
        return "comment"
    if "dm me" in low or "message me" in low or "reach out" in low or "inbox" in low:
        return "dm"
    return "dm"  # default when the post doesn't say


def normalize(raw_post: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize one scraped LinkedIn hiring post into a WarmApply lead.

    `raw_post` is whatever the subagent scraped, e.g.:
        {id/url, title/role, company, location, text/description,
         recruiter_name, recruiter_profile, email?, link?, outreach_method?}
    Unknown fields → null; never fabricate a company, email, or name.
    """
    raw_post = raw_post or {}
    stable = str(raw_post.get("id") or "").strip() or _slug(raw_post.get("url"))

    text = str(raw_post.get("text") or raw_post.get("description") or "")
    snippet = _strip_html(text)[:_SNIPPET_LEN]

    # contact_email: prefer an explicit field, else scan the post text.
    contact_email = (raw_post.get("email") or raw_post.get("contact_email") or "").strip() or None
    if not contact_email:
        contact_email = _email_in(text)

    has_link = bool((raw_post.get("link") or raw_post.get("apply_url") or "").strip())
    method = decide_outreach_method(text, contact_email, has_link,
                                    raw_post.get("outreach_method"))

    return {
        "job_id": f"{SOURCE}:{stable}",
        "source": SOURCE,
        "title": (raw_post.get("title") or raw_post.get("role") or "").strip() or None,
        "company": (raw_post.get("company") or "").strip() or None,   # never fabricate
        "company_domain": None,
        "location": (raw_post.get("location") or "").strip() or "Remote",
        "url": raw_post.get("url"),
        "posted_date": None,  # feed shows relative times; don't fabricate a date
        "easy_apply": False,
        "description_snippet": snippet,
        "outreach_method": method,
        "recruiter_name": (raw_post.get("recruiter_name") or "").strip() or None,
        "recruiter_profile": (raw_post.get("recruiter_profile") or "").strip() or None,
        "contact_email": contact_email,
        "found_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "_tags": [str(t).lower() for t in (raw_post.get("tags") or [])],  # role match
    }


def matches_roles(job: Dict[str, Any], roles: Optional[List[str]]) -> bool:
    """Case-insensitive match of any role across title + tags + the post snippet.

    Feed posts are free text, so the snippet is included in the haystack (a post may
    name the role only in the body). A role matches when all its tokens appear.
    """
    if not roles:
        return True
    haystack = _tokens(job.get("title") or "") | _tokens(job.get("description_snippet") or "")
    for tag in job.get("_tags", []):
        haystack |= _tokens(tag)
    for role in roles:
        rtokens = _tokens(role)
        if rtokens and rtokens <= haystack:
            return True
    return False


def normalize_posts(posts: List[Dict[str, Any]],
                    roles: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Normalize + role-filter a list of scraped posts (convenience for the subagent).

    Strips the internal `_tags` key from the returned lead objects.
    """
    leads = []
    for post in posts or []:
        lead = normalize(post)
        if matches_roles(lead, roles):
            lead.pop("_tags", None)
            leads.append(lead)
    return leads
