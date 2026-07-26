"""WarmApply · Jobspresso DRY-RUN (OFFLINE — asserts zero network).

Feeds a SAVED sample that mirrors the REAL Jobspresso feed structure seen live
(WP Job Manager RSS with a custom job_listing namespace: dedicated <company>,
<location>, <job_type>, and WP <post-id>) through the REAL parser + normalizer +
role filter, and asserts:
  - canonical shape (exact key set) + source/job_id prefix (from post-id),
  - company comes from the dedicated <company> element,
  - a MISSING <company> → company null (never fabricated),
  - title used as-is, RFC-822 pubDate → YYYY-MM-DD, HTML-stripped snippet,
  - role filter drops non-matching roles,
  - ZERO network calls (requests tripwired).
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sources import jobspresso as jp  # noqa: E402


# ---------------------------------------------------------------------------
# Network tripwire.
# ---------------------------------------------------------------------------

class _Tripwire:
    def __init__(self):
        self.calls = []

    def get(self, *args, **kwargs):
        self.calls.append(args)
        raise AssertionError("network call attempted — dry-run must be offline!")


_tripwire = _Tripwire()
jp.requests = _tripwire  # type: ignore


# ---------------------------------------------------------------------------
# Saved sample mirroring the REAL feed (namespaces + elements as seen live).
#   item 1: normal design role, has <company>
#   item 2: another design role
#   item 3: non-design role → filtered out
#   item 4: NO <company> element → company must be null (not fabricated)
# ---------------------------------------------------------------------------

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:wp="com-wordpress:feed-additions:1"
     xmlns:job_listing="https://jobspresso.co/">
  <channel>
    <title>Jobs &#8211; Jobspresso</title>
    <link>https://jobspresso.co/</link>
    <item>
      <title>Senior Product Designer</title>
      <link>https://jobspresso.co/job/acme-various-senior-product-designer/</link>
      <dc:creator>Acme&lt;br&gt;&#8890;&#160;Worldwide</dc:creator>
      <pubDate>Thu, 24 Jul 2026 16:56:41 +0000</pubDate>
      <guid>https://jobspresso.co/?post_type=job_listing&#038;p=100</guid>
      <description>&lt;p&gt;Own the &lt;b&gt;design system&lt;/b&gt; &amp; ship polished UI.&lt;/p&gt;</description>
      <wp:post-id>100</wp:post-id>
      <job_listing:location>Worldwide</job_listing:location>
      <job_listing:job_type>Design</job_listing:job_type>
      <job_listing:job_category>Full Time</job_listing:job_category>
      <job_listing:company>Acme</job_listing:company>
    </item>
    <item>
      <title>UX Designer</title>
      <link>https://jobspresso.co/job/globex-various-ux-designer/</link>
      <dc:creator>Globex&lt;br&gt;&#8890;&#160;USA</dc:creator>
      <pubDate>Wed, 22 Jul 2026 13:51:12 +0000</pubDate>
      <guid>https://jobspresso.co/?post_type=job_listing&#038;p=101</guid>
      <description>Run usability studies and prototype flows.</description>
      <wp:post-id>101</wp:post-id>
      <job_listing:location>USA</job_listing:location>
      <job_listing:job_type>Design</job_listing:job_type>
      <job_listing:company>Globex</job_listing:company>
    </item>
    <item>
      <title>Backend Engineer</title>
      <link>https://jobspresso.co/job/initech-various-backend-engineer/</link>
      <pubDate>Tue, 21 Jul 2026 10:00:00 +0000</pubDate>
      <guid>https://jobspresso.co/?post_type=job_listing&#038;p=102</guid>
      <description>Build APIs in Python.</description>
      <wp:post-id>102</wp:post-id>
      <job_listing:location>Worldwide</job_listing:location>
      <job_listing:job_type>Programming</job_listing:job_type>
      <job_listing:company>Initech</job_listing:company>
    </item>
    <item>
      <title>UI Designer (Contract)</title>
      <link>https://jobspresso.co/job/various-ui-designer-contract/</link>
      <pubDate>Sat, 25 Jul 2026 09:00:00 +0000</pubDate>
      <guid>https://jobspresso.co/?post_type=job_listing&#038;p=103</guid>
      <description>Short gig for a &lt;i&gt;UI Designer&lt;/i&gt;.</description>
      <wp:post-id>103</wp:post-id>
      <job_listing:location>Europe</job_listing:location>
      <job_listing:job_type>Design</job_listing:job_type>
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
    print("WarmApply · Jobspresso — DRY RUN (OFFLINE; requests tripwired)")
    print("=" * 74 + "\n")

    jobs = jp.normalize_feed(SAMPLE_RSS, ROLES)
    print("Sample feed → canonical jobs (role-filtered):")
    print(json.dumps(jobs, indent=2, ensure_ascii=False))
    by_id = {j["job_id"]: j for j in jobs}

    print("\n" + "-" * 74)
    print("Assertions:")
    failures = []

    # 1: role filter kept the 3 design roles (post-ids 100/101/103), dropped 102.
    ids = [j["job_id"] for j in jobs]
    expected = ["jobspresso:100", "jobspresso:101", "jobspresso:103"]
    ok_filter = ids == expected
    failures += [] if ok_filter else [f"role filter/id wrong: {ids}"]
    print(f"  [{'OK' if ok_filter else 'XX'}] role filter kept design roles, dropped Backend; "
          f"job_id from post-id ({ids})")

    # 2: canonical shape + source + prefix + no internal keys.
    shape_ok = all(set(j.keys()) == CANONICAL_KEYS for j in jobs)
    prefix_ok = all(j["job_id"].startswith("jobspresso:") and j["source"] == "jobspresso"
                    for j in jobs)
    no_internal = all("_job_type" not in j for j in jobs)
    ok_shape = shape_ok and prefix_ok and no_internal
    failures += [] if ok_shape else ["canonical shape/source/prefix wrong"]
    print(f"  [{'OK' if ok_shape else 'XX'}] canonical shape exact + source correct + no internal keys")

    # 3: company from the dedicated <company> element; title used as-is.
    a = by_id.get("jobspresso:100")
    ok_company = bool(a) and a["company"] == "Acme" and a["title"] == "Senior Product Designer"
    failures += [] if ok_company else [f"company/title wrong: {a and (a['company'], a['title'])}"]
    print(f"  [{'OK' if ok_company else 'XX'}] company from <company> element → "
          f"{a['company']!r}, title as-is → {a['title']!r}")

    # 4: MISSING <company> → null (never fabricated).
    d = by_id.get("jobspresso:103")
    ok_null = bool(d) and d["company"] is None and d["title"] == "UI Designer (Contract)"
    failures += [] if ok_null else [f"missing-company case wrong: {d and d['company']}"]
    print(f"  [{'OK' if ok_null else 'XX'}] missing <company> → company=None (not fabricated)")

    # 5: pubDate → YYYY-MM-DD, custom <location>, HTML stripped.
    ok_date = bool(a) and a["posted_date"] == "2026-07-24"
    ok_loc = bool(a) and a["location"] == "Worldwide"
    ok_html = bool(a) and "<" not in a["description_snippet"] and "design system" in a["description_snippet"]
    ok_fields = ok_date and ok_loc and ok_html
    failures += [] if ok_fields else [f"field mapping wrong: {a and (a['posted_date'], a['location'])}"]
    print(f"  [{'OK' if ok_fields else 'XX'}] pubDate→{a['posted_date']}, "
          f"<location>→{a['location']!r}, HTML stripped")

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
    print("RESULT: PASS ✅ — parse + company/title extraction + role filter correct, offline.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
