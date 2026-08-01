"""WarmApply · applied_history — de-dupe + record store (pure stdlib, no network).

The store lives at ``data/applied_history.json`` and maps a stable ``job_id`` to a
small record::

    { "<job_id>": { "company": ..., "title": ..., "status": ..., "ts": ... } }

It is the single source of truth for "already handled." The Job Finder consults it
to drop repeats BEFORE handing jobs to downstream agents; the application agent later
flips records from ``"seen"`` to ``"applied"``.

Public API (as required by the job-finder definition):
    - is_new(job, blacklist_companies=None) -> bool
    - mark_seen(job) -> None            # status: "seen"
    - mark_applied(job_id) -> None      # status: "applied"

Deduplication — a job is NOT new (drop it) if ANY of:
    1. its ``job_id`` is already in history, OR
    2. a ``company + normalized-title`` pair matches an existing entry (case-insensitive), OR
    3. its ``company`` is in ``blacklist_companies``.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

# ---------------------------------------------------------------------------
# Paths — routed through paths.py (§4). `scripts/` is on sys.path when this runs
# directly (sys.path[0]) or is imported as a sibling, so a plain import resolves.
# ---------------------------------------------------------------------------

import paths

HISTORY_PATH = paths.applied_history_path()

Job = Dict[str, Any]
History = Dict[str, Dict[str, Any]]


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def _normalize(text: Optional[str]) -> str:
    """Lower-case, collapse whitespace, strip — for case-insensitive matching."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip().lower()


def _pair_key(company: Optional[str], title: Optional[str]) -> str:
    """Stable key for a (company, normalized-title) pair."""
    return f"{_normalize(company)}::{_normalize(title)}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Store I/O
# ---------------------------------------------------------------------------

def _load(path: str = HISTORY_PATH) -> History:
    """Load the history store, returning {} if it is missing or empty."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save(history: History, path: str = HISTORY_PATH) -> None:
    """Atomically persist the history store, creating parent dirs as needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(history, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


def _existing_pairs(history: History) -> set:
    """Set of every (company, normalized-title) pair already recorded."""
    return {
        _pair_key(rec.get("company"), rec.get("title"))
        for rec in history.values()
        if isinstance(rec, dict)
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_new(job: Job, blacklist_companies: Optional[Iterable[str]] = None,
           *, path: str = HISTORY_PATH) -> bool:
    """Return True only if ``job`` is fresh and worth surfacing.

    Drops the job (returns False) if its job_id is known, if a matching
    company+normalized-title pair was already seen, or if its company is
    blacklisted.
    """
    job_id = job.get("job_id")
    if not job_id:
        # No stable id → cannot de-dupe safely; treat as not-new rather than
        # risk surfacing an unidentifiable listing.
        return False

    blacklist = {_normalize(c) for c in (blacklist_companies or [])}
    if _normalize(job.get("company")) in blacklist:
        return False

    history = _load(path)
    if job_id in history:
        return False

    if _pair_key(job.get("company"), job.get("title")) in _existing_pairs(history):
        return False

    return True


def mark_seen(job: Job, *, path: str = HISTORY_PATH) -> None:
    """Record ``job`` with status "seen" (idempotent on job_id)."""
    job_id = job.get("job_id")
    if not job_id:
        raise ValueError("mark_seen requires job['job_id']")

    history = _load(path)
    existing = history.get(job_id, {})
    history[job_id] = {
        "company": job.get("company"),
        "title": job.get("title"),
        "status": "seen",
        "ts": existing.get("ts") or _now_iso(),
    }
    _save(history, path)


def mark_applied(job_id: str, *, path: str = HISTORY_PATH) -> None:
    """Flip an existing record to status "applied" (used later by the apply agent)."""
    history = _load(path)
    rec = history.get(job_id)
    if rec is None:
        # Never seen before — create a minimal applied record so the store
        # stays the source of truth.
        rec = {"company": None, "title": None}
    rec = dict(rec)
    rec["status"] = "applied"
    rec["ts"] = _now_iso()
    history[job_id] = rec
    _save(history, path)


def dedupe(jobs: Iterable[Job], blacklist_companies: Optional[Iterable[str]] = None,
           *, path: str = HISTORY_PATH) -> list:
    """Convenience: return the subset of ``jobs`` that are new.

    De-dupes both against history AND within the input batch (so two identical
    listings in one run don't both pass).
    """
    fresh: list = []
    seen_ids: set = set()
    seen_pairs: set = set()
    blacklist = {_normalize(c) for c in (blacklist_companies or [])}

    for job in jobs:
        job_id = job.get("job_id")
        pair = _pair_key(job.get("company"), job.get("title"))
        if job_id in seen_ids or pair in seen_pairs:
            continue
        if _normalize(job.get("company")) in blacklist:
            continue
        if not is_new(job, blacklist_companies, path=path):
            continue
        fresh.append(job)
        seen_ids.add(job_id)
        seen_pairs.add(pair)
    return fresh
