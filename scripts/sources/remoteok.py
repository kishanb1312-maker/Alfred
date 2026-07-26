"""WarmApply · source adapter — RemoteOK (https://remoteok.com/api).

Read-only: fetch the public RemoteOK JSON feed and normalize each listing into the
canonical WarmApply job shape. Remote-only board, so `location` is effectively
"Remote"; results are filtered by the user's `roles`.

Endpoint returns a JSON ARRAY whose FIRST element is legal/metadata — it is
skipped. A real browser-like User-Agent is required (the API blocks the default
python-requests UA). Any network/parse error → return [] so the run continues.

Split into:
  - fetch(roles, locations=None, timeout=15) -> list   # network (the ONLY I/O)
  - normalize(raw) -> dict                              # pure
  - matches_roles(job, roles) -> bool                   # pure
  - normalize_feed(feed, roles) -> list                 # pure (skip meta + filter)

Dependency: requests (already in requirements.txt). No new dependency.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

API_URL = "https://remoteok.com/api"

# A real, descriptive User-Agent (RemoteOK rejects the default requests UA).
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 WarmApply/1.0 "
    "(+job-search; contact via app)"
)

SOURCE = "remoteok"
_SNIPPET_LEN = 300


# ---------------------------------------------------------------------------
# Pure helpers (no network)
# ---------------------------------------------------------------------------

def _strip_html(text: str) -> str:
    """Best-effort tag/entity strip for the description snippet."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)          # drop tags
    text = re.sub(r"&[a-zA-Z#0-9]+;", " ", text)  # drop entities
    return re.sub(r"\s+", " ", text).strip()


def _posted_date(raw_date: Any) -> Optional[str]:
    """Return YYYY-MM-DD from RemoteOK's `date` (ISO string) if parseable."""
    if not raw_date:
        return None
    s = str(raw_date)
    # RemoteOK dates look like "2026-07-20T12:00:00+00:00"; take the date part.
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return None


def _tokens(text: str) -> set:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def normalize(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Map one RemoteOK job object to the canonical WarmApply job shape."""
    job_id = raw.get("id")
    tags = raw.get("tags") or []
    if not isinstance(tags, list):
        tags = []

    desc = _strip_html(str(raw.get("description") or ""))
    snippet = desc[:_SNIPPET_LEN]
    if tags:
        snippet = (snippet + "  · tags: " + ", ".join(str(t) for t in tags)).strip()

    return {
        "job_id": f"{SOURCE}:{job_id}",
        "source": SOURCE,
        "title": raw.get("position") or raw.get("title"),
        "company": raw.get("company"),
        "company_domain": None,
        "location": raw.get("location") or "Remote",
        "url": raw.get("url"),
        "posted_date": _posted_date(raw.get("date")),
        "easy_apply": False,
        "description_snippet": snippet,
        "found_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "_tags": [str(t).lower() for t in tags],   # internal, used for role match
    }


def matches_roles(job: Dict[str, Any], roles: Optional[List[str]]) -> bool:
    """Case-insensitive match of any role across the job's title + tags.

    A role matches when all of its word-tokens appear in the haystack (title +
    tags), so "Product Designer" matches "Senior Product Designer". Empty/None
    roles → keep everything.
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


def normalize_feed(feed: List[Any], roles: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Skip the metadata element, normalize each job, filter by roles.

    Strips the internal `_tags` key from the returned canonical objects.
    """
    if not isinstance(feed, list) or len(feed) == 0:
        return []
    jobs = []
    for raw in feed[1:]:                       # element 0 is legal/metadata
        if not isinstance(raw, dict) or raw.get("id") is None:
            continue
        job = normalize(raw)
        if matches_roles(job, roles):
            job.pop("_tags", None)
            jobs.append(job)
    return jobs


# ---------------------------------------------------------------------------
# Network fetch (the ONLY I/O). On any error → [].
# ---------------------------------------------------------------------------

def fetch(roles: Optional[List[str]] = None, locations: Optional[List[str]] = None,
          timeout: int = 15) -> List[Dict[str, Any]]:
    """Fetch RemoteOK, normalize + role-filter. Read-only; [] on any error.

    `locations` is accepted for a uniform adapter signature but ignored —
    RemoteOK is a remote-only board.
    """
    try:
        resp = requests.get(API_URL, headers={"User-Agent": USER_AGENT,
                                              "Accept": "application/json"},
                            timeout=timeout)
        resp.raise_for_status()
        feed = resp.json()
    except (requests.RequestException, ValueError):
        return []
    return normalize_feed(feed, roles)
