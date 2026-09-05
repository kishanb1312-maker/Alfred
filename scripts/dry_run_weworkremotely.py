"""Alfred · We Work Remotely DRY-RUN (OFFLINE — asserts zero network).

Feeds a SAVED sample of the WWR RSS feed (fake items, no network) through the REAL
parser + normalizer + role filter, prints the canonical jobs, and asserts:
  - canonical shape (exact key set) + source/job_id prefix,
  - correct "Company: Title" split (incl. the no-colon → company null case),
  - RFC-822 pubDate → YYYY-MM-DD and HTML-stripped snippet,
  - the role filter drops non-matching roles,
  - ZERO network calls (requests is tripwired to raise).
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sources import weworkremotely as wwr  # noqa: E402


# ---------------------------------------------------------------------------
# Network tripwire: any HTTP via wwr.requests raises.
# ---------------------------------------------------------------------------

class _Tripwire:
    def __init__(self):
        self.calls = []

    def get(self, *args, **kwargs):
        self.calls.append(args)
        raise AssertionError("network call attempted — dry-run must be offline!")


_tripwire = _Tripwire()
wwr.requests = _tripwire  # type: ignore


# ---------------------------------------------------------------------------
# Saved sample of the WWR RSS feed (fake items).
#   - item 1: normal "Company: Title"
#   - item 2: another design role, region "USA Only"
#   - item 3: non-design role → should be filtered out
#   - item 4: NO colon in title → company null, title = whole string
# ---------------------------------------------------------------------------

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>We Work Remotely: Remote Jobs</title>
    <link>https://weworkremotely.com/</link>
    <item>
      <title>Acme: Senior Product Designer</title>
      <region>Anywhere in the World</region>
      <category>Design</category>
      <description>&lt;p&gt;Own the &lt;b&gt;design system&lt;/b&gt; &amp; ship polished UI.&lt;/p&gt;</description>
      <pubDate>Fri, 24 Jul 2026 09:00:00 +0000</pubDate>
      <guid>https://weworkremotely.com/remote-jobs/acme-senior-product-designer</guid>
      <link>https://weworkremotely.com/remote-jobs/acme-senior-product-designer</link>
    </item>
    <item>
      <title>Globex: UX Designer</title>
      <region>USA Only</region>
      <category>Design</category>
      <description>Run usability studies and prototype flows.</description>
      <pubDate>Wed, 22 Jul 2026 09:00:00 +0000</pubDate>
      <guid>https://weworkremotely.com/remote-jobs/globex-ux-designer</guid>
      <link>https://weworkremotely.com/remote-jobs/globex-ux-designer</link>
    </item>
    <item>
      <title>Initech: Backend Engineer</title>
      <region>Anywhere in the World</region>
      <category>Programming</category>
      <description>Build APIs in Python.</description>
      <pubDate>Thu, 23 Jul 2026 09:00:00 +0000</pubDate>
      <guid>https://weworkremotely.com/remote-jobs/initech-backend-engineer</guid>
      <link>https://weworkremotely.com/remote-jobs/initech-backend-engineer</link>
    </item>
    <item>
      <title>Freelance UI Designer Wanted</title>
      <region>Europe Only</region>
      <category>Design</category>
      <description>Short gig for a &lt;i&gt;UI Designer&lt;/i&gt;.</description>
      <pubDate>Sat, 25 Jul 2026 09:00:00 +0000</pubDate>
      <guid>https://weworkremotely.com/remote-jobs/freelance-ui-designer-wanted</guid>
      <link>https://weworkremotely.com/remote-jobs/freelance-ui-designer-wanted</link>
    </item>
  </channel>
</rss>"""

ROLES = ["Product Designer", "UX Designer", "UI Designer"]

CANONICAL_KEYS = {
    "job_id", "source", "title", "company", "company_domain", "location",
    "url", "posted_date", "easy_apply", "description_snippet", "found_at",
}


