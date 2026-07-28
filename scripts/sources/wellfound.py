"""WarmApply · source adapter — Wellfound (BROWSER source; pure normalizer).

Wellfound (formerly AngelList Talent) has NO API or RSS — it's a login-gated JS
app. So it is WarmApply's first **browser source**: the job-finder subagent drives
the user's logged-in Chrome (Claude-in-Chrome MCP), reads the rendered job cards,
and passes each card's fields to `normalize()` here.

This module is therefore PURE — no network, no requests, no browsing. It only:
  - declares the source as browser-driven (SOURCE, BROWSER=True),
  - normalizes one scraped card dict → canonical WarmApply job shape,
  - offers the same role matcher the Python adapters use.

The reusable browser-source contract (Indeed, LinkedIn will reuse it):
    SOURCE: str
    BROWSER = True
    normalize(raw_card: dict) -> dict
    matches_roles(job: dict, roles) -> bool
There is intentionally NO fetch() — source_dispatch skips BROWSER modules and the
subagent supplies the cards. stdlib only; no new dependency.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

SOURCE = "wellfound"
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


def _slug(value: Optional[str]) -> str:
    """Last non-empty path segment of a URL (query & trailing slash stripped)."""
    if not value:
        return ""
    v = str(value).split("?", 1)[0].split("#", 1)[0].rstrip("/")
    return v.rsplit("/", 1)[-1] if "/" in v else v


def clean_job_url(url: Optional[str]) -> Optional[str]:
    """Return a SPECIFIC Wellfound job URL, or None if it's a role-list/search URL.

    Rejects (→ None): a role search (`/role/`), a location list (`/l/`), or a bare
    `/jobs` with no specific id. Keeps a specific posting such as
    `wellfound.com/jobs/<id>-<slug>` or `wellfound.com/company/<slug>/jobs/<id>...`
    (identified by a `/jobs/<segment>` where the segment contains a digit id).
    """
    if not url:
        return None
    u = str(url).strip()
    if not u:
        return None
    low = u.lower()
    if "/role/" in low or "/l/" in low:
        return None
    m = re.search(r"/jobs/([^/?#]+)", low)
    if m and re.search(r"\d", m.group(1)):
        return u
    return None  # /jobs search with no id, or unrecognized → never store a wrong link


def _posted_date(value: Any) -> Optional[str]:
    """Pass through an ISO date (YYYY-MM-DD...) → YYYY-MM-DD; else None.

    Wellfound cards often show relative text ("3 days ago"); the subagent should
    resolve those to a date when it can, but we never fabricate one here.
    """
    if not value:
        return None
    s = str(value).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return None


def normalize(raw_card: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize one scraped Wellfound card into the canonical job shape.

    `raw_card` is whatever the subagent scraped, e.g.:
        {title, company, location, url, posted, snippet/description, id?}
    Missing company → null (never fabricated). Stable id from an explicit `id`,
    else the URL slug.
    """
    raw_card = raw_card or {}

    # url = the SPECIFIC job posting URL; reject role-list/search URLs so we never
    # store the link used to *find* jobs. Never fabricate one.
    job_url = clean_job_url(raw_card.get("url"))
    seg = ""
    if job_url:
        m = re.search(r"/jobs/([^/?#]+)", job_url)
        seg = m.group(1) if m else ""
    stable = str(raw_card.get("id") or "").strip() or seg or (_slug(job_url) if job_url else "")

    company = (raw_card.get("company") or "").strip() or None  # never fabricate
    desc = raw_card.get("description")
    if desc is None:
        desc = raw_card.get("snippet")
    snippet = _strip_html(str(desc or ""))[:_SNIPPET_LEN]

    return {
        "job_id": f"{SOURCE}:{stable}",
        "source": SOURCE,
        "title": (raw_card.get("title") or "").strip() or None,
        "company": company,
        "company_domain": None,
        "location": (raw_card.get("location") or "").strip() or "Remote",
        "url": job_url,  # the specific job posting URL, or null (never a role-list URL)
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
