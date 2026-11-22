"""Alfred · career-ops bridge DRY-RUN (OFFLINE — no node, no network).

Replaces careerops_bridge._run (the single subprocess chokepoint) with a fake
that returns canned career-ops output, and proves:

  1. every call runs with CAREER_OPS_ROOT = Alfred's home and no tracker override,
  2. scan(): the receipt's added_urls are read back from scan-history.tsv and
     normalized to Alfred's job shape; rows not in the receipt are ignored,
  3. the careerops_scan source returns those jobs through source_dispatch and
     de-dupes against an Alfred source (first in search_order wins),
  4. liveness(): check-liveness text output is parsed; aggregator URLs are never
     sent to it,
  5. verify_facts(): pass / block verdicts come through; garbage -> "error",
  6. repost_urls(): detect-reposts clusters map to per-URL notes,
  7. merge_house_rules(): Alfred's block is added once, replaced in place, and the
     user's own lines survive,
  8. missing install -> every call skips with a reason instead of raising.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TMP = tempfile.mkdtemp(prefix="alfred_bridge_")
os.environ["ALFRED_HOME"] = TMP
os.makedirs(os.path.join(TMP, "data"), exist_ok=True)

import careerops_bridge as cob  # noqa: E402
import source_dispatch  # noqa: E402
from sources import careerops_scan  # noqa: E402

calls = []
HISTORY = os.path.join(TMP, "data", "scan-history.tsv")
with open(HISTORY, "w", encoding="utf-8") as fh:
    fh.write("url\tfirst_seen\tportal\ttitle\tcompany\tstatus\tlocation\tfingerprint\tposted_at\t"
             "trust_score\ttrust_flags\tnormalized_company\trequisition_id\tlanguage\tlisting_key\n")
    fh.write("https://boards.greenhouse.io/acme/jobs/1\t2026-11-22\tgreenhouse\tProduct Designer\t"
             "Acme\tadded\tBengaluru, India\t\t2026-11-21\t\t\tacme\tR-1\ten\tgh:acme:1\n")
    fh.write("https://jobs.lever.co/zen/2\t2026-11-22\tlever\tUX Designer\tZen\tadded\tRemote\t\t\t"
             "80\tvague_title\tzen\t\ten\tlever:zen:2\n")
    fh.write("https://old.example/3\t2026-10-01\tashby\tOld Role\tOldCo\tadded\tRemote\t\t\t\t\t\t\t\t\n")

LIVENESS_OUT = """Checking 2 URL(s)...

✅ active     (api) https://boards.greenhouse.io/acme/jobs/1
❌ expired          https://jobs.lever.co/zen/2
           posting says no longer accepting applications

