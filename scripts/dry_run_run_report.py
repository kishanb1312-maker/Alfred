"""Alfred · run_report DRY-RUN (OFFLINE, fake data in a temp home).

Builds a fake run (sources, verified/dropped, review list, decisions, apply results,
a scheduled email, a tracker) and proves the Markdown report and the HTML dashboard:
  - count applied only with the site's confirmation (submitted), not filled/blocked,
  - list what needs the user with the missing answers and the URL,
  - show scheduled emails with time and recipient,
  - read every tracker row,
  - escape page text in the dashboard (no raw <script> from job data),
  - refuse a "submitted" record without a confirmation.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
TMP = tempfile.mkdtemp(prefix="alfred_report_")
os.environ["ALFRED_HOME"] = TMP
for d in ("data", "config", "output"):
    os.makedirs(os.path.join(TMP, d), exist_ok=True)
with open(os.path.join(TMP, "config", "search.yaml"), "w") as fh:
    fh.write("dry_run: false\nlocation_priority: [remote_abroad, india, onsite_abroad]\n")

import review_store as rs  # noqa: E402
import run_report  # noqa: E402


def w(name, value):
    with open(os.path.join(TMP, "data", name), "w") as fh:
        json.dump(value, fh)


def main() -> int:
    failures = []

    def check(ok, label):
        failures.extend([] if ok else [label])
        print(f"  [{'OK' if ok else 'XX'}] {label}")

    print("=" * 66 + "\nAlfred · run_report — DRY RUN (offline, fake data)\n" + "=" * 66)
    w("finder_report.json", [{"source": "careerops_scan", "status": "ok", "count": 20},
                             {"source": "linkedin_easy_apply", "status": "ok", "count": 9}])
    w("verified_jobs.json", [{}] * 22)
    w("verify_dropped.json", [{"company": "Gone", "title": "UX", "verification": {"reason": "posting expired"}}])
    w("evaluation_output.json", [{}] * 22)
    jobs = [("n8n:1", "n8n", "Product Designer", "Remote — Europe", "4.6/5"),
            ("zeta:2", "Zeta", "Lead UX Designer", "Bangalore - DD", "4.3/5"),
            ("cl:3", "Clerk <script>alert(1)</script>", "Product Designer", "Remote", "4.1/5"),
            ("pl:4", "Synerise", "Senior Product Designer", "Kraków", "4.0/5")]
    for jid, co, title, loc, sc in jobs:
        rs.add_for_review({"job_id": jid, "company": co, "title": title, "location": loc, "score": sc,
                           "url": f"https://example.com/{jid}", "cv_pdf": f"{TMP}/output/cv-{jid}.pdf"})
    for jid in ("n8n:1", "zeta:2", "cl:3"):
        rs.approve(jid)
    rs.record_apply_result("n8n:1", "submitted", host="jobs.ashbyhq.com",
                           confirmation="Thanks for applying to n8n!")
    rs.record_apply_result("zeta:2", "filled", host="jobs.lever.co",
                           unanswered=["Current CTC in LPA?"], final_url="https://jobs.lever.co/zeta/2")
    rs.record_apply_result("cl:3", "blocked", host="jobs.lever.co", notes="hCaptcha appeared")
    rs.record_scheduled_email("n8n:1", "talent@n8n.example", "Product Designer — Kishan",
                              "2026-11-23 11:00 IST", "me@example.com", f"{TMP}/output/cv-n8n:1.pdf")
    try:
        rs.record_apply_result("pl:4", "submitted")
        refused = False
    except ValueError:
        refused = True
    with open(os.path.join(TMP, "data", "applications.md"), "w") as fh:
        fh.write("# Applications Tracker\n\n| # | Date | Company | Role | Score | Status | PDF | Report | Notes |\n"
                 "|---|---|---|---|---|---|---|---|---|\n"
                 "| 1 | 2026-11-23 | n8n | Product Designer | 4.6/5 | Applied | ✅ | [1](reports/1.md) | via ashby |\n"
                 "| 2 | 2026-11-23 | Zeta | Lead UX Designer | 4.3/5 | Evaluated | ✅ | [2](reports/2.md) | |\n")

    d = run_report.collect()
    out = run_report.write(d)
    md = open(out["md"], encoding="utf-8").read()
    page = open(out["dashboard"], encoding="utf-8").read()
    t = d["totals"]
    check(t["applied"] == 1 and t["needs_you"] == 2 and t["approved"] == 3 and t["on_review"] == 4,
          f"totals: applied only with confirmation; filled+blocked = needs you ({t})")
    check(t["found"] == 29 and t["dropped"] == 1 and t["emails_scheduled"] == 1 and t["tracker_rows"] == 2,
          "totals: found per source, dropped, scheduled emails, tracker rows")
    check("## Applied" in md and "Thanks for applying to n8n!" in md and "jobs.ashbyhq.com" in md,
          "MD: Applied table with host + confirmation")
    check("Current CTC in LPA?" in md and "https://jobs.lever.co/zeta/2" in md and "hCaptcha" in md,
          "MD: Needs you lists missing answers, URL, blocker")
    check("scheduled 2026-11-23 11:00 IST → talent@n8n.example" in md, "MD: scheduled email time + recipient")
    check("Synerise" in md.split("## Waiting for your approval")[1].split("##")[0],
          "MD: un-decided job listed as waiting")
    check("<script>alert(1)</script>" not in page.split('id="data">')[0] and "<\\/script>" in page,
          "HTML: job text is escaped / cannot close the data script")
    check(page.count("<table") == 2 and "Alfred dashboard" in page and os.path.exists(out["latest"]),
          "HTML: dashboard + latest copy written, two tables")
    check(refused, "record_apply_result refuses 'submitted' without a confirmation")
    print("\n" + ("RESULT: FAIL ❌" if failures else "RESULT: PASS ✅ — report + dashboard; offline."))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
