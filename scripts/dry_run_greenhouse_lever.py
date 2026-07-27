"""WarmApply · Greenhouse/Lever DRY-RUN (OFFLINE — asserts zero network).

Feeds SAVED sample Greenhouse AND Lever JSON responses through the REAL per-provider
normalizers + role filter, and asserts:
  - canonical shape for BOTH providers, correct source + job_id (provider:token:id),
  - Greenhouse ISO date and Lever epoch-ms date both → YYYY-MM-DD; HTML stripped,
  - company = the board entry's name; role filter drops non-matching roles,
  - empty company_boards → [] (and makes no network call),
  - ZERO network (the _http_get_json chokepoint is tripwired to raise).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sources import greenhouse_lever as gl  # noqa: E402


# ---------------------------------------------------------------------------
# Network tripwire: the single JSON chokepoint raises if called.
# ---------------------------------------------------------------------------

_net_calls = []


def _tripwire(url, timeout):
    _net_calls.append(url)
    raise AssertionError("network call attempted — dry-run must be offline!")


gl._http_get_json = _tripwire  # type: ignore


# ---------------------------------------------------------------------------
# Saved sample responses.
# ---------------------------------------------------------------------------

GH_ENTRY = {"provider": "greenhouse", "token": "airbnb", "name": "Airbnb"}
GH_RESPONSE = {
    "jobs": [
        {
            "id": 5001, "title": "Senior Product Designer",
            "location": {"name": "Remote - US"},
            "absolute_url": "https://boards.greenhouse.io/airbnb/jobs/5001",
            "updated_at": "2026-07-24T12:00:00-04:00",
            "content": "<p>Own the <b>design system</b> &amp; ship polished UI.</p>",
            "department": "Design",
        },
        {
            "id": 5002, "title": "Backend Engineer",
            "location": {"name": "San Francisco"},
            "absolute_url": "https://boards.greenhouse.io/airbnb/jobs/5002",
            "updated_at": "2026-07-20T09:00:00-04:00",
            "content": "Build APIs.", "department": "Engineering",
        },
    ]
}

LV_ENTRY = {"provider": "lever", "token": "netflix", "name": "Netflix"}
# Lever createdAt is epoch MILLISECONDS; build one for a known date.
_LV_MS = int(datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc).timestamp() * 1000)
LV_RESPONSE = [
    {
        "id": "l1-abc", "text": "UX Designer",
        "categories": {"location": "Remote", "team": "Design"},
        "hostedUrl": "https://jobs.lever.co/netflix/l1-abc",
        "createdAt": _LV_MS,
        "descriptionPlain": "Run usability studies and prototype flows.",
    },
    {
        "id": "l2-def", "text": "Data Engineer",
        "categories": {"location": "New York", "team": "Data Platform"},
        "hostedUrl": "https://jobs.lever.co/netflix/l2-def",
        "createdAt": _LV_MS, "descriptionPlain": "Pipelines.",
    },
]

ROLES = ["Product Designer", "UX Designer", "UI Designer"]

CANONICAL_KEYS = {
    "job_id", "source", "title", "company", "company_domain", "location",
    "url", "posted_date", "easy_apply", "description_snippet", "found_at",
}


def main() -> int:
    print("=" * 74)
    print("WarmApply · Greenhouse/Lever — DRY RUN (OFFLINE; _http_get_json tripwired)")
    print("=" * 74)

    gh_jobs = gl.normalize_greenhouse(GH_RESPONSE, GH_ENTRY, ROLES)
    lv_jobs = gl.normalize_lever(LV_RESPONSE, LV_ENTRY, ROLES)

    print("\nGreenhouse sample → canonical jobs:")
    print(json.dumps(gh_jobs, indent=2, ensure_ascii=False))
    print("\nLever sample → canonical jobs:")
    print(json.dumps(lv_jobs, indent=2, ensure_ascii=False))

    # Empty company_boards → [] with no network.
    empty_result = gl.fetch(roles=ROLES, company_boards=[])

    print("\n" + "-" * 74)
    print("Assertions:")
    failures = []

    # 1: Greenhouse — 1 design job kept (5001), Backend dropped; shape + ids.
    gh_ok = ([j["job_id"] for j in gh_jobs] == ["greenhouse_lever:greenhouse:airbnb:5001"]
             and gh_jobs[0]["company"] == "Airbnb"
             and gh_jobs[0]["location"] == "Remote - US"
             and gh_jobs[0]["posted_date"] == "2026-07-24"
             and gh_jobs[0]["source"] == "greenhouse_lever"
             and set(gh_jobs[0].keys()) == CANONICAL_KEYS
             and "<" not in gh_jobs[0]["description_snippet"]
             and "design system" in gh_jobs[0]["description_snippet"])
    failures += [] if gh_ok else [f"greenhouse normalize wrong: {gh_jobs}"]
    print(f"  [{'OK' if gh_ok else 'XX'}] Greenhouse: canonical shape, id "
          f"greenhouse:airbnb:5001, ISO date→2026-07-24, HTML stripped, Backend dropped")

    # 2: Lever — 1 design job kept (l1), Data dropped; epoch-ms date; shape + ids.
    lv_ok = ([j["job_id"] for j in lv_jobs] == ["greenhouse_lever:lever:netflix:l1-abc"]
             and lv_jobs[0]["company"] == "Netflix"
             and lv_jobs[0]["location"] == "Remote"
             and lv_jobs[0]["posted_date"] == "2026-07-22"
             and lv_jobs[0]["source"] == "greenhouse_lever"
             and set(lv_jobs[0].keys()) == CANONICAL_KEYS)
    failures += [] if lv_ok else [f"lever normalize wrong: {lv_jobs}"]
    print(f"  [{'OK' if lv_ok else 'XX'}] Lever: canonical shape, id lever:netflix:l1-abc, "
          f"epoch-ms→2026-07-22, Data Engineer dropped")

    # 3: both providers report the SAME source.
    ok_source = all(j["source"] == "greenhouse_lever" for j in gh_jobs + lv_jobs)
    failures += [] if ok_source else ["source not greenhouse_lever for all"]
    print(f"  [{'OK' if ok_source else 'XX'}] both providers → source='greenhouse_lever'")

    # 4: empty company_boards → [] (and no network).
    ok_empty = empty_result == []
    failures += [] if ok_empty else [f"empty company_boards should be [], got {empty_result}"]
    print(f"  [{'OK' if ok_empty else 'XX'}] empty company_boards → [] (no boards to query)")

    # 5: normal Python source (not browser), has fetch().
    ok_py = (getattr(gl, "BROWSER", False) is False) and hasattr(gl, "fetch")
    failures += [] if ok_py else ["module should be a Python (non-browser) source"]
    print(f"  [{'OK' if ok_py else 'XX'}] Python source (no BROWSER flag, has fetch())")

    # 6: zero network.
    ok_offline = len(_net_calls) == 0
    failures += [] if ok_offline else [f"network touched: {_net_calls}"]
    print(f"  [{'OK' if ok_offline else 'XX'}] NO network (_http_get_json invoked "
          f"{len(_net_calls)} times)")

    print("\n" + "=" * 74)
    if failures:
        print("RESULT: FAIL ❌")
        for msg in failures:
            print(f"  - {msg}")
        print("=" * 74)
        return 1
    print("RESULT: PASS ✅ — Greenhouse + Lever normalize correctly; empty boards → []; offline.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
