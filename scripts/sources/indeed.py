"""Alfred · source adapter — Indeed (BROWSER source; pure normalizer).

Indeed is a browser source (like Wellfound): the job-finder subagent drives the
a browser carrying the user's signed-in session (whichever the host
provides), reads the rendered job cards, and
passes each card's fields to `normalize()` here. This module is PURE — no network,
no requests, no browsing.

Indeed is the MOST anti-bot-aggressive source, so the subagent must browse gently
and skip on any CAPTCHA/block (see agents/job-finder.md). This module just
keeps the scraped output consistent + offline-testable.

Browser-source contract (mirrors wellfound.py):
    SOURCE: str
    BROWSER = True
    normalize(raw_card: dict) -> dict
    matches_roles(job: dict, roles) -> bool
There is intentionally NO fetch() — source_dispatch skips BROWSER modules. stdlib
only; no new dependency.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

SOURCE = "indeed"
BROWSER = True  # source_dispatch: skip Python fetch; the subagent browses instead.
_SNIPPET_LEN = 300


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


def _jobkey_from_url(url: Optional[str]) -> str:
    """Extract Indeed's jobkey from a viewjob URL (?jk=... or &jk=...)."""
    if not url:
        return ""
    m = re.search(r"[?&]jk=([A-Za-z0-9]+)", str(url))
    return m.group(1) if m else ""


def _posted_date(value: Any) -> Optional[str]:
    """Pass through an ISO date → YYYY-MM-DD; relative text ("3 days ago") → None.

    Indeed shows relative dates on cards, so we never fabricate an absolute date.
    """
    if not value:
        return None
    s = str(value).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return None


def normalize(raw_card: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize one scraped Indeed card into the canonical job shape.

    `raw_card` is whatever the subagent scraped, e.g.:
        {jobkey|jk|id, title, company, location, url, posted, snippet/description}
    Stable id from the jobkey (data-jk / jk= in the URL). Missing company → null.
    """
    raw_card = raw_card or {}
    jobkey = (str(raw_card.get("jobkey") or raw_card.get("jk") or raw_card.get("id") or "").strip()
              or _jobkey_from_url(raw_card.get("url")))

    company = (raw_card.get("company") or "").strip() or None  # never fabricate
    desc = raw_card.get("description")
    if desc is None:
        desc = raw_card.get("snippet")
    snippet = _strip_html(str(desc or ""))[:_SNIPPET_LEN]

    return {
        "job_id": f"{SOURCE}:{jobkey}",
        "source": SOURCE,
        "title": (raw_card.get("title") or "").strip() or None,
        "company": company,
        "company_domain": None,
        "location": (raw_card.get("location") or "").strip() or "Remote",
        "url": raw_card.get("url"),
        "posted_date": _posted_date(raw_card.get("posted") or raw_card.get("posted_date")),
        "easy_apply": False,
        "description_snippet": snippet,
        "found_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "_tags": [str(t).lower() for t in (raw_card.get("tags") or [])],  # role match
    }


def matches_roles(job: Dict[str, Any], roles: Optional[List[str]]) -> bool:
    """Case-insensitive match of any role across the job's title + tags.

    A role matches when all its word-tokens appear in the haystack, so
    "Product Designer" matches "Senior Product Designer". Empty roles → keep all.
    """
    if not roles:
        return True
    haystack = _tokens(job.get("title") or "")
    for tag in job.get("_tags", []):
        haystack |= _tokens(tag)
    for role in roles:
        rtokens = _tokens(role)
        if rtokens and rtokens <= haystack:
            return True
    return False


def normalize_cards(cards: List[Dict[str, Any]],
                    roles: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Normalize + role-filter a list of scraped cards (convenience for the subagent).

    Strips the internal `_tags` key from the returned canonical objects.
    """
    jobs = []
    for card in cards or []:
        job = normalize(card)
        if matches_roles(job, roles):
            job.pop("_tags", None)
            jobs.append(job)
    return jobs
