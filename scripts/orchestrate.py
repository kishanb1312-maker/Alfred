"""Alfred · orchestrate — deterministic glue for the top-level runbook.

This is NOT a subagent and it invokes NO subagents and NO network. It is the small
set of pure helpers the main Claude Code session leans on while executing RUNBOOK.md:

    - preflight()          verify configs + resume, report dry_run and /pause
    - merge_job(...)       assemble the canonical job object (the data contract)
    - run_summary(stats)   format the end-of-run report

All AI/network/browser steps happen when the MAIN SESSION invokes the worker
subagents in agents/ — never in this file.

CLI:
    python scripts/orchestrate.py --preflight        # checks; nonzero exit if blocked
    python scripts/orchestrate.py --summary [stats.json]

Dependency: PyYAML (already in requirements.txt, used across Alfred) to read the
YAML config. No network.
"""

from __future__ import annotations

import glob
import json
import os
import sys
from typing import Any, Dict, List, Optional

import yaml

import paths  # single source of truth for all filesystem paths (§4)

# Resolved at import time via paths.py (whose DATA_HOME/CODE_ROOT are computed once
# when the module is imported), so both the plugin layout (~/.alfred) and the
# legacy clone-and-run layout (repo root) work with no change to the logic below.
SEARCH_CONFIG = paths.search_config()
PROFILE_CONFIG = paths.profile_config()
RESUME_GLOB = paths.resume_glob()
PAUSE_FLAG = paths.pause_flag()
CV_PATH = paths.cv_md()


# ---------------------------------------------------------------------------
# preflight
# ---------------------------------------------------------------------------

def preflight(search_path: str = SEARCH_CONFIG,
              profile_path: str = PROFILE_CONFIG,
              resume_glob: str = RESUME_GLOB,
              pause_flag: str = PAUSE_FLAG,
              cv_path: str = CV_PATH) -> Dict[str, Any]:
    """Verify configs + cv.md exist; report dry_run and /pause status.

    cv.md is the CV career-ops tailors from. The .docx is only needed once, to
    create it (`alfred cv-from-docx`), so a missing .docx is reported, not blocking.

    Returns a report dict with `ok`/`blocked` and per-check detail. `blocked` is
    True if a required input is missing OR /pause is set — the runbook aborts then.
    """
    issues: List[str] = []

    search_exists = os.path.exists(search_path)
    profile_exists = os.path.exists(profile_path)
    resume_matches = sorted(glob.glob(resume_glob))
    resume_exists = len(resume_matches) > 0
    cv_exists = os.path.isfile(cv_path)
    paused = os.path.exists(pause_flag)

    if not search_exists:
        issues.append(f"missing search config: {search_path} "
                      "(copy config/search.example.yaml → config/search.yaml)")
    if not profile_exists:
        issues.append(f"missing profile config: {profile_path} "
                      "(copy config/profile.example.yaml → config/profile.yaml)")
    if not cv_exists:
        issues.append(f"no cv.md at {cv_path} "
                      "(alfred cv-from-docx <your resume.docx>, then /alfred:alfred-setup)")

    # Read dry_run only if the search config is present + parseable.
    dry_run: Optional[bool] = None
    if search_exists:
        try:
            with open(search_path, "r", encoding="utf-8") as fh:
                cfg = yaml.safe_load(fh) or {}
            dry_run = bool(cfg.get("dry_run", False))
        except (yaml.YAMLError, OSError) as exc:
            issues.append(f"could not parse {search_path}: {exc}")

    if paused:
        issues.append(f"/pause is set ({pause_flag}) — application-agent must not act")

    blocked = (not search_exists) or (not profile_exists) or (not cv_exists) or paused

    return {
        "ok": not blocked,
        "blocked": blocked,
        "dry_run": dry_run,
        "paused": paused,
        "checks": {
            "search_config": {"path": search_path, "exists": search_exists},
            "profile_config": {"path": profile_path, "exists": profile_exists},
            "resume": {"glob": resume_glob, "found": resume_matches, "exists": resume_exists},
            "cv": {"path": cv_path, "exists": cv_exists},
        },
        "issues": issues,
    }


def _print_preflight(report: Dict[str, Any]) -> None:
    print("Alfred · preflight")
    print("-" * 60)
    c = report["checks"]

    def mark(ok: bool) -> str:
        return "✅" if ok else "❌"

    print(f"  {mark(c['search_config']['exists'])} search config  : {c['search_config']['path']}")
    print(f"  {mark(c['profile_config']['exists'])} profile config : {c['profile_config']['path']}")
    print(f"  {mark(c['cv']['exists'])} cv.md          : {c['cv']['path']}")

    dry = report["dry_run"]
    dry_show = "ON (no real sends/submits)" if dry else ("OFF (LIVE)" if dry is False else "unknown")
    print(f"  •  dry_run        : {dry_show}")
    print(f"  {'⛔' if report['paused'] else '▶️ '} /pause         : "
          f"{'SET — will halt' if report['paused'] else 'not set'}")

    print("-" * 60)
    if report["blocked"]:
        print("RESULT: BLOCKED — resolve before running:")
        for issue in report["issues"]:
            print(f"  - {issue}")
    else:
        print("RESULT: OK — ready to run Alfred.")
        if report["dry_run"]:
            print("  (dry_run is ON — a full pass will prepare everything but send/submit nothing.)")


