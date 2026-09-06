"""Alfred · Company Research DRY-RUN (offline, mocked network).

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
import paths  # noqa: E402  bundled example config lives under CODE_ROOT

SEARCH_CFG = paths.search_example()


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
            "job_id": "wellfound:FAKE-B2",
            "source": "wellfound",
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
        {
            # Job C: survives threshold, but the waterfall finds NO listed email →
            # exercises the single-best pattern-guess fallback.
            "job_id": "remoteok:FAKE-C3",
            "source": "remoteok",
            "title": "Platform / SRE Engineer",
            "company": "Zephyr Labs",
            "company_domain": "zephyr.example",
            "location": "Remote (India)",
            "url": "https://example.com/fake/C3",
            "posted_date": "2026-07-24",
            "easy_apply": False,
            "description_snippet": (
                "[FAKE] Platform engineer: Kubernetes on AWS, Terraform IaC, Python "
                "automation, Linux. Reliability and CI/CD focus."
            ),
            "found_at": "2026-07-24T18:30:07Z",
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
    "wellfound:FAKE-B2": {
        "summary": "[MOCK] B2B web app studio shipping React products.",
        "industry": "Software",
        "size": "51-200",
        "tech_stack": ["React", "TypeScript", "Node.js"],
        "values_culture": "[MOCK] design-led, ships fast",
        "recent_signal": "[MOCK] rebranded its design system",
        "website": "https://initech.example",
    },
    "remoteok:FAKE-C3": {
        "summary": "[MOCK] Infra startup running Kubernetes platforms.",
        "industry": "Cloud infrastructure",
        "size": "11-50",
        "tech_stack": ["Kubernetes", "AWS", "Terraform"],
        "values_culture": "[MOCK] small, ships fast",
        "recent_signal": "[MOCK] launched a managed platform",
        "website": "https://zephyr.example",
    },
}


# ---------------------------------------------------------------------------
# MOCK email waterfall. Returns a candidate + the step that "won" + a mocked
# confidence. The REAL verifier then runs (syntax only; MX skipped offline).
# ---------------------------------------------------------------------------

def mock_waterfall(job: dict) -> dict:
    """Pretend we ran the waterfall. NO network. Returns pre-verification info.

    `candidate` is the email found by steps 1–3 (or None → triggers the step-4
    pattern-guess). `recruiter_name` may be known even when no email was found.
    """
    if job["job_id"] == "linkedin:FAKE-A1":
        # Step 2: email-finder API "returned" a personal recruiter email.
        return {
            "candidate": "priya.sharma@globex.example",
            "recipient_name": "Priya Sharma", "first": "Priya", "last": "Sharma",
            "confidence": 92,          # [MOCK] finder confidence → ≥85 accept normally
            "source": "hunter",
            "is_personal": True,
        }
    if job["job_id"] == "wellfound:FAKE-B2":
        # Step 1: generic inbox, lower confidence.
        return {
            "candidate": "careers@initech.example",
            "recipient_name": None, "first": "", "last": "",
            "confidence": 70,          # [MOCK] generic inbox → 60-84 FLAG band
            "source": "career-page",
            "is_personal": False,
        }
    # Job C: steps 1–3 found NO email, but LinkedIn gave a recruiter NAME →
    # step 4 pattern-guess fallback will run against the real company domain.
    return {
        "candidate": None,
        "recipient_name": "Alex Kim", "first": "Alex", "last": "Kim",
        "confidence": 0,
        "source": None,
        "is_personal": False,
    }


def apply_confidence_gate(confidence: int) -> str:
    """Alfred gates: ≥85 send · 60-84 flag · <60 not-found."""
    if confidence >= 85:
        return "accept"
    if confidence >= 60:
        return "flag"
    return "not_found"


# ---------------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------------

def resolve_email(job: dict, wf: dict) -> dict:
    """Dual-channel email resolution: use the waterfall's find, else fall back to a
    single best pattern-guess against the company's REAL domain. Offline (MX skipped).

    Returns the canonical dual-channel fields for the enriched job.
    """
    candidate = wf.get("candidate")
    source = wf.get("source")
    verified_mailbox = source in ("hunter", "apollo")  # finder-confirmed only

    if not candidate:
        # Step 4 — single best pattern-guess (needs a name + the real domain).
        domain = job.get("company_domain")
        guess = email_verify.best_guess(wf.get("first", ""), wf.get("last", ""),
                                        domain, check_mx=False)  # offline: no DNS
        if guess["email"]:
            candidate = guess["email"]
            source = guess["source"]            # "pattern"
            verified_mailbox = guess["verified_mailbox"]  # False for a guess

    # REAL syntax verify (offline; MX skipped — no DNS in a dry-run).
    ok = bool(candidate) and email_verify.verify(candidate, check_mx=False)["ok"]
    if not ok:
        candidate, source = None, "none"

    cold_email = bool(candidate)
    return {
        "contact_email": candidate,
        "email_source": source if candidate else "none",
        "verified_mailbox": bool(verified_mailbox) if candidate else False,
        "cold_email": cold_email,
        "recipient_name": wf.get("recipient_name"),
        "confidence": wf.get("confidence"),
    }


def enrich(job: dict, profile: dict, threshold: int) -> dict:
    # --- Email (mock discovery + REAL offline verify + pattern-guess fallback) ---
    wf = mock_waterfall(job)
    em = resolve_email(job, wf)
    guessed = em["email_source"] == "pattern"

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
    enriched["email"] = {
        "address": em["contact_email"], "recipient_name": em["recipient_name"],
        "confidence": em["confidence"], "source": em["email_source"],
        "verified": em["verified_mailbox"], "flagged": guessed,
    }
    enriched["match"] = {"score": score, "rationale": rationale, "meets_threshold": meets}
    # dual-channel fields (every surviving job)
    enriched["apply_portal"] = True
    enriched["cold_email"] = em["cold_email"]
    enriched["contact_email"] = em["contact_email"]
    enriched["email_source"] = em["email_source"]
    enriched["verified_mailbox"] = em["verified_mailbox"]
    enriched["bounced"] = False
    return enriched


def main() -> int:
    print("=" * 72)
    print("Alfred · Company Research — DRY RUN (offline, mocked network)")
    print("=" * 72)

    cfg = yaml.safe_load(open(SEARCH_CFG, encoding="utf-8")) or {}
    threshold = int(cfg.get("match_threshold", 70))
    profile = yaml.safe_load(FAKE_PROFILE_YAML) or {}

    print(f"\nmatch_threshold : {threshold}  (from {os.path.relpath(SEARCH_CFG, paths.CODE_ROOT)})")
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
    print(f"Threshold filter (>= {threshold}) + dual-channel plan:")
    for e in enriched:
        verdict = "PASS ✅" if e["match"]["meets_threshold"] else "DROP ✂️"
        chans = "portal" + (" + email" if e["cold_email"] else " only")
        guess = " ⚠️guess" if e["email_source"] == "pattern" else ""
        print(f"  {verdict}  {e['company']:<14} {e['title']:<24} "
              f"score={e['match']['score']:>3}  [{chans}] "
              f"email={e['contact_email'] or 'none'}{guess}")
    print(f"\n{len(passed)} job(s) handed off to resume-cover-letter; "
          f"{len(dropped)} dropped below threshold.")

    # ---- Assertions --------------------------------------------------------
    by_id = {e["job_id"]: e for e in enriched}
    print("\n" + "-" * 72)
    print("Assertions:")
    failures = []

    # 1: every job carries the dual-channel fields (apply_portal + cold_email + ...).
    dc_keys = {"apply_portal", "cold_email", "contact_email", "email_source",
               "verified_mailbox", "bounced"}
    ok_fields = all(dc_keys <= set(e.keys()) and e["apply_portal"] is True for e in enriched)
    failures += [] if ok_fields else ["dual-channel fields missing on some job"]
    print(f"  [{'OK' if ok_fields else 'XX'}] every job has dual-channel fields, apply_portal=True")

    # 2: every job has an email OR a null-with-reason (email_source=='none').
    ok_email_or_reason = all(
        (e["contact_email"] and e["email_source"] != "none")
        or (e["contact_email"] is None and e["email_source"] == "none")
        for e in enriched)
    failures += [] if ok_email_or_reason else ["a job has an inconsistent email/source"]
    print(f"  [{'OK' if ok_email_or_reason else 'XX'}] every job → an email or null-with-reason")

    # 3: pattern-guess fallback produced ONE best guess (first.last@real-domain),
    #    tagged source='pattern', verified_mailbox=False.
    c = by_id["remoteok:FAKE-C3"]
    ok_guess = (c["contact_email"] == "alex.kim@zephyr.example"
                and c["email_source"] == "pattern"
                and c["verified_mailbox"] is False
                and c["cold_email"] is True)
    failures += [] if ok_guess else [f"pattern-guess wrong: {c['contact_email']}, "
                                     f"src={c['email_source']}, vm={c['verified_mailbox']}"]
    print(f"  [{'OK' if ok_guess else 'XX'}] pattern-guess fallback → {c['contact_email']} "
          f"(source=pattern, verified_mailbox=False)")

    # 4: a finder email stays verified_mailbox=True; guess never fabricates a domain.
    a = by_id["linkedin:FAKE-A1"]
    ok_finder = a["email_source"] == "hunter" and a["verified_mailbox"] is True
    ok_domain = c["contact_email"].endswith("@zephyr.example")  # the REAL company domain
    failures += [] if (ok_finder and ok_domain) else ["finder/domain rule wrong"]
    print(f"  [{'OK' if ok_finder and ok_domain else 'XX'}] finder email verified_mailbox=True; "
          f"guess uses the real company domain (no fabrication)")

    print("\n" + "=" * 72)
    if failures:
        print("RESULT: FAIL ❌")
        for f in failures:
            print(f"  - {f}")
        print("=" * 72)
        return 1
    print("RESULT: PASS ✅ — dual-channel email-for-every-job + single best guess; offline.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
