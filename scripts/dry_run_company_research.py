"""WarmApply · Company Research DRY-RUN (offline, mocked network).

Demonstrates the enrichment pipeline WITHOUT any live calls:
  1. read the match threshold from config/search.example.yaml,
  2. use 2 CLEARLY-FAKE jobs + a FAKE sample profile (profile.yaml shape),
  3. MOCK company analysis + the email waterfall (no web/Hunter/LinkedIn),
  4. run the REAL email_verify syntax check (MX skipped — offline) and the REAL
     match_score baseline,
  5. print the enriched objects and which jobs pass the 70 match threshold.

Nothing here touches the network. Mocked values are labeled [MOCK]; sample jobs
and profile are labeled [FAKE], per the "no fabrication" guardrail (dry-run only).
"""

from __future__ import annotations

import json
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import email_verify  # noqa: E402
import match_score  # noqa: E402

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEARCH_CFG = os.path.join(_REPO_ROOT, "config", "search.example.yaml")


# ---------------------------------------------------------------------------
# FAKE sample profile (config/profile.yaml shape) — none of this is real.
# In a live run the agent reads config/profile.yaml (or profile.example.yaml).
# ---------------------------------------------------------------------------

FAKE_PROFILE_YAML = """
personal:
  full_name: "Fake Candidate"
  email: "fake.candidate@example.com"
  location: "Bengaluru, India"
years_experience:
  python: 5
  aws: 4
  docker: 4
  kubernetes: 3
  terraform: 2
  linux: 6
  react: 0
"""


# ---------------------------------------------------------------------------
# 2 FAKE jobs (job-finder output shape). Job A should pass, Job B should fail.
# ---------------------------------------------------------------------------

def fake_jobs() -> list:
    return [
        {
            "job_id": "linkedin:FAKE-A1",
            "source": "linkedin_easy_apply",
            "title": "Site Reliability Engineer",
            "company": "Globex Systems",
            "company_domain": "globex.example",
            "location": "Remote (India)",
            "url": "https://example.com/fake/A1",
            "posted_date": "2026-07-22",
            "easy_apply": True,
            "description_snippet": (
                "[FAKE] SRE role: own SLOs and on-call. Stack is Kubernetes on AWS, "
                "Docker, Terraform for IaC, and Python automation across Linux fleets. "
                "CI/CD and observability experience valued."
            ),
            "found_at": "2026-07-24T18:30:00Z",
        },
        {
            "job_id": "adzuna:FAKE-B2",
            "source": "adzuna",
            "title": "Frontend Engineer",
            "company": "Initech",
            "company_domain": "initech.example",
            "location": "Bengaluru",
            "url": "https://example.com/fake/B2",
            "posted_date": "2026-07-23",
            "easy_apply": False,
            "description_snippet": (
                "[FAKE] Frontend role building React + TypeScript UIs with modern CSS, "
                "design systems, and accessibility. Figma-to-code workflow."
            ),
            "found_at": "2026-07-24T18:30:05Z",
        },
    ]


# ---------------------------------------------------------------------------
# MOCK company analysis (would be WebSearch + WebFetch in a live run).
# ---------------------------------------------------------------------------

MOCK_ANALYSIS = {
    "linkedin:FAKE-A1": {
        "summary": "[MOCK] SaaS infra company running large Kubernetes platforms.",
        "industry": "Cloud infrastructure",
        "size": "201-500",
        "tech_stack": ["Kubernetes", "AWS", "Terraform", "Python"],
        "values_culture": "[MOCK] reliability-first, strong on-call culture",
        "recent_signal": "[MOCK] announced a multi-region platform launch",
        "website": "https://globex.example",
    },
    "adzuna:FAKE-B2": {
        "summary": "[MOCK] B2B web app studio shipping React products.",
        "industry": "Software",
        "size": "51-200",
        "tech_stack": ["React", "TypeScript", "Node.js"],
        "values_culture": "[MOCK] design-led, ships fast",
        "recent_signal": "[MOCK] rebranded its design system",
        "website": "https://initech.example",
    },
}


# ---------------------------------------------------------------------------
# MOCK email waterfall. Returns a candidate + the step that "won" + a mocked
# confidence. The REAL verifier then runs (syntax only; MX skipped offline).
# ---------------------------------------------------------------------------

