"""Alfred · source adapter — LinkedIn Easy Apply (BROWSER source; pure normalizer).

LinkedIn's job search has no public API, so this is a browser source: the job-finder
subagent drives a browser carrying the user's signed-in LinkedIn session, reads the
rendered job cards, and passes each card's fields to `normalize()` here. This module
is PURE — no network, no requests, no browsing.

Distinct from `linkedin_feed`: that one hunts "we're hiring" POSTS and produces
outreach leads. This one reads real job POSTINGS from `/jobs/search`, and its whole
point is the `easy_apply` flag — a posting Alfred can submit through LinkedIn's own
modal rather than a company portal.

LinkedIn is aggressively anti-bot and login-gated, so the subagent must browse gently
and skip on any CAPTCHA / login wall / block (see agents/job-finder.md). This module
just keeps the scraped output consistent + offline-testable.

Browser-source contract (mirrors indeed.py / wellfound.py):
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

SOURCE = "linkedin_easy_apply"
BROWSER = True  # source_dispatch: skip Python fetch; the subagent browses instead.
_SNIPPET_LEN = 300

# Strings LinkedIn renders on an Easy Apply button, lower-cased. A card is only
# marked easy_apply when the scrape actually saw one of these (or passed an
# explicit boolean) — absence is False, never a guess.
_EASY_APPLY_MARKERS = ("easy apply", "easyapply", "simple apply")


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


def _job_id_from_url(url: Optional[str]) -> str:
    """Extract LinkedIn's numeric job id from any posting URL form.

    Handles `/jobs/view/4012345678/`, `/jobs/view/some-slug-4012345678`, and the
    `?currentJobId=4012345678` used by the split-pane search UI.
    """
    if not url:
        return ""
    u = str(url)
    m = re.search(r"/jobs/view/(?:[^/?#]*?-)?(\d{6,})", u)
    if m:
        return m.group(1)
    m = re.search(r"[?&]currentJobId=(\d{6,})", u)
    return m.group(1) if m else ""


def clean_job_url(url: Optional[str]) -> Optional[str]:
    """Return a SPECIFIC LinkedIn posting URL, or None for a search/list URL.

    A `/jobs/search` or `/jobs/collections` link describes a query, not a job, and
    storing one sends every downstream agent to the wrong page. When such a URL
    carries `currentJobId`, the specific posting it is showing is recoverable, so
    rebuild the canonical `/jobs/view/<id>/` form rather than discarding the card.
    """
    if not url:
        return None
    u = str(url).strip()
    if not u:
        return None
    job_id = _job_id_from_url(u)
    low = u.lower()
    if "/jobs/view/" in low and job_id:
        return u
    if job_id:  # a search/collections URL that names the job it is displaying
        return f"https://www.linkedin.com/jobs/view/{job_id}/"
    return None  # a bare search with no job id → never store a wrong link


def is_easy_apply(raw_card: Dict[str, Any]) -> bool:
    """True only when the scrape actually observed an Easy Apply affordance.

    Accepts an explicit boolean from the scraper, or the button/label text seen on
    the card. Anything else is False: claiming Easy Apply on a posting that in fact
    routes to a company portal would send the application-agent down a path that
    does not exist.
    """
    raw_card = raw_card or {}
    explicit = raw_card.get("easy_apply")
    if isinstance(explicit, bool):
        return explicit
    haystack = " ".join(
        str(raw_card.get(k) or "")
        for k in ("apply_label", "apply_button", "badge", "labels", "footer")
    ).lower()
    return any(marker in haystack for marker in _EASY_APPLY_MARKERS)


def _posted_date(value: Any) -> Optional[str]:
    """Pass through an ISO date → YYYY-MM-DD; relative text ("3 days ago") → None.

    LinkedIn cards show relative ages, so we never fabricate an absolute date. The
    subagent resolves the relative label itself when applying `max_age_days`.
    """
    if not value:
        return None
    s = str(value).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return None


def normalize(raw_card: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize one scraped LinkedIn job card into the canonical job shape.

    `raw_card` is whatever the subagent scraped, e.g.:
        {id|job_id|urn, title, company, location, url, posted, snippet/description,
         easy_apply|apply_label, workplace_type}
    Stable id from the numeric posting id. Missing company → null (never fabricated).
    """
    raw_card = raw_card or {}
    job_id = (str(raw_card.get("id") or raw_card.get("job_id") or "").strip()
              or _job_id_from_url(raw_card.get("url")))
    if not job_id:
        # A URN like "urn:li:jobPosting:4012345678" is the other id LinkedIn exposes.
        m = re.search(r"(\d{6,})", str(raw_card.get("urn") or ""))
        job_id = m.group(1) if m else ""

    company = (raw_card.get("company") or "").strip() or None  # never fabricate
    desc = raw_card.get("description")
    if desc is None:
        desc = raw_card.get("snippet")
    snippet = _strip_html(str(desc or ""))[:_SNIPPET_LEN]

    location = (raw_card.get("location") or "").strip()
    workplace = (raw_card.get("workplace_type") or "").strip()
    if workplace and workplace.lower() not in location.lower():
        location = f"{location} ({workplace})" if location else workplace

    return {
        "job_id": f"{SOURCE}:{job_id}",
        "source": SOURCE,
        "title": (raw_card.get("title") or "").strip() or None,
        "company": company,
        "company_domain": None,
        "location": location or "Remote",
        "url": clean_job_url(raw_card.get("url")),
        "posted_date": _posted_date(raw_card.get("posted") or raw_card.get("posted_date")),
        "easy_apply": is_easy_apply(raw_card),
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
                    roles: Optional[List[str]] = None,
                    *, easy_apply_only: bool = True) -> List[Dict[str, Any]]:
    """Normalize + role-filter a list of scraped cards (convenience for the subagent).

    Drops any card with no recoverable posting id — an unidentifiable listing cannot
    be de-duped or applied to. With `easy_apply_only` (the default, and the point of
    this source) also drops postings that carry no Easy Apply affordance; pass False
    to keep every matching LinkedIn posting regardless of apply route.
    Strips the internal `_tags` key from the returned canonical objects.
    """
    jobs = []
    for card in cards or []:
        job = normalize(card)
        if job["job_id"] == f"{SOURCE}:":
            continue
        if easy_apply_only and not job["easy_apply"]:
            continue
        if matches_roles(job, roles):
            job.pop("_tags", None)
            jobs.append(job)
    return jobs
