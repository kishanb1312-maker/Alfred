"""WarmApply · source adapter — Greenhouse / Lever company boards (Python source).

Read-only: watch SPECIFIC companies' public job boards (no key needed). Driven by a
`company_boards` list in config/search.yaml — empty by default; the user adds the
companies they'd love to work at:

    company_boards:
      - { provider: greenhouse, token: "airbnb",  name: "Airbnb" }
      - { provider: lever,      token: "netflix", name: "Netflix" }

Providers (public JSON):
  - Greenhouse: GET https://boards-api.greenhouse.io/v1/boards/<token>/jobs?content=true
      → { "jobs": [ { id, title, location:{name}, absolute_url, updated_at, content } ] }
  - Lever:      GET https://api.lever.co/v0/postings/<token>?mode=json
      → [ { id, text, categories:{location,team}, hostedUrl, createdAt(ms), descriptionPlain } ]

This is a normal Python source (NO BROWSER flag). Pure per-provider normalizers are
kept separate from the single network chokepoint so the dry-run is fully offline.
A single board failing → skip it and continue; empty `company_boards` → [].

Dependency: requests + PyYAML (both already present) + stdlib. No new dependency.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
import yaml

SOURCE = "greenhouse_lever"
_SNIPPET_LEN = 300
_HTTP_TIMEOUT = 15

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 WarmApply/1.0 "
    "(+job-search; contact via app)"
)

# This module lives in scripts/sources/, so when run directly sys.path[0] is
# scripts/sources/ — not scripts/. Insert the parent scripts/ dir (mirroring
# source_dispatch.py) so `import paths` resolves whether run directly or dispatched.
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402  single source of truth for paths (§4)

_SEARCH_CONFIG = paths.search_config()
_SEARCH_EXAMPLE = paths.search_example()

_GREENHOUSE_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
_LEVER_URL = "https://api.lever.co/v0/postings/{token}?mode=json"


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


def _date_from_iso(value: Any) -> Optional[str]:
    """Greenhouse updated_at (ISO 8601) → YYYY-MM-DD."""
    if not value:
        return None
    s = str(value)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return None


def _date_from_epoch_ms(value: Any) -> Optional[str]:
    """Lever createdAt (epoch milliseconds) → YYYY-MM-DD (UTC)."""
    try:
        ms = int(value)
    except (TypeError, ValueError):
        return None
    if ms <= 0:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def _company_of(entry: Dict[str, Any]) -> Optional[str]:
    return (entry.get("name") or entry.get("token") or "").strip() or None


def matches_roles(job: Dict[str, Any], roles: Optional[List[str]]) -> bool:
    """Case-insensitive match of any role across the job's title + tags (team/dept)."""
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


# ---------------------------------------------------------------------------
# Per-provider single-job normalizers (pure)
# ---------------------------------------------------------------------------

def normalize_greenhouse_job(job: Dict[str, Any], entry: Dict[str, Any]) -> Dict[str, Any]:
    token = (entry.get("token") or "").strip()
    loc = job.get("location") or {}
    location = (loc.get("name") if isinstance(loc, dict) else None) or "Remote"
    snippet = _strip_html(str(job.get("content") or ""))[:_SNIPPET_LEN]
    return {
        "job_id": f"{SOURCE}:greenhouse:{token}:{job.get('id')}",
        "source": SOURCE,
        "title": (job.get("title") or "").strip() or None,
        "company": _company_of(entry),
        "company_domain": None,
        "location": location,
        "url": job.get("absolute_url"),
        "posted_date": _date_from_iso(job.get("updated_at")),
        "easy_apply": False,
        "description_snippet": snippet,
        "found_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "_tags": [str(job.get("department") or "").lower()],
    }


def normalize_lever_job(job: Dict[str, Any], entry: Dict[str, Any]) -> Dict[str, Any]:
    token = (entry.get("token") or "").strip()
    cats = job.get("categories") or {}
    location = (cats.get("location") if isinstance(cats, dict) else None) or "Remote"
    team = cats.get("team") if isinstance(cats, dict) else None
    snippet = _strip_html(str(job.get("descriptionPlain") or job.get("description") or ""))[:_SNIPPET_LEN]
    return {
        "job_id": f"{SOURCE}:lever:{token}:{job.get('id')}",
        "source": SOURCE,
        "title": (job.get("text") or "").strip() or None,
        "company": _company_of(entry),
        "company_domain": None,
        "location": str(location),
        "url": job.get("hostedUrl"),
        "posted_date": _date_from_epoch_ms(job.get("createdAt")),
        "easy_apply": False,
        "description_snippet": snippet,
        "found_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "_tags": [str(team or "").lower()],
    }


# ---------------------------------------------------------------------------
# Feed-level normalizers (pure) — parse a full provider response + role-filter
# ---------------------------------------------------------------------------

def normalize_greenhouse(response: Dict[str, Any], entry: Dict[str, Any],
                         roles: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    jobs = (response or {}).get("jobs") or []
    out = []
    for raw in jobs:
        if not isinstance(raw, dict):
            continue
        job = normalize_greenhouse_job(raw, entry)
        if matches_roles(job, roles):
            job.pop("_tags", None)
            out.append(job)
    return out


def normalize_lever(response: List[Any], entry: Dict[str, Any],
                    roles: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    out = []
    for raw in response or []:
        if not isinstance(raw, dict):
            continue
        job = normalize_lever_job(raw, entry)
        if matches_roles(job, roles):
            job.pop("_tags", None)
            out.append(job)
    return out


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _read_company_boards(path: str = _SEARCH_CONFIG) -> List[Dict[str, Any]]:
    """Read `company_boards` from config/search.yaml (fallback to the example)."""
    for candidate in (path, _SEARCH_EXAMPLE):
        try:
            with open(candidate, "r", encoding="utf-8") as fh:
                cfg = yaml.safe_load(fh) or {}
            boards = cfg.get("company_boards")
            if isinstance(boards, list):
                return boards
        except (FileNotFoundError, yaml.YAMLError):
            continue
    return []


# ---------------------------------------------------------------------------
# Network chokepoint (monkeypatched in the dry-run) + fetch
# ---------------------------------------------------------------------------

def _http_get_json(url: str, timeout: int):
    """The ONLY network call. Returns parsed JSON, or raises on error."""
    resp = requests.get(url, headers={"User-Agent": USER_AGENT,
                                      "Accept": "application/json"}, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def fetch(roles: Optional[List[str]] = None, locations: Optional[List[str]] = None,
          timeout: int = _HTTP_TIMEOUT,
          company_boards: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Query each configured company board; normalize + role-filter.

    Reads `company_boards` from config unless one is passed in (for testing).
    Empty list → []. A board that errors/404s is skipped; the run continues.
    `locations` is accepted for a uniform signature but not used for filtering here.
    """
    boards = company_boards if company_boards is not None else _read_company_boards()
    if not boards:
        return []

    collected: List[Dict[str, Any]] = []
    for entry in boards:
        if not isinstance(entry, dict):
            continue
        provider = (entry.get("provider") or "").strip().lower()
        token = (entry.get("token") or "").strip()
        if not token or provider not in ("greenhouse", "lever"):
            continue  # skip malformed / unknown-provider entries
        try:
            if provider == "greenhouse":
                data = _http_get_json(_GREENHOUSE_URL.format(token=token), timeout)
                collected.extend(normalize_greenhouse(data, entry, roles))
            else:  # lever
                data = _http_get_json(_LEVER_URL.format(token=token), timeout)
                collected.extend(normalize_lever(data, entry, roles))
        except Exception:
            # One board failing must not break the run.
            continue
    return collected