# ---------------------------------------------------------------------------
# merge_job — the canonical job object (data contract)
# ---------------------------------------------------------------------------

def _derive_channel(research: Dict[str, Any]) -> str:
    if research.get("channel") in ("portal", "email"):
        return research["channel"]
    if research.get("contact_email") or (research.get("email") or {}).get("address"):
        return "portal+email"
    return "portal"


def merge_job(finder: Dict[str, Any],
              research: Optional[Dict[str, Any]] = None,
              tailoring: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Assemble the canonical job object from the stages.

    Pure dict merge; any missing key degrades to null so the contract shape is
    always complete regardless of how far a job progressed.
    """
    finder = finder or {}
    research = research or {}
    tailoring = tailoring or {}

    return {
        # job-finder
        "job_id": finder.get("job_id"),
        "source": finder.get("source"),
        "title": finder.get("title"),
        "company": finder.get("company"),
        "company_domain": finder.get("company_domain"),
        "location": finder.get("location"),
        "url": finder.get("url"),
        "posted_date": finder.get("posted_date"),
        "easy_apply": finder.get("easy_apply"),
        "description_snippet": finder.get("description_snippet"),
        # job-verifier
        "employer_url": finder.get("employer_url") or research.get("employer_url"),
        "liveness": finder.get("liveness") or research.get("liveness"),
        "repost": finder.get("repost") or research.get("repost"),
        # job-evaluator (career-ops A-H report, 1-5 score) + contact finder
        "score": research.get("score"),
        "recommendation": research.get("recommendation"),
        "legitimacy": research.get("legitimacy"),
        "report": research.get("report"),
        "tracker_num": research.get("tracker_num"),
        "contact_email": research.get("contact_email") or (research.get("email") or {}).get("address"),
        "email_source": research.get("email_source"),
        "verified_mailbox": research.get("verified_mailbox"),
        "channel": _derive_channel(research) if research else None,
        # cv-tailor
        "cv_pdf": tailoring.get("cv_pdf"),
        "fact_check": tailoring.get("fact_check"),
        "output_dir": tailoring.get("output_dir"),
        # application-agent
        "applied_date": tailoring.get("applied_date"),
    }


# ---------------------------------------------------------------------------
# run_summary — end-of-run report
# ---------------------------------------------------------------------------

def run_summary(stats: Dict[str, Any]) -> str:
    """Format the end-of-run report from a stats dict.

    Recognized keys (all optional, default 0/empty):
      found, verified, dead, evaluated, tailored, blocked_facts, approved, applied,
      skipped, pending_approval, dry_run,
      caps_remaining: {"apply": int, "email": int}
    """
    stats = stats or {}
    caps = stats.get("caps_remaining") or {}

    def g(k: str) -> int:
        return int(stats.get(k, 0) or 0)

    dry = stats.get("dry_run")
    mode = "DRY RUN (nothing sent/submitted)" if dry else ("LIVE" if dry is False else "unknown")

    lines = [
        "=" * 60,
        f"Alfred · run summary   [mode: {mode}]",
        "=" * 60,
        f"  Found (fresh, de-duped) : {g('found')}",
        f"  Still open (verified)   : {g('verified')}   closed/unconfirmed dropped: {g('dead')}",
        f"  Evaluated (A-H, 1-5)    : {g('evaluated')}",
        f"  CV tailored + checked   : {g('tailored')}   blocked by fact check: {g('blocked_facts')}",
        f"  Approved                : {g('approved')}",
        f"  Applied                 : {g('applied')}",
        f"  Skipped                 : {g('skipped')}",
        "-" * 60,
        f"  Pending your approval   : {g('pending_approval')}",
        f"  Caps remaining today    : applies={caps.get('apply', '—')}  "
        f"emails={caps.get('email', '—')}",
        "=" * 60,
    ]
    if g("pending_approval"):
        lines.append(f"  ⏳ {g('pending_approval')} job(s) waiting for you — "
                     "/alfred:alfred-approve, or `alfred review` in a terminal.")
    lines.append("  Tracker: data/applications.md   Reports: reports/")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli(argv: List[str]) -> int:
    if "--preflight" in argv:
        report = preflight()
        _print_preflight(report)
        return 1 if report["blocked"] else 0

    if "--summary" in argv:
        idx = argv.index("--summary")
        stats: Dict[str, Any] = {}
        if idx + 1 < len(argv):
            with open(argv[idx + 1], "r", encoding="utf-8") as fh:
                stats = json.load(fh)
        elif not sys.stdin.isatty():
            raw = sys.stdin.read().strip()
            if raw:
                stats = json.loads(raw)
        print(run_summary(stats))
        return 0

    print(__doc__)
    print("usage: python scripts/orchestrate.py [--preflight | --summary [stats.json]]")
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
