"""Alfred · source adapter — Jobspresso (WP Job Manager RSS).

Read-only: fetch the Jobspresso job feed and normalize each <item> into the
canonical Alfred job shape.

Live-feed structure (confirmed by inspection of https://jobspresso.co/?feed=job_feed):
  - Standard RSS 2.0 with a custom `job_listing` namespace (https://jobspresso.co/).
  - <title>            → the ROLE only (NOT "Role at Company"); used as-is.
  - <company>          → dedicated custom element (job_listing ns) — the reliable
                          company source. Absent/empty → company null (never guessed).
  - <location>         → custom element ("Worldwide", "USA", …); fallback "Remote".
  - <job_type>         → custom element; folded into the role-match haystack.
  - <pubDate>          → RFC-822 → YYYY-MM-DD.
  - <post-id>          → numeric WP id (stable); fallback to the <link> slug.
  - <description>      → HTML → stripped, first ~300 chars.

Split (mirrors weworkremotely.py):
  - fetch(roles, locations=None, timeout=15) -> list   # network (the ONLY I/O)
  - normalize(item) -> dict                             # pure
  - matches_roles(job, roles) -> bool                   # pure
  - normalize_feed(xml_text, roles) -> list             # pure (parse + filter)

RSS parsed with stdlib xml.etree.ElementTree. Dependency: requests + stdlib only.
Any network/parse error → [].
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

import requests

FEED_URL = "https://jobspresso.co/?feed=job_feed"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Alfred/1.0 "
    "(+job-search; contact via app)"
)

SOURCE = "jobspresso"
_SNIPPET_LEN = 300


# ---------------------------------------------------------------------------
# Pure helpers (no network)
# ---------------------------------------------------------------------------

def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-zA-Z#0-9]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokens(text: str) -> set:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def _posted_date(pubdate: Any) -> Optional[str]:
    if not pubdate:
        return None
    try:
        return parsedate_to_datetime(str(pubdate)).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return None


def _slug(value: Optional[str]) -> str:
    if not value:
        return ""
    v = str(value).split("?", 1)[0].split("#", 1)[0].rstrip("/")
    return v.rsplit("/", 1)[-1] if "/" in v else v


def normalize(item: Dict[str, Any]) -> Dict[str, Any]:
    """Map one parsed Jobspresso item dict to the canonical Alfred job shape."""
    # Stable id: prefer the numeric WP post-id, else the link slug.
    stable = (item.get("post-id") or "").strip() or _slug(item.get("link"))

    company = (item.get("company") or "").strip() or None  # never fabricate
    snippet = _strip_html(str(item.get("description") or ""))[:_SNIPPET_LEN]

    return {
        "job_id": f"{SOURCE}:{stable}",
        "source": SOURCE,
        "title": (item.get("title") or "").strip() or None,
        "company": company,
        "company_domain": None,
        "location": (item.get("location") or "").strip() or "Remote",
        "url": item.get("link"),
        "posted_date": _posted_date(item.get("pubDate")),
        "easy_apply": False,
        "description_snippet": snippet,
        "found_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "_job_type": (item.get("job_type") or "").strip(),  # internal, role match
    }


def matches_roles(job: Dict[str, Any], roles: Optional[List[str]]) -> bool:
    """Case-insensitive match of any role across the job's title + job_type.

    A role matches when all its word-tokens appear in the haystack, so
    "Product Designer" matches "Senior Product Designer". Empty roles → keep all.
    """
    if not roles:
        return True
    haystack = _tokens(job.get("title") or "") | _tokens(job.get("_job_type") or "")
    for role in roles:
        rtokens = _tokens(role)
        if rtokens and rtokens <= haystack:
            return True
    return False


def _parse_items(xml_text: str) -> List[Dict[str, Any]]:
    """Parse RSS text into item dicts (namespace-agnostic, by local tag name).

    The custom job_listing elements (company/location/job_type) and the WP
    <post-id> are captured by their local names alongside the standard fields.
    """
    root = ET.fromstring(xml_text)
    items: List[Dict[str, Any]] = []
    for el in root.iter():
        if _local(el.tag) != "item":
            continue
        data: Dict[str, Any] = {}
        for child in el:
            name = _local(child.tag)
            text = (child.text or "").strip()
            # Don't let an empty duplicate tag clobber a populated one.
            if name not in data or (not data.get(name) and text):
                data[name] = text
        items.append(data)
    return items


def normalize_feed(xml_text: str, roles: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Parse RSS text, normalize each item, filter by roles. [] on parse error."""
    try:
        items = _parse_items(xml_text)
    except ET.ParseError:
        return []
    jobs = []
    for item in items:
        if not item.get("title") and not item.get("link"):
            continue
        job = normalize(item)
        if matches_roles(job, roles):
            job.pop("_job_type", None)
            jobs.append(job)
    return jobs


# ---------------------------------------------------------------------------
# Network fetch (the ONLY I/O). On any error → [].
# ---------------------------------------------------------------------------

def fetch(roles: Optional[List[str]] = None, locations: Optional[List[str]] = None,
          timeout: int = 15) -> List[Dict[str, Any]]:
    """Fetch the Jobspresso job feed, normalize + role-filter. Read-only; [] on error.

    `locations` is accepted for a uniform adapter signature but ignored —
    Jobspresso is a remote-focused board.
    """
    try:
        resp = requests.get(FEED_URL, headers={"User-Agent": USER_AGENT,
                                               "Accept": "application/rss+xml, application/xml"},
                            timeout=timeout)
        resp.raise_for_status()
        xml_text = resp.text
    except requests.RequestException:
        return []
    return normalize_feed(xml_text, roles)
