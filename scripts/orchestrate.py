"""WarmApply · orchestrate — deterministic glue for the top-level runbook.

This is NOT a subagent and it invokes NO subagents and NO network. It is the small
set of pure helpers the main Claude Code session leans on while executing RUNBOOK.md:

    - preflight()          verify configs + resume, report dry_run and /pause
    - merge_job(...)       assemble the canonical job object (the data contract)
    - run_summary(stats)   format the end-of-run report

All AI/network/browser steps happen when the MAIN SESSION invokes the worker
subagents in .claude/agents/ — never in this file.

CLI:
    python scripts/orchestrate.py --preflight        # checks; nonzero exit if blocked
    python scripts/orchestrate.py --summary [stats.json]

Dependency: PyYAML (already in requirements.txt, used across WarmApply) to read the
YAML config. No network.
"""

from __future__ import annotations

import glob
import json
import os
import sys
from typing import Any, Dict, List, Optional

import yaml

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEARCH_CONFIG = os.path.join(_REPO_ROOT, "config", "search.yaml")
PROFILE_CONFIG = os.path.join(_REPO_ROOT, "config", "profile.yaml")
RESUME_GLOB = os.path.join(_REPO_ROOT, "data", "*.docx")
PAUSE_FLAG = os.path.join(_REPO_ROOT, "data", "paused.flag")


# ---------------------------------------------------------------------------
# preflight
# ---------------------------------------------------------------------------

def preflight(search_path: str = SEARCH_CONFIG,
              profile_path: str = PROFILE_CONFIG,
              resume_glob: str = RESUME_GLOB,
              pause_flag: str = PAUSE_FLAG) -> Dict[str, Any]:
    """Verify configs + resume exist; report dry_run and /pause status.

    Returns a report dict with `ok`/`blocked` and per-check detail. `blocked` is
    True if a required input is missing OR /pause is set — the runbook aborts then.
    """
    issues: List[str] = []

    search_exists = os.path.exists(search_path)
    profile_exists = os.path.exists(profile_path)
    resume_matches = sorted(glob.glob(resume_glob))
    resume_exists = len(resume_matches) > 0
    paused = os.path.exists(pause_flag)

    if not search_exists:
        issues.append(f"missing search config: {search_path} "
                      "(copy config/search.example.yaml → config/search.yaml)")
    if not profile_exists:
        issues.append(f"missing profile config: {profile_path} "
                      "(copy config/profile.example.yaml → config/profile.yaml)")
    if not resume_exists:
        issues.append(f"no master resume found at {resume_glob} "
                      "(put your .docx resume in data/)")

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

    blocked = (not search_exists) or (not profile_exists) or (not resume_exists) or paused

    return {
        "ok": not blocked,
        "blocked": blocked,
        "dry_run": dry_run,
        "paused": paused,
        "checks": {
            "search_config": {"path": search_path, "exists": search_exists},
            "profile_config": {"path": profile_path, "exists": profile_exists},
            "resume": {"glob": resume_glob, "found": resume_matches, "exists": resume_exists},
        },
        "issues": issues,
    }


def _print_preflight(report: Dict[str, Any]) -> None:
    print("WarmApply · preflight")
    print("-" * 60)
    c = report["checks"]

    def mark(ok: bool) -> str:
        return "✅" if ok else "❌"

    print(f"  {mark(c['search_config']['exists'])} search config  : {c['search_config']['path']}")
    print(f"  {mark(c['profile_config']['exists'])} profile config : {c['profile_config']['path']}")
    resume = c["resume"]
    resume_show = resume["found"][0] if resume["found"] else resume["glob"]
    print(f"  {mark(resume['exists'])} master resume  : {resume_show}")

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
        print("RESULT: OK — ready to run WarmApply.")
        if report["dry_run"]:
            print("  (dry_run is ON — a full pass will prepare everything but send/submit nothing.)")


# ---------------------------------------------------------------------------
# merge_job — the canonical job object (data contract)
# ---------------------------------------------------------------------------

def _derive_channel(research: Dict[str, Any]) -> str:
    if research.get("channel") in ("portal", "email"):
        return research["channel"]
    email = research.get("email") or {}
    if email.get("address") and email.get("verified") and email.get("source") not in (None, "", "none"):
        return "email"
    return "portal"


def merge_job(finder: Dict[str, Any],
              research: Optional[Dict[str, Any]] = None,
              tailoring: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Assemble the canonical job object from the three stages.

    Pure dict merge; any missing key degrades to null so the contract shape is
    always complete regardless of how far a job progressed.
    """
    finder = finder or {}
    research = research or {}
    tailoring = tailoring or {}

    return {
        # from job-finder
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
        # added by company-research
        "company_analysis": research.get("company_analysis"),
        "email": research.get("email"),
        "match": research.get("match"),
        "channel": _derive_channel(research) if research else None,
        # added by resume-cover-letter
        "files": tailoring.get("files"),
        "what_i_changed": tailoring.get("what_i_changed"),
        # added by tracker
        "notion_url": tailoring.get("notion_url"),
        # updated by application-agent
        "applied_date": tailoring.get("applied_date"),
        "reply": tailoring.get("reply", False),
        "follow_up_sent": tailoring.get("follow_up_sent", False),
    }


# ---------------------------------------------------------------------------
# run_summary — end-of-run report
# ---------------------------------------------------------------------------

def run_summary(stats: Dict[str, Any]) -> str:
    """Format the end-of-run report from a stats dict.

    Recognized keys (all optional, default 0/empty):
      found, researched, tailored, tracked, approved, applied, skipped,
      pending_approval, dry_run,
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
        f"WarmApply · run summary   [mode: {mode}]",
        "=" * 60,
        f"  Found (fresh, de-duped) : {g('found')}",
        f"  Researched              : {g('researched')}",
        f"  Tailored                : {g('tailored')}",
        f"  Tracked (Notion rows)   : {g('tracked')}",
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
        lines.append(f"  ⏳ {g('pending_approval')} job(s) waiting for a Telegram tap "
                     "(Approve/Skip) — will be picked up next run.")
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
