#!/usr/bin/env python3
"""Alfred · verify_jobs — "is the job real?" before any AI tokens are spent.

For every job in data/finder_output.json:

  1. Aggregator listing (LinkedIn, Indeed, Wellfound, RemoteOK, ...)?
     -> career-ops confirm-at-employer.mjs looks for the same role on the
        employer's own ATS. A found employer URL becomes `employer_url` and is
        what gets checked, evaluated and applied to.
  2. Employer / ATS URL -> career-ops check-liveness.mjs (free ATS APIs first,
     headless Playwright second): active | expired | uncertain.
  3. career-ops detect-reposts.mjs over the scan history -> `repost` note for
     roles re-listed 2+ times (a ghost-job signal, never a verdict on its own).

Outcome per job (`verification.status`):
    live         employer URL confirmed active                  -> evaluate
    unconfirmed  aggregator only, or liveness uncertain         -> evaluate, flagged
    closed       expired / closed at the employer               -> dropped
    stale        employer board answered and the role is absent -> dropped

LinkedIn Easy Apply jobs are kept as `unconfirmed` when no employer listing is
found: the Easy Apply form itself is the application path.

Writes data/verified_jobs.json (kept) and data/verify_dropped.json (dropped,
with the reason). Needs career-ops; without it every job passes through as
`unconfirmed` with the reason, so a missing install never empties a run.

Usage: verify_jobs.py [--in data/finder_output.json] [--no-record]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import careerops_bridge as cob  # noqa: E402
import paths  # noqa: E402


def _check_url(job: Dict[str, Any]) -> str:
    return job.get("employer_url") or job.get("url") or ""


def classify(job: Dict[str, Any], confirm: Dict[str, Any] | None,
             live: Dict[str, Any] | None) -> Tuple[str, str]:
    """PURE: (status, reason) from the confirm + liveness results."""
    if confirm:
        v = confirm.get("verdict")
        if confirm.get("live") == "closed":
            return "closed", "employer ATS reports the role closed"
        if v == "board_without_role" and confirm.get("complete"):
            if job.get("easy_apply"):
                return "unconfirmed", "not on the employer board; Easy Apply form is the path"
            return "stale", "employer board read in full and the role is not on it"
    if live:
        verdict = live.get("verdict")
        if verdict == "expired":
            return "closed", live.get("reason") or "posting expired"
        if verdict == "active":
            return "live", "active at " + ("employer" if job.get("employer_url") else "source")
        return "unconfirmed", live.get("reason") or "liveness uncertain"
    if confirm and confirm.get("verdict") in ("no_board", "unidentified", "board_without_role"):
        return "unconfirmed", f"employer check: {confirm.get('verdict')}"
    return "unconfirmed", "not checked"


def verify(jobs: List[Dict[str, Any]], record: bool = True) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    reason = cob.unavailable_reason()
    if reason:
        for j in jobs:
            j["verification"] = {"status": "unconfirmed", "reason": f"not checked: {reason}"}
        return jobs, [], {"skipped": reason}

    confirms: Dict[str, Dict[str, Any]] = {}
    for j in jobs:
        if cob.is_aggregator(j.get("url")) and j.get("company") and j.get("title"):
            c = cob.confirm_at_employer(j["url"], j["company"], j["title"], j.get("origin"))
            confirms[j["job_id"]] = c
            if c.get("verdict") in ("employer_url", "found") and c.get("employerUrl"):
                j["employer_url"] = c["employerUrl"]

    urls = sorted({_check_url(j) for j in jobs if _check_url(j) and not cob.is_aggregator(_check_url(j))})
    live = cob.liveness(urls, record=record) if urls else {"verdicts": {}}
    reposts = cob.repost_urls(cob.reposts())

    kept, dropped = [], []
    for j in jobs:
        status, why = classify(j, confirms.get(j["job_id"]),
                               live.get("verdicts", {}).get(_check_url(j)))
        j["verification"] = {"status": status, "reason": why,
                             "employer_check": (confirms.get(j["job_id"]) or {}).get("verdict")}
        note = reposts.get(j.get("url")) or reposts.get(j.get("employer_url") or "")
        if note:
            j["repost"] = note
        (kept if status in ("live", "unconfirmed") else dropped).append(j)
    stats = {"checked": len(jobs), "live": sum(j["verification"]["status"] == "live" for j in kept),
             "unconfirmed": sum(j["verification"]["status"] == "unconfirmed" for j in kept),
             "dropped": len(dropped), "reposts": sum(1 for j in kept if j.get("repost")),
             "liveness_error": live.get("error")}
    return kept, dropped, stats


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default=os.path.join(paths.data_dir(), "finder_output.json"))
    ap.add_argument("--no-record", action="store_true")
    a = ap.parse_args(argv)
    with open(a.src, "r", encoding="utf-8") as fh:
        jobs = json.load(fh)
    kept, dropped, stats = verify(jobs, record=not a.no_record)
    for name, value in (("verified_jobs.json", kept), ("verify_dropped.json", dropped)):
        with open(os.path.join(paths.data_dir(), name), "w", encoding="utf-8") as fh:
            json.dump(value, fh, indent=2)
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