Results: 1 active  1 expired  0 uncertain  (1 via API, no browser)
"""


def fake_run(script, args=(), timeout=900, stdin=None):
    args = list(args)
    calls.append({"script": script, "args": args, "env_root": cob.env().get("CAREER_OPS_ROOT"),
                  "tracker_env": cob.env().get("CAREER_OPS_TRACKER")})
    if script == "scan.mjs":
        receipt = {"version": "careerops.scan.receipt@1", "date": "2026-11-22", "added": 2,
                   "added_urls": ["https://boards.greenhouse.io/acme/jobs/1",
                                  "https://jobs.lever.co/zen/2"], "errors": []}
        return {"ok": True, "rc": 0, "stdout": "log line\n" + json.dumps(receipt) + "\n", "stderr": ""}
    if script == "check-liveness.mjs":
        file_arg = args[args.index("--file") + 1]
        calls[-1]["urls"] = open(file_arg, encoding="utf-8").read().split()
        return {"ok": True, "rc": 0, "stdout": LIVENESS_OUT, "stderr": ""}
    if script == "verify-cv-facts.mjs":
        target = args[0]
        if "bad" in target:
            return {"ok": False, "rc": 1, "stdout": json.dumps({"verdict": "block",
                    "invented": ["led a team of 40"]}), "stderr": ""}
        if "garbage" in target:
            return {"ok": False, "rc": 1, "stdout": "not json", "stderr": "boom"}
        return {"ok": True, "rc": 0, "stdout": json.dumps({"verdict": "pass", "invented": []}), "stderr": ""}
    if script == "detect-reposts.mjs":
        return {"ok": True, "rc": 0, "stdout": json.dumps({"metadata": {"clusters": 1}, "clusters": [
            {"company": "Acme", "role": "Product Designer", "repostCount": 3, "daysSpan": 40,
             "appearances": [{"url": "https://a.example/1"}, {"url": "https://a.example/2"},
                             {"url": "https://a.example/3"}]}]}), "stderr": ""}
    return {"ok": False, "rc": 1, "stdout": "", "stderr": f"unexpected {script}"}


def main() -> int:
    print("=" * 70)
    print("Alfred · career-ops bridge — DRY RUN (offline, fake node)")
    print("=" * 70)
    failures = []

    def check(ok, label):
        failures.extend([] if ok else [label])
        print(f"  [{'OK' if ok else 'XX'}] {label}")

    # 8 first: the REAL _run with no install must skip, not raise.
    os.environ["ALFRED_CAREEROPS_DIR"] = os.path.join(TMP, "nowhere")
    skipped = cob._run("scan.mjs", ["--json"])
    res_none = cob.scan()
    check(skipped.get("skipped") is True and res_none["jobs"] == [] and res_none["skipped"],
          "no install → _run skips with a reason, scan() returns [] (no exception)")
    check(cob.verify_facts("x.html")["verdict"] == "error", "no install → fact gate reports error, not pass")

    cob._run = fake_run
    cob.unavailable_reason = lambda: None

    # 2. scan
    res = cob.scan(since_days=3)
    jobs = res["jobs"]
    check(len(jobs) == 2 and {j["company"] for j in jobs} == {"Acme", "Zen"},
          "scan(): only receipt URLs read back from scan-history (2 of 3 rows)")
    acme = next(j for j in jobs if j["company"] == "Acme")
    check(acme["job_id"] == "careerops:greenhouse:gh:acme:1" and acme["source"] == "careerops_scan"
          and acme["posted_date"] == "2026-11-21" and acme["location"] == "Bengaluru, India",
          "scan(): normalized to Alfred job shape (job_id, source, posted_date, location)")
    zen = next(j for j in jobs if j["company"] == "Zen")
    check(zen["trust_flags"] == ["vague_title"], "scan(): trust flags carried for Block G")
    check(calls[-1]["args"][:2] == ["--json", "--quiet"] and "--since" in calls[-1]["args"],
          "scan(): --json --quiet --since passed")

    # 1. env
    check(all(c["env_root"] == TMP and c["tracker_env"] is None for c in calls),
          "every call: CAREER_OPS_ROOT = Alfred home, no CAREER_OPS_TRACKER override")

    # 3. through source_dispatch with an Alfred source
    class FakeAlfred:
        BROWSER = False
        @staticmethod
        def fetch(roles=None, locations=None, timeout=15):
            return [{"job_id": "remoteok:9", "source": "remoteok", "title": "Product Designer",
                     "company": "Acme", "url": "https://remoteok.com/9"}]
    hist = os.path.join(TMP, "data", "applied_history.json")
    fresh, report = source_dispatch.dispatch(["careerops_scan", "remoteok"], roles=["Designer"],
                                             registry={"careerops_scan": careerops_scan,
                                                       "remoteok": FakeAlfred},
                                             history_path=hist)
    check(len(fresh) == 2 and fresh[0]["source"] == "careerops_scan"
          and not any(j["source"] == "remoteok" for j in fresh),
          "dispatch: careerops_scan first wins the Acme duplicate over remoteok")
    check([r["status"] for r in report] == ["ok", "ok"], "dispatch: both sources report ok")

    # 4. liveness
    live = cob.liveness(["https://boards.greenhouse.io/acme/jobs/1", "https://jobs.lever.co/zen/2",
                         "https://www.linkedin.com/jobs/view/123/"], record=False)
    v = live["verdicts"]
    check(v["https://boards.greenhouse.io/acme/jobs/1"]["verdict"] == "active"
          and v["https://boards.greenhouse.io/acme/jobs/1"]["via_api"]
          and v["https://jobs.lever.co/zen/2"]["verdict"] == "expired"
          and "no longer accepting" in (v["https://jobs.lever.co/zen/2"]["reason"] or ""),
          "liveness(): active/expired + reason parsed from text output")
    sent = calls[-1].get("urls", [])
    check("https://www.linkedin.com/jobs/view/123/" not in sent
          and live["skipped_aggregators"] == ["https://www.linkedin.com/jobs/view/123/"]
          and "--no-record" in calls[-1]["args"],
          "liveness(): LinkedIn URL never liveness-checked (aggregator), --no-record honored")

    # 5. fact gate
    check(cob.verify_facts("output/good.html", ["cv.md"])["verdict"] == "pass"
          and cob.verify_facts("output/bad.html")["verdict"] == "block"
          and cob.verify_facts("output/garbage.html")["verdict"] == "error",
          "verify_facts(): pass / block / error (garbage never reads as pass)")

    # 6. reposts
    notes = cob.repost_urls(cob.reposts())
    check(len(notes) == 3 and "listed 3 times over 40 days" in notes["https://a.example/2"],
          "repost_urls(): cluster → note on every URL")

    # 7. house rules merge
    rules = cob.house_rules_text()
    once = cob.merge_house_rules("# Mine\n- keep this\n", rules)
    twice = cob.merge_house_rules(once.replace("No cover letters", "No cover letters (old)"), rules)
    check(once.count(cob.HOUSE_START) == 1 and "- keep this" in once
          and twice.count(cob.HOUSE_START) == 1 and "(old)" not in twice and "- keep this" in twice,
          "merge_house_rules(): added once, replaced in place, user lines kept")
    check("No cover letters" in rules and "Aside" in rules and "Playwright MCP" in rules,
          "house rules carry the no-cover-letter and Aside-only rules")

    print("\n" + "=" * 70)
    if failures:
        print("RESULT: FAIL ❌")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("RESULT: PASS ✅ — bridge env, scan, dispatch, liveness, fact gate, reposts, house rules; offline.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
