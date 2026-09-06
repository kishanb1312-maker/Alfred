"""Alfred · Indeed DRY-RUN (OFFLINE — browser source; no network at all).

Indeed is a BROWSER source: the job-finder subagent scrapes cards from a browser and
this module only normalizes them. This dry-run:
  A. runs the REAL normalize + matches_roles over fake scraped cards and asserts the
     canonical shape, source, role filter, jobkey extraction (explicit + from URL),
     null-company + relative-date→None (no fabrication);
  B. proves the module is browser-shaped (BROWSER=True, no fetch(), no requests);
  C. runs source_dispatch over ["indeed", <fake python source>] and asserts indeed
     is reported status:"browser" (dispatch never calls a fetch for it).

Pure/offline throughout — Indeed has no network code to trip.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import source_dispatch  # noqa: E402
from sources import indeed as idd  # noqa: E402


# ---------------------------------------------------------------------------
# Fake scraped cards.
#   card 1: explicit jobkey + ISO date
#   card 2: jobkey ONLY in the URL (?jk=...) + relative "Posted 3 days ago" → None
#   card 3: non-design role → filtered out
#   card 4: no company + "Just posted" → company null, posted_date None
# ---------------------------------------------------------------------------

CARDS = [
    {
        "jobkey": "abc123", "title": "Senior Product Designer", "company": "Acme",
        "location": "Bengaluru, Karnataka",
        "url": "https://in.indeed.com/viewjob?jk=abc123",
        "posted": "2026-07-24",
        "snippet": "<p>Own the <b>design system</b> &amp; ship polished UI.</p>",
    },
    {
        "title": "UX Designer", "company": "Globex", "location": "Remote",
        "url": "https://in.indeed.com/viewjob?jk=def456&from=serp",  # jobkey only in URL
        "posted": "Posted 3 days ago",
        "snippet": "Run usability studies and prototype flows.",
    },
    {
        "jobkey": "ghi789", "title": "Backend Engineer", "company": "Initech",
        "url": "https://in.indeed.com/viewjob?jk=ghi789",
        "posted": "2026-07-23", "snippet": "Build APIs.",
    },
    {
        "jobkey": "jkl000", "title": "UI Designer",  # no company
        "url": "https://in.indeed.com/viewjob?jk=jkl000",
        "posted": "Just posted", "snippet": "Short gig for a UI Designer.",
    },
]

ROLES = ["Product Designer", "UX Designer", "UI Designer"]

CANONICAL_KEYS = {
    "job_id", "source", "title", "company", "company_domain", "location",
    "url", "posted_date", "easy_apply", "description_snippet", "found_at",
}


class FakePythonSource:
    def fetch(self, roles=None, locations=None, timeout=15):
        return [{"job_id": "fakeapi:1", "source": "fakeapi", "company": "PyCo",
                 "title": "Product Designer", "url": "https://x/1"}]


def main() -> int:
    print("=" * 74)
    print("Alfred · Indeed — DRY RUN (OFFLINE; browser source, no network)")
    print("=" * 74)

    # ---- A. normalize + role filter ---------------------------------------
    jobs = idd.normalize_cards(CARDS, ROLES)
    print("\nA) Fake scraped cards → canonical jobs (role-filtered):")
    print(json.dumps(jobs, indent=2, ensure_ascii=False))
    by_id = {j["job_id"]: j for j in jobs}

    # ---- C. dispatch marks indeed as browser ------------------------------
    registry = {"indeed": idd, "fakeapi": FakePythonSource()}
    order = ["indeed", "fakeapi"]
    tmp_history = os.path.join(tempfile.mkdtemp(prefix="alfred_idd_"), "history.json")
    fresh, report = source_dispatch.dispatch(order, roles=ROLES, blacklist=[],
                                             registry=registry, history_path=tmp_history)
    print("\nC) dispatch report over [indeed, fakeapi]:")
    for r in report:
        print(f"  - {r['source']:<9} {r['status']:<8} count={r['count']}  {r.get('note','')}")

    # ---- Assertions --------------------------------------------------------
    print("\n" + "-" * 74)
    print("Assertions:")
    failures = []

    # A1: role filter kept 3 design roles; job_id from jobkey (incl. URL-only case).
    ids = [j["job_id"] for j in jobs]
    expected = ["indeed:abc123", "indeed:def456", "indeed:jkl000"]
    ok_filter = ids == expected
    failures += [] if ok_filter else [f"role filter/jobkey wrong: {ids}"]
    print(f"  [{'OK' if ok_filter else 'XX'}] role filter kept design roles; job_id from jobkey "
          f"(incl. URL-only def456) → {ids}")

    # A2: canonical shape + source + prefix + no internal keys.
    shape_ok = all(set(j.keys()) == CANONICAL_KEYS for j in jobs)
    prefix_ok = all(j["job_id"].startswith("indeed:") and j["source"] == "indeed" for j in jobs)
    no_internal = all("_tags" not in j for j in jobs)
    ok_shape = shape_ok and prefix_ok and no_internal
    failures += [] if ok_shape else ["canonical shape/source/prefix wrong"]
    print(f"  [{'OK' if ok_shape else 'XX'}] canonical shape exact + source=indeed + no internal keys")

    # A3: relative dates → None; ISO kept; HTML stripped.
    c1 = by_id.get("indeed:abc123")
    c2 = by_id.get("indeed:def456")
    c4 = by_id.get("indeed:jkl000")
    ok_dates = (bool(c1) and c1["posted_date"] == "2026-07-24"
                and bool(c2) and c2["posted_date"] is None
                and bool(c4) and c4["posted_date"] is None
                and "<" not in c1["description_snippet"] and "design system" in c1["description_snippet"])
    failures += [] if ok_dates else ["date/HTML handling wrong"]
    print(f"  [{'OK' if ok_dates else 'XX'}] relative dates→None (def456, jkl000), ISO kept "
          f"(abc123={c1['posted_date']}), HTML stripped")

    # A4: missing company → null.
    ok_null = bool(c4) and c4["company"] is None
    failures += [] if ok_null else [f"missing-company case wrong: {c4 and c4['company']}"]
    print(f"  [{'OK' if ok_null else 'XX'}] missing company on card → company=None (not fabricated)")

    # B: module is browser-shaped.
    ok_browser_mod = (getattr(idd, "BROWSER", False) is True
                      and not hasattr(idd, "fetch")
                      and getattr(idd, "requests", None) is None)
    failures += [] if ok_browser_mod else ["indeed module is not browser-shaped"]
    print(f"  [{'OK' if ok_browser_mod else 'XX'}] BROWSER=True, no fetch(), no requests "
          f"(pure normalizer)")

    # C1: dispatch marks indeed status 'browser'.
    status = {r["source"]: r for r in report}
    idd_entry = status.get("indeed", {})
    ok_dispatch = (idd_entry.get("status") == "browser"
                   and idd_entry.get("note") == "handled by job-finder subagent"
                   and idd_entry.get("count") == 0)
    failures += [] if ok_dispatch else [f"dispatch did not mark indeed browser: {idd_entry}"]
    print(f"  [{'OK' if ok_dispatch else 'XX'}] dispatch → indeed status='browser' "
          f"(no Python fetch attempted)")

    # C2: python source still ran.
    ok_py = status.get("fakeapi", {}).get("status") == "ok" and "fakeapi:1" in [j["job_id"] for j in fresh]
    failures += [] if ok_py else ["python source did not run alongside browser source"]
    print(f"  [{'OK' if ok_py else 'XX'}] Python source still runs via dispatch "
          f"(fakeapi ok, returned {len(fresh)} job)")

    print("\n" + "=" * 74)
    if failures:
        print("RESULT: FAIL ❌")
        for msg in failures:
            print(f"  - {msg}")
        print("=" * 74)
        return 1
    print("RESULT: PASS ✅ — normalize + jobkey + role filter correct; dispatch defers indeed "
          "to the subagent; fully offline.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
