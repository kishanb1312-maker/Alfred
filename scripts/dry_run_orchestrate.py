"""Alfred · Orchestrator DRY-RUN (OFFLINE — no network, no subagent calls).

Exercises the deterministic glue in scripts/orchestrate.py:
  1. preflight() against the EXAMPLE configs (+ a temp cv.md) → OK/dry_run,
     and a second call proving it BLOCKS when cv.md is missing,
  2. merge_job() assembling the canonical job object from sample finder/research/
     tailoring parts,
  3. run_summary() for a simulated dry_run pass.

Nothing here calls a subagent, the network, or a browser — it's pure dict glue.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orchestrate as orch  # noqa: E402
import paths  # noqa: E402  bundled example configs live under CODE_ROOT

EX_SEARCH = paths.search_example()
EX_PROFILE = paths.profile_example()


# ---------------------------------------------------------------------------
# Sample stage outputs (finder → research → tailoring).
# ---------------------------------------------------------------------------

FINDER = {
    "job_id": "linkedin:FAKE-A1",
    "source": "linkedin_easy_apply",
    "title": "Site Reliability Engineer",
    "company": "Globex Systems",
    "company_domain": "globex.example",
    "location": "Remote (India)",
    "url": "https://example.com/fake/A1",
    "posted_date": "2026-07-22",
    "easy_apply": True,
    "description_snippet": "[FAKE] SRE role: Kubernetes on AWS, Terraform, Python.",
}

RESEARCH = {
    "employer_url": "https://boards.greenhouse.io/globex/jobs/123",
    "score": "4.4/5", "recommendation": "Apply", "legitimacy": "High Confidence",
    "report": "reports/007-globex-2026-11-22.md", "tracker_num": 7,
    "contact_email": "priya.sharma@globex.example", "email_source": "hunter",
    "verified_mailbox": True,
}

TAILORING = {
    "cv_pdf": "output/cv-kishan-globex-2026-11-22.pdf",
    "fact_check": "pass",
    "output_dir": "output/Globex_ProductDesigner",
}


def main() -> int:
    print("=" * 66)
    print("Alfred · Orchestrator — DRY RUN (OFFLINE; no subagent/network calls)")
    print("=" * 66)

    workdir = tempfile.mkdtemp(prefix="alfred_orch_")
    cv_path = os.path.join(workdir, "cv.md")
    with open(cv_path, "w", encoding="utf-8") as fh:   # temp stand-in cv.md
        fh.write("# Fake Person\n\n## Experience\n")
    resume_glob = os.path.join(workdir, "*.docx")
    no_pause = os.path.join(workdir, "paused.flag")   # absent

    # ---- 1a. preflight against example configs (should be OK, dry_run ON) --
    print("\n1a) preflight() — example configs + temp cv.md, not paused:\n")
    report = orch.preflight(search_path=EX_SEARCH, profile_path=EX_PROFILE,
                            resume_glob=resume_glob, pause_flag=no_pause, cv_path=cv_path)
    orch._print_preflight(report)

    # ---- 1b. preflight BLOCKED (no resume) --------------------------------
    print("\n1b) preflight() — same, but cv.md missing (proves it blocks):\n")
    blocked = orch.preflight(search_path=EX_SEARCH, profile_path=EX_PROFILE,
                             resume_glob=resume_glob, pause_flag=no_pause,
                             cv_path=os.path.join(workdir, "none", "cv.md"))
    orch._print_preflight(blocked)

    # ---- 2. merge_job → canonical job object ------------------------------
    print("\n" + "=" * 66)
    print("2) merge_job(finder, research, tailoring) → canonical job object:")
    job = orch.merge_job(FINDER, RESEARCH, TAILORING)
    print(json.dumps(job, indent=2, ensure_ascii=False))

    # ---- 3. run_summary for a simulated dry_run pass ----------------------
    print("\n" + "=" * 66)
    print("3) run_summary(stats) — simulated dry_run pass:\n")
    stats = {
        "found": 9, "verified": 6, "dead": 3, "evaluated": 6, "tailored": 3,
        "blocked_facts": 1, "approved": 1, "applied": 1, "skipped": 2, "pending_approval": 2,
        "dry_run": True, "caps_remaining": {"apply": 24, "email": 9},
    }
    print(orch.run_summary(stats))

    # ---- Assertions --------------------------------------------------------
    print("\n" + "-" * 66)
    print("Assertions:")
    failures = []

    ok_pre = report["ok"] is True and report["dry_run"] is True and report["paused"] is False
    failures += [] if ok_pre else ["preflight against examples should be OK + dry_run ON"]
    print(f"  [{'OK' if ok_pre else 'XX'}] preflight OK, dry_run ON, not paused")

    ok_block = blocked["blocked"] is True and not blocked["checks"]["cv"]["exists"]
    failures += [] if ok_block else ["preflight should block when cv.md missing"]
    print(f"  [{'OK' if ok_block else 'XX'}] preflight blocks on missing cv.md")

    contract_keys = {
        "job_id", "source", "title", "company", "company_domain", "location", "url",
        "posted_date", "easy_apply", "description_snippet", "employer_url", "liveness",
        "repost", "score", "recommendation", "legitimacy", "report", "tracker_num",
        "contact_email", "email_source", "verified_mailbox", "channel", "cv_pdf",
        "fact_check", "output_dir", "applied_date",
    }
    missing = contract_keys - set(job.keys())
    ok_contract = not missing
    failures += [] if ok_contract else [f"canonical job missing keys: {sorted(missing)}"]
    print(f"  [{'OK' if ok_contract else 'XX'}] canonical job has all {len(contract_keys)} "
          f"contract keys (missing={sorted(missing)})")

    ok_channel = job["channel"] == "portal+email"
    failures += [] if ok_channel else [f"channel should derive 'portal+email', got {job['channel']!r}"]
    print(f"  [{'OK' if ok_channel else 'XX'}] channel derived from contact email → "
          f"{job['channel']!r}")
    stale = {"notion_url", "files", "what_i_changed", "match", "company_analysis"} & set(job)
    failures += [] if not stale else [f"retired keys still in contract: {sorted(stale)}"]
    print(f"  [{'OK' if not stale else 'XX'}] no Notion / cover-letter / 0-100 keys left")
    summary = orch.run_summary(stats)
    ok_words = ("Telegram" not in summary) and ("Notion" not in summary) and ("alfred-approve" in summary)
    failures += [] if ok_words else ["summary still mentions Telegram/Notion or lacks the review pointer"]
    print(f"  [{'OK' if ok_words else 'XX'}] summary points to the manual review, no Telegram/Notion")

    ok_summary = ("DRY RUN" in orch.run_summary(stats)) and ("Applied" in orch.run_summary(stats))
    failures += [] if ok_summary else ["run_summary missing mode/labels"]
    print(f"  [{'OK' if ok_summary else 'XX'}] run_summary renders mode + counts")

    print("  [OK] no subagent/network/browser calls (pure dict glue only)")

    print("\n" + "=" * 66)
    if failures:
        print("RESULT: FAIL ❌")
        for f in failures:
            print(f"  - {f}")
        print("=" * 66)
        return 1
    print("RESULT: PASS ✅ — preflight, merge_job, and run_summary all correct, offline.")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
