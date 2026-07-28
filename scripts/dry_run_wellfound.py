"""WarmApply · Wellfound DRY-RUN (OFFLINE — browser source; no network at all).

Wellfound is a BROWSER source: the job-finder subagent scrapes cards from Chrome
and this module only normalizes them. So this dry-run:
  A. runs the REAL normalize + matches_roles over fake scraped cards and asserts the
     canonical shape, source, role filter, null-company + no-fabricated-date cases;
  B. proves the module is browser-shaped (BROWSER=True, no fetch(), no requests);
  C. runs source_dispatch over ["wellfound", <fake python source>] and asserts
     wellfound is reported status:"browser" (dispatch never calls a fetch for it),
     while the Python source still runs normally.

Pure/offline throughout — Wellfound has no network code to trip.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import source_dispatch  # noqa: E402
from sources import wellfound as wf  # noqa: E402


# ---------------------------------------------------------------------------
# Fake scraped cards (whatever the subagent reads off the rendered page).
#   card 1: normal design role
#   card 2: relative "posted" ("3 days ago") → posted_date must be None (not faked)
#   card 3: non-design role → filtered out
#   card 4: NO company on the card → company null (never fabricated)
# ---------------------------------------------------------------------------

CARDS = [
    {
        "title": "Senior Product Designer", "company": "Acme", "location": "Remote",
        "url": "https://wellfound.com/jobs/12345-senior-product-designer",
        "posted": "2026-07-24",
        "snippet": "<p>Own the <b>design system</b> &amp; ship polished UI.</p>",
        "tags": ["design", "figma"],
    },
    {
        "title": "UX Designer", "company": "Globex", "location": "Bengaluru / Remote",
        "url": "https://wellfound.com/jobs/222-ux-designer",
        "posted": "3 days ago",  # relative → not a real date
        "snippet": "Run usability studies and prototype flows.",
    },
    {
        "title": "Backend Engineer", "company": "Initech",
        "url": "https://wellfound.com/jobs/333-backend-engineer",
        "posted": "2026-07-23", "snippet": "Build APIs.",
    },
    {
        "title": "UI Designer",  # no company key on this card
        "url": "https://wellfound.com/jobs/444-ui-designer",
        "posted": "2026-07-25", "snippet": "Short gig for a UI Designer.",
    },
    {
        "id": "role1", "title": "UX Designer", "company": "ListCo",  # role-list URL → null
        "url": "https://wellfound.com/role/ux-designer/india",
        "posted": "2026-07-24", "snippet": "Role search page, not a specific job.",
    },
]

ROLES = ["Product Designer", "UX Designer", "UI Designer"]

CANONICAL_KEYS = {
    "job_id", "source", "title", "company", "company_domain", "location",
    "url", "posted_date", "easy_apply", "description_snippet", "found_at",
}


class FakePythonSource:
    """Stand-in API/RSS source with a fetch(), to show dispatch still runs those."""
    def fetch(self, roles=None, locations=None, timeout=15):
        return [{"job_id": "fakeapi:1", "source": "fakeapi", "company": "PyCo",
                 "title": "Product Designer", "url": "https://x/1"}]


def main() -> int:
    print("=" * 74)
    print("WarmApply · Wellfound — DRY RUN (OFFLINE; browser source, no network)")
    print("=" * 74)

    # ---- A. normalize + role filter ---------------------------------------
    jobs = wf.normalize_cards(CARDS, ROLES)
    print("\nA) Fake scraped cards → canonical jobs (role-filtered):")
    print(json.dumps(jobs, indent=2, ensure_ascii=False))
    by_id = {j["job_id"]: j for j in jobs}

    # ---- C. dispatch marks wellfound as browser ---------------------------
    registry = {"wellfound": wf, "fakeapi": FakePythonSource()}
    order = ["wellfound", "fakeapi"]
    tmp_history = os.path.join(tempfile.mkdtemp(prefix="warmapply_wf_"), "history.json")
    fresh, report = source_dispatch.dispatch(order, roles=ROLES, blacklist=[],
                                             registry=registry, history_path=tmp_history)
    print("\nC) dispatch report over [wellfound, fakeapi]:")
    for r in report:
        print(f"  - {r['source']:<9} {r['status']:<8} count={r['count']}  {r.get('note','')}")
    print(f"  dispatch returned {len(fresh)} python-source job(s) "
          f"(wellfound contributes via the subagent, not dispatch)")

    # ---- Assertions --------------------------------------------------------
    print("\n" + "-" * 74)
    print("Assertions:")
    failures = []

    # A1: role filter kept the design roles (ids from job URL), dropped Backend.
    ids = [j["job_id"] for j in jobs]
    expected = ["wellfound:12345-senior-product-designer",
                "wellfound:222-ux-designer", "wellfound:444-ui-designer",
                "wellfound:role1"]
    ok_filter = ids == expected
    failures += [] if ok_filter else [f"role filter/id wrong: {ids}"]
    print(f"  [{'OK' if ok_filter else 'XX'}] role filter kept design roles, dropped Backend "
          f"(ids from job URL)")

    # A2: canonical shape + source + prefix + no internal keys.
    shape_ok = all(set(j.keys()) == CANONICAL_KEYS for j in jobs)
    prefix_ok = all(j["job_id"].startswith("wellfound:") and j["source"] == "wellfound"
                    for j in jobs)
    no_internal = all("_tags" not in j for j in jobs)
    ok_shape = shape_ok and prefix_ok and no_internal
    failures += [] if ok_shape else ["canonical shape/source/prefix wrong"]
    print(f"  [{'OK' if ok_shape else 'XX'}] canonical shape exact + source=wellfound + no internal keys")

    # A3: relative "posted" → posted_date None (never fabricated); HTML stripped.
    c2 = by_id.get("wellfound:222-ux-designer")
    ok_reldate = bool(c2) and c2["posted_date"] is None
    c1 = by_id.get("wellfound:12345-senior-product-designer")
    ok_html = bool(c1) and "<" not in c1["description_snippet"] and "design system" in c1["description_snippet"]
    ok_dates = ok_reldate and ok_html and c1["posted_date"] == "2026-07-24"
    failures += [] if ok_dates else ["date/HTML handling wrong"]
    print(f"  [{'OK' if ok_dates else 'XX'}] relative 'posted'→None (not fabricated), "
          f"ISO kept ({c1['posted_date']}), HTML stripped")

    # A4: missing company → null.
    c4 = by_id.get("wellfound:444-ui-designer")
    ok_null = bool(c4) and c4["company"] is None
    failures += [] if ok_null else [f"missing-company case wrong: {c4 and c4['company']}"]
    print(f"  [{'OK' if ok_null else 'XX'}] missing company on card → company=None (not fabricated)")

    # B: module is browser-shaped — BROWSER=True, no fetch(), no requests import.
    ok_browser_mod = (getattr(wf, "BROWSER", False) is True
                      and not hasattr(wf, "fetch")
                      and getattr(wf, "requests", None) is None)
    failures += [] if ok_browser_mod else ["wellfound module is not browser-shaped"]
    print(f"  [{'OK' if ok_browser_mod else 'XX'}] BROWSER=True, no fetch(), no requests "
          f"(pure normalizer)")

    # C1: dispatch marks wellfound status 'browser' and contributes nothing to dispatch.
    status = {r["source"]: r for r in report}
    wf_entry = status.get("wellfound", {})
    ok_dispatch = (wf_entry.get("status") == "browser"
                   and wf_entry.get("note") == "handled by job-finder subagent"
                   and wf_entry.get("count") == 0)
    failures += [] if ok_dispatch else [f"dispatch did not mark wellfound browser: {wf_entry}"]
    print(f"  [{'OK' if ok_dispatch else 'XX'}] dispatch → wellfound status='browser' "
          f"(no Python fetch attempted)")

    # C2: the Python source still ran normally alongside it.
    ok_py = status.get("fakeapi", {}).get("status") == "ok" and "fakeapi:1" in [j["job_id"] for j in fresh]
    failures += [] if ok_py else ["python source did not run alongside browser source"]
    print(f"  [{'OK' if ok_py else 'XX'}] Python source still runs via dispatch "
          f"(fakeapi ok, returned {len(fresh)} job)")

    # D1: a specific job URL is kept as url.
    u1 = by_id["wellfound:12345-senior-product-designer"]["url"]
    ok_joburl = u1 == "https://wellfound.com/jobs/12345-senior-product-designer"
    failures += [] if ok_joburl else [f"specific job URL not kept: {u1!r}"]
    print(f"  [{'OK' if ok_joburl else 'XX'}] specific job URL kept as url ({u1})")

    # D2: a role-list/search URL → url rejected to null.
    u_role = by_id["wellfound:role1"]["url"]
    ok_role_null = u_role is None
    failures += [] if ok_role_null else [f"role-list URL not rejected: {u_role!r}"]
    print(f"  [{'OK' if ok_role_null else 'XX'}] role-list URL input → url=null (not stored)")

    print("\n" + "=" * 74)
    if failures:
        print("RESULT: FAIL ❌")
        for msg in failures:
            print(f"  - {msg}")
        print("=" * 74)
        return 1
    print("RESULT: PASS ✅ — normalize + role filter correct; dispatch defers wellfound "
          "to the subagent; fully offline.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