def main() -> int:
    print("=" * 74)
    print("Alfred · We Work Remotely — DRY RUN (OFFLINE; requests tripwired)")
    print("=" * 74 + "\n")

    jobs = wwr.normalize_feed(SAMPLE_RSS, ROLES)
    print("Sample RSS → canonical jobs (role-filtered):")
    print(json.dumps(jobs, indent=2, ensure_ascii=False))

    by_id = {j["job_id"]: j for j in jobs}

    # ---- Assertions --------------------------------------------------------
    print("\n" + "-" * 74)
    print("Assertions:")
    failures = []

    # 1: role filter kept the 3 design roles, dropped the Backend Engineer.
    ids = [j["job_id"] for j in jobs]
    expected_ids = [
        "we_work_remotely:acme-senior-product-designer",
        "we_work_remotely:globex-ux-designer",
        "we_work_remotely:freelance-ui-designer-wanted",
    ]
    ok_filter = ids == expected_ids
    failures += [] if ok_filter else [f"role filter wrong: {ids}"]
    print(f"  [{'OK' if ok_filter else 'XX'}] role filter kept design roles, dropped Backend "
          f"({len(jobs)} jobs)")

    # 2: canonical shape (exact key set), source + job_id prefix, no internal keys.
    shape_ok = all(set(j.keys()) == CANONICAL_KEYS for j in jobs)
    prefix_ok = all(j["job_id"].startswith("we_work_remotely:")
                    and j["source"] == "we_work_remotely" for j in jobs)
    no_internal = all("_categories" not in j for j in jobs)
    ok_shape = shape_ok and prefix_ok and no_internal
    failures += [] if ok_shape else ["canonical shape/source/prefix wrong"]
    print(f"  [{'OK' if ok_shape else 'XX'}] canonical shape exact + source correct + no internal keys")

    # 3: "Company: Title" split — normal case.
    a = by_id.get("we_work_remotely:acme-senior-product-designer")
    ok_split = bool(a) and a["company"] == "Acme" and a["title"] == "Senior Product Designer"
    failures += [] if ok_split else [f"company/title split wrong: {a and (a['company'], a['title'])}"]
    print(f"  [{'OK' if ok_split else 'XX'}] 'Company: Title' split → "
          f"company={a['company']!r}, title={a['title']!r}")

    # 4: no-colon title → company null, title = whole string.
    f = by_id.get("we_work_remotely:freelance-ui-designer-wanted")
    ok_nocolon = bool(f) and f["company"] is None and f["title"] == "Freelance UI Designer Wanted"
    failures += [] if ok_nocolon else [f"no-colon split wrong: {f and (f['company'], f['title'])}"]
    print(f"  [{'OK' if ok_nocolon else 'XX'}] no-colon title → company=None, "
          f"title={f['title']!r}")

    # 5: pubDate → YYYY-MM-DD, region → location, HTML stripped.
    ok_date = bool(a) and a["posted_date"] == "2026-07-24"
    ok_loc = bool(a) and a["location"] == "Anywhere in the World"
    ok_html = bool(a) and "<" not in a["description_snippet"] and "design system" in a["description_snippet"]
    ok_fields = ok_date and ok_loc and ok_html
    failures += [] if ok_fields else [f"field mapping wrong (date/loc/html): "
                                      f"{a and (a['posted_date'], a['location'])}"]
    print(f"  [{'OK' if ok_fields else 'XX'}] pubDate→{a['posted_date']}, region→location, "
          f"HTML stripped")

    # 6: zero network.
    ok_offline = len(_tripwire.calls) == 0
    failures += [] if ok_offline else [f"network touched: {_tripwire.calls}"]
    print(f"  [{'OK' if ok_offline else 'XX'}] NO network (requests.get invoked "
          f"{len(_tripwire.calls)} times)")

    print("\n" + "=" * 74)
    if failures:
        print("RESULT: FAIL ❌")
        for msg in failures:
            print(f"  - {msg}")
        print("=" * 74)
        return 1
    print("RESULT: PASS ✅ — parse + split + normalize + role filter correct, offline.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
