"""WarmApply · LinkedIn Feed Hunter DRY-RUN (OFFLINE — browser source, no network).

Feeds fake scraped hiring posts through the REAL normalize + matches_roles and asserts:
  - lead shape = canonical job shape PLUS outreach_method / recruiter_name /
    recruiter_profile / contact_email,
  - correct outreach_method per post (email / dm / comment / link),
  - null-not-fabricated (company/email/name absent → null; posted_date always null),
  - source=linkedin_feed, role filter drops non-matching posts,
  - module is browser-shaped (BROWSER=True, no fetch(), no requests),
  - dispatch marks linkedin_feed status:"browser" (no network).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import source_dispatch  # noqa: E402
from sources import linkedin_feed as lf  # noqa: E402


# ---------------------------------------------------------------------------
# Fake scraped posts — one per outreach_method + one non-design (filtered).
# ---------------------------------------------------------------------------

POSTS = [
    {   # → email (address stated in the post text)
        "id": "111", "role": "Product Designer", "company": "Acme",
        "location": "Remote / Bengaluru",
        "text": "We're hiring a Product Designer! Email me at sara@acme.com to apply.",
        "recruiter_name": "Sara R.",
        "recruiter_profile": "https://www.linkedin.com/in/sarar",
        "url": "https://www.linkedin.com/posts/sarar-activity-111",
    },
    {   # → dm
        "id": "222", "title": "UX Designer", "company": "Globex",
        "text": "We are hiring a UX Designer — DM me if interested!",
        "recruiter_name": "Raj K.",
        "recruiter_profile": "https://www.linkedin.com/in/rajk",
        "url": "https://www.linkedin.com/posts/rajk-activity-222",
    },
    {   # → comment ; company NOT stated → must be null
        "id": "333", "title": "UI Designer",
        "text": "Looking for a UI Designer — comment below with your portfolio.",
        "recruiter_name": "Mia P.",
        "url": "https://www.linkedin.com/posts/miap-activity-333",
    },
    {   # → link (application link present)
        "id": "444", "title": "Product Designer", "company": "Initech",
        "text": "Hiring a Product Designer. Apply here for the role.",
        "link": "https://initech.example/apply",
        "recruiter_name": "Bill L.",
        "recruiter_profile": "https://www.linkedin.com/in/billl",
        "url": "https://www.linkedin.com/posts/billl-activity-444",
    },
    {   # non-design → filtered out
        "id": "555", "title": "Sales Manager", "company": "Umbrella",
        "text": "We're hiring a Sales Manager — DM me.",
        "url": "https://www.linkedin.com/posts/umbrella-activity-555",
    },
]

ROLES = ["Product Designer", "UX Designer", "UI Designer"]

CANONICAL_KEYS = {
    "job_id", "source", "title", "company", "company_domain", "location",
    "url", "posted_date", "easy_apply", "description_snippet", "found_at",
}
LEAD_EXTRA = {"outreach_method", "recruiter_name", "recruiter_profile", "contact_email"}
LEAD_KEYS = CANONICAL_KEYS | LEAD_EXTRA


class FakePythonSource:
    def fetch(self, roles=None, locations=None, timeout=15):
        return [{"job_id": "fakeapi:1", "source": "fakeapi", "company": "PyCo",
                 "title": "Product Designer", "url": "https://x/1"}]


def main() -> int:
    print("=" * 74)
    print("WarmApply · LinkedIn Feed Hunter — DRY RUN (OFFLINE; no network)")
    print("=" * 74)

    leads = lf.normalize_posts(POSTS, ROLES)
    print("\nFake posts → leads (role-filtered):")
    print(json.dumps(leads, indent=2, ensure_ascii=False))
    by_id = {l["job_id"]: l for l in leads}

    # dispatch behavior
    registry = {"linkedin_feed": lf, "fakeapi": FakePythonSource()}
    tmp_history = os.path.join(tempfile.mkdtemp(prefix="warmapply_lf_"), "history.json")
    fresh, report = source_dispatch.dispatch(["linkedin_feed", "fakeapi"], roles=ROLES,
                                             blacklist=[], registry=registry,
                                             history_path=tmp_history)
    print("\ndispatch report over [linkedin_feed, fakeapi]:")
    for r in report:
        print(f"  - {r['source']:<14} {r['status']:<8} count={r['count']}  {r.get('note','')}")

    print("\n" + "-" * 74)
    print("Assertions:")
    failures = []

    # 1: role filter kept 4 design posts, dropped Sales Manager.
    ids = [l["job_id"] for l in leads]
    expected = ["linkedin_feed:111", "linkedin_feed:222",
                "linkedin_feed:333", "linkedin_feed:444"]
    ok_filter = ids == expected
    failures += [] if ok_filter else [f"role filter wrong: {ids}"]
    print(f"  [{'OK' if ok_filter else 'XX'}] role filter kept design posts, dropped Sales ({ids})")

    # 2: lead shape (canonical + 4 outreach fields), source + prefix, no internal keys.
    shape_ok = all(set(l.keys()) == LEAD_KEYS for l in leads)
    prefix_ok = all(l["job_id"].startswith("linkedin_feed:") and l["source"] == "linkedin_feed"
                    for l in leads)
    no_internal = all("_tags" not in l for l in leads)
    ok_shape = shape_ok and prefix_ok and no_internal
    failures += [] if ok_shape else ["lead shape/source/prefix wrong"]
    print(f"  [{'OK' if ok_shape else 'XX'}] lead shape = canonical + outreach fields "
          f"({len(LEAD_KEYS)} keys), source=linkedin_feed")

    # 3: outreach_method per post.
    got = {i: by_id[f"linkedin_feed:{i}"]["outreach_method"] for i in ("111", "222", "333", "444")}
    want = {"111": "email", "222": "dm", "333": "comment", "444": "link"}
    ok_method = got == want
    failures += [] if ok_method else [f"outreach_method wrong: {got}"]
    print(f"  [{'OK' if ok_method else 'XX'}] outreach_method: email/dm/comment/link → {got}")

    # 4: contact_email extracted from post text (111), else null.
    ok_email = (by_id["linkedin_feed:111"]["contact_email"] == "sara@acme.com"
                and by_id["linkedin_feed:222"]["contact_email"] is None
                and by_id["linkedin_feed:444"]["contact_email"] is None)
    failures += [] if ok_email else ["contact_email extraction wrong"]
    print(f"  [{'OK' if ok_email else 'XX'}] contact_email from post (111=sara@acme.com), else null")

    # 5: null-not-fabricated — company absent (333) → null; posted_date always null.
    ok_null = (by_id["linkedin_feed:333"]["company"] is None
               and all(l["posted_date"] is None for l in leads))
    failures += [] if ok_null else ["null/fabrication rule wrong"]
    print(f"  [{'OK' if ok_null else 'XX'}] absent company→null (333), posted_date always null")

    # 6: recruiter fields — present where given (111), null where absent.
    ok_recruiter = (by_id["linkedin_feed:111"]["recruiter_name"] == "Sara R."
                    and by_id["linkedin_feed:333"]["recruiter_profile"] is None)
    failures += [] if ok_recruiter else ["recruiter field handling wrong"]
    print(f"  [{'OK' if ok_recruiter else 'XX'}] recruiter_name/profile present-or-null")

    # 7: module is browser-shaped.
    ok_browser = (getattr(lf, "BROWSER", False) is True
                  and not hasattr(lf, "fetch")
                  and getattr(lf, "requests", None) is None)
    failures += [] if ok_browser else ["module not browser-shaped"]
    print(f"  [{'OK' if ok_browser else 'XX'}] BROWSER=True, no fetch(), no requests")

    # 8: dispatch marks linkedin_feed browser; python source still runs.
    status = {r["source"]: r for r in report}
    ok_dispatch = (status.get("linkedin_feed", {}).get("status") == "browser"
                   and status.get("fakeapi", {}).get("status") == "ok")
    failures += [] if ok_dispatch else [f"dispatch wrong: {status}"]
    print(f"  [{'OK' if ok_dispatch else 'XX'}] dispatch → linkedin_feed status='browser' "
          f"(no network); python source still runs")

    print("\n" + "=" * 74)
    if failures:
        print("RESULT: FAIL ❌")
        for msg in failures:
            print(f"  - {msg}")
        print("=" * 74)
        return 1
    print("RESULT: PASS ✅ — leads + outreach routing correct; dispatch defers to subagent; offline.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
