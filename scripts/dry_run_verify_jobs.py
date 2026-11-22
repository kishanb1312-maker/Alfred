"""Alfred · job verifier DRY-RUN (OFFLINE — fake career-ops).

Proves `scripts/verify_jobs.py` decides "is the job real?" correctly:

  - aggregator + employer found     -> employer_url set, liveness checked there, live
  - employer ATS reports closed     -> dropped as closed
  - employer board without the role -> dropped as stale (unless Easy Apply)
  - ATS URL expired                 -> dropped as closed
  - liveness uncertain              -> kept, unconfirmed
  - repost cluster                  -> kept with a repost note
  - no career-ops install           -> everything kept as unconfirmed, with the reason
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["ALFRED_HOME"] = tempfile.mkdtemp(prefix="alfred_verify_")

import careerops_bridge as cob  # noqa: E402
import verify_jobs  # noqa: E402


def jobs():
    return [
        {"job_id": "li:1", "company": "Acme", "title": "Product Designer",
         "url": "https://www.linkedin.com/jobs/view/1/"},
        {"job_id": "li:2", "company": "Shut", "title": "UX Designer",
         "url": "https://www.linkedin.com/jobs/view/2/"},
        {"job_id": "indeed:3", "company": "Gone", "title": "UI Designer",
         "url": "https://in.indeed.com/viewjob?jk=3"},
        {"job_id": "li:4", "company": "EasyCo", "title": "Product Designer",
         "url": "https://www.linkedin.com/jobs/view/4/", "easy_apply": True},
        {"job_id": "gh:5", "company": "Dead", "title": "Designer",
         "url": "https://boards.greenhouse.io/dead/jobs/5"},
        {"job_id": "lever:6", "company": "Maybe", "title": "Designer",
         "url": "https://jobs.lever.co/maybe/6"},
        {"job_id": "ashby:7", "company": "Ghost", "title": "Designer",
         "url": "https://jobs.ashbyhq.com/ghost/7"},
    ]


CONFIRM = {
    "Acme": {"verdict": "found", "match": "exact", "employerUrl": "https://boards.greenhouse.io/acme/jobs/11"},
    "Shut": {"verdict": "employer_url", "employerUrl": "https://jobs.lever.co/shut/22", "live": "closed"},
    "Gone": {"verdict": "board_without_role", "complete": True},
    "EasyCo": {"verdict": "board_without_role", "complete": True},
}
LIVE = {
    "https://boards.greenhouse.io/acme/jobs/11": {"verdict": "active"},
    "https://boards.greenhouse.io/dead/jobs/5": {"verdict": "expired", "reason": "404"},
    "https://jobs.lever.co/maybe/6": {"verdict": "uncertain", "reason": "anti-bot page"},
    "https://jobs.ashbyhq.com/ghost/7": {"verdict": "active"},
}


def main() -> int:
    print("=" * 70)
    print("Alfred · job verifier — DRY RUN (offline, fake career-ops)")
    print("=" * 70)
    failures = []

    def check(ok, label):
        failures.extend([] if ok else [label])
        print(f"  [{'OK' if ok else 'XX'}] {label}")

    real_reason = cob.unavailable_reason
    cob.unavailable_reason = lambda: "Node 22.13+ needed (found none)"
    kept0, dropped0, stats0 = verify_jobs.verify(jobs())
    check(len(kept0) == 7 and not dropped0 and stats0.get("skipped")
          and all("not checked" in j["verification"]["reason"] for j in kept0),
          "no career-ops → all kept as unconfirmed with the reason (never an empty run)")

    checked_urls = []
    cob.unavailable_reason = lambda: None
    cob.confirm_at_employer = lambda url, company, title, origin=None: CONFIRM.get(company, {"verdict": "no_board"})
    cob.liveness = lambda urls, record=True: (checked_urls.extend(urls),
                                              {"verdicts": {u: LIVE[u] for u in urls if u in LIVE}})[1]
    cob.reposts = lambda window_days=90: {"clusters": [{"company": "Ghost", "role": "Designer",
                                          "repostCount": 4, "daysSpan": 60,
                                          "appearances": [{"url": "https://jobs.ashbyhq.com/ghost/7"}]}]}
    kept, dropped, stats = verify_jobs.verify(jobs(), record=False)
    k = {j["job_id"]: j for j in kept}
    d = {j["job_id"]: j for j in dropped}

    check(k["li:1"]["employer_url"] == "https://boards.greenhouse.io/acme/jobs/11"
          and k["li:1"]["verification"]["status"] == "live",
          "aggregator + employer found → employer_url set, live")
    check(d.get("li:2", {}).get("verification", {}).get("status") == "closed",
          "employer ATS reports closed → dropped (closed)")
    check(d.get("indeed:3", {}).get("verification", {}).get("status") == "stale",
          "employer board read in full, role absent → dropped (stale)")
    check(k["li:4"]["verification"]["status"] == "unconfirmed",
          "same, but Easy Apply → kept (the Easy Apply form is the path)")
    check(d.get("gh:5", {}).get("verification", {}).get("status") == "closed", "ATS URL expired → dropped")
    check(k["lever:6"]["verification"]["status"] == "unconfirmed", "liveness uncertain → kept, unconfirmed")
    check("listed 4 times" in k["ashby:7"].get("repost", ""), "repost cluster → kept with a note")
    check(not any("linkedin.com" in u or "indeed.com" in u for u in checked_urls),
          "aggregator pages are never liveness-checked")
    check(stats["dropped"] == 3 and stats["live"] == 2 and stats["reposts"] == 1,
          f"stats: {stats}")
    cob.unavailable_reason = real_reason

    print("\n" + "=" * 70)
    if failures:
        print("RESULT: FAIL ❌")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("RESULT: PASS ✅ — employer confirmation, liveness, reposts, honest fallback; offline.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