def mock_waterfall(job: dict) -> dict:
    """Pretend we ran the waterfall. NO network. Returns pre-verification info."""
    if job["job_id"] == "linkedin:FAKE-A1":
        # Step 2: email-finder API "returned" a personal recruiter email.
        return {
            "candidate": "priya.sharma@globex.example",
            "recipient_name": "Priya Sharma",
            "confidence": 92,          # [MOCK] finder confidence → ≥85 accept normally
            "source": "hunter",
            "is_personal": True,
            "patterns_considered": email_verify.generate_patterns(
                "Priya", "Sharma", "globex.example"
            ),
        }
    # Job B: no personal email; Step 1 generic inbox, lower confidence.
    return {
        "candidate": "careers@initech.example",
        "recipient_name": None,
        "confidence": 70,              # [MOCK] generic inbox → 60-84 FLAG band
        "source": "career-page",
        "is_personal": False,
        "patterns_considered": email_verify.generate_patterns(
            "", "", "initech.example"
        ),
    }


def apply_confidence_gate(confidence: int) -> str:
    """WarmApply gates: ≥85 send · 60-84 flag · <60 not-found."""
    if confidence >= 85:
        return "accept"
    if confidence >= 60:
        return "flag"
    return "not_found"


# ---------------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------------

def enrich(job: dict, profile: dict, threshold: int) -> dict:
    # --- Email (mock discovery + REAL offline verify) ---
    wf = mock_waterfall(job)
    gate = apply_confidence_gate(wf["confidence"])
    # REAL verifier, offline: syntax only, MX skipped (no DNS in dry-run).
    vres = email_verify.verify(wf["candidate"], check_mx=False)

    if gate == "not_found" or not vres["ok"]:
        email_block = {
            "address": None, "recipient_name": None, "confidence": wf["confidence"],
            "source": "none", "verified": False, "is_personal": False,
            "flagged": False, "mx_checked": False,
        }
    else:
        email_block = {
            "address": wf["candidate"],
            "recipient_name": wf["recipient_name"],
            "confidence": wf["confidence"],
            "source": wf["source"],
            "verified": bool(vres["ok"]),        # syntax-verified (MX skipped offline)
            "is_personal": wf["is_personal"],
            "flagged": gate == "flag",           # 60-84 → surfaced on Telegram card
            "mx_checked": False,                 # offline dry-run: DNS not queried
        }

    # --- Match (REAL deterministic baseline) ---
    job_text = f"{job['title']} {job['description_snippet']}"
    detail = match_score.baseline_detail(job_text, profile)
    score = detail["score"]
    meets = score >= threshold
    rationale = (
        f"baseline skill overlap {score}/100 "
        f"(matched: {', '.join(detail['matched']) or 'none'})"
    )

    enriched = dict(job)
    enriched["company_analysis"] = MOCK_ANALYSIS[job["job_id"]]
    enriched["email"] = email_block
    enriched["match"] = {
        "score": score,
        "rationale": rationale,
        "meets_threshold": meets,
    }
    enriched["_debug_patterns"] = wf["patterns_considered"]
    return enriched


def main() -> int:
    print("=" * 72)
    print("WarmApply · Company Research — DRY RUN (offline, mocked network)")
    print("=" * 72)

    cfg = yaml.safe_load(open(SEARCH_CFG, encoding="utf-8")) or {}
    threshold = int(cfg.get("match_threshold", 70))
    profile = yaml.safe_load(FAKE_PROFILE_YAML) or {}

    print(f"\nmatch_threshold : {threshold}  (from {os.path.relpath(SEARCH_CFG, _REPO_ROOT)})")
    print("profile         : [FAKE] in-script sample (profile.yaml shape)")
    print(f"profile skills  : {sorted((profile.get('years_experience') or {}).keys())}")
    print("company analysis + email waterfall are [MOCK] (no live calls).")
    print("email_verify (syntax) + match_score (baseline) run FOR REAL, offline.\n")

    jobs = fake_jobs()
    enriched = [enrich(j, profile, threshold) for j in jobs]

    print("Enriched job records:")
    print(json.dumps(enriched, indent=2, ensure_ascii=False))

    passed = [e for e in enriched if e["match"]["meets_threshold"]]
    dropped = [e for e in enriched if not e["match"]["meets_threshold"]]

    print("\n" + "-" * 72)
    print(f"Threshold filter (>= {threshold}):")
    for e in enriched:
        verdict = "PASS ✅" if e["match"]["meets_threshold"] else "DROP ✂️"
        print(f"  {verdict}  {e['company']:<16} {e['title']:<26} "
              f"score={e['match']['score']:>3}  "
              f"email={e['email']['address'] or 'portal-only'}"
              f"{' [FLAG]' if e['email'].get('flagged') else ''}")
    print(f"\n{len(passed)} job(s) handed off to resume-cover-letter; "
          f"{len(dropped)} dropped below threshold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
