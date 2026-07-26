"""WarmApply · source adapter — We Work Remotely (RSS 2.0).

Read-only: fetch the public WWR RSS feed and normalize each <item> into the
canonical WarmApply job shape. WWR is a remote-only board, so results are relevant
regardless of the user's city locations.

Feed quirks handled:
  - <title> is "Company Name: Job Title" — split on the FIRST ": " (no colon →
    company null, title = whole string).
  - <region> → location (fallback "Remote"); <pubDate> is RFC-822 → YYYY-MM-DD.
  - <description> is HTML → tags stripped, first ~300 chars.
  - stable id from <guid> (or the link slug).

Split (mirrors remoteok.py):
  - fetch(roles, locations=None, timeout=15) -> list   # network (the ONLY I/O)
  - normalize(item) -> dict                             # pure
  - matches_roles(job, roles) -> bool                   # pure
  - normalize_feed(xml_text, roles) -> list             # pure (parse + filter)

RSS is parsed with stdlib xml.etree.ElementTree. Dependency: requests (already in
requirements.txt) + stdlib only. Any network/parse error → [].
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

import requests

FEED_URL = "https://weworkremotely.com/remote-jobs.rss"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 WarmApply/1.0 "
    "(+job-search; contact via app)"
)

SOURCE = "we_work_remotely"
_SNIPPET_LEN = 300


# ---------------------------------------------------------------------------
# Pure helpers (no network)
# ---------------------------------------------------------------------------

def _local(tag: str) -> str:
    """Local element name without any XML namespace prefix."""
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
    """RFC-822 pubDate → YYYY-MM-DD, or None if unparseable."""
    if not pubdate:
        return None
    try:
        return parsedate_to_datetime(str(pubdate)).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return None


def _slug(value: Optional[str]) -> str:
    """Last non-empty path segment of a URL/guid (query & trailing slash stripped)."""
    if not value:
        return ""
    v = str(value).split("?", 1)[0].split("#", 1)[0].rstrip("/")
    return v.rsplit("/", 1)[-1] if "/" in v else v


def split_company_title(raw_title: str):
    """"Company: Title" → (company, title). No colon → (None, whole string)."""
    raw_title = (raw_title or "").strip()
    if ": " in raw_title:
        company, title = raw_title.split(": ", 1)
        return company.strip() or None, title.strip()
    return None, raw_title


def normalize(item: Dict[str, Any]) -> Dict[str, Any]:
    """Map one parsed RSS item dict to the canonical WarmApply job shape."""
    company, title = split_company_title(item.get("title", ""))
    categories = item.get("categories") or []
    if not isinstance(categories, list):
        categories = [str(categories)]

    stable = _slug(item.get("guid") or item.get("link"))
    snippet = _strip_html(str(item.get("description") or ""))[:_SNIPPET_LEN]

    return {
        "job_id": f"{SOURCE}:{stable}",
        "source": SOURCE,
        "title": title,
        "company": company,
        "company_domain": None,
        "location": (item.get("region") or "").strip() or "Remote",
        "url": item.get("link"),
        "posted_date": _posted_date(item.get("pubDate")),
        "easy_apply": False,
        "description_snippet": snippet,
        "found_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "_categories": [str(c).lower() for c in categories],  # internal, role match
    }


def matches_roles(job: Dict[str, Any], roles: Optional[List[str]]) -> bool:
    """Case-insensitive match of any role across the job's title + categories.

    A role matches when all its word-tokens appear in the haystack, so
    "Product Designer" matches "Senior Product Designer". Empty roles → keep all.
    """
    if not roles:
        return True
    haystack = _tokens(job.get("title") or "")
    for cat in job.get("_categories", []):
        haystack |= _tokens(cat)
    for role in roles:
        rtokens = _tokens(role)
        if rtokens and rtokens <= haystack:
            return True
    return False


def _parse_items(xml_text: str) -> List[Dict[str, Any]]:
    """Parse RSS text into a list of item dicts (namespace-agnostic).

    Collects each <item>'s children by local tag name; multiple <category>
    elements are gathered into `categories`.
    """
    root = ET.fromstring(xml_text)
    items: List[Dict[str, Any]] = []
    for el in root.iter():
        if _local(el.tag) != "item":
            continue
        data: Dict[str, Any] = {"categories": []}
        for child in el:
            name = _local(child.tag)
            text = (child.text or "").strip()
            if name == "category":
                if text:
                    data["categories"].append(text)
            else:
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
            job.pop("_categories", None)
            jobs.append(job)
    return jobs


# ---------------------------------------------------------------------------
# Network fetch (the ONLY I/O). On any error → [].
# ---------------------------------------------------------------------------

def fetch(roles: Optional[List[str]] = None, locations: Optional[List[str]] = None,
          timeout: int = 15) -> List[Dict[str, Any]]:
    """Fetch the WWR RSS feed, normalize + role-filter. Read-only; [] on any error.

    `locations` is accepted for a uniform adapter signature but ignored — WWR is a
    remote-only board.
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
