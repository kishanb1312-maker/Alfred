"""WarmApply · Job Finder DRY-RUN (no network, no browser, fake data).

Demonstrates the de-dupe pipeline end-to-end:
  1. read config/search.example.yaml,
  2. fabricate a few CLEARLY-FAKE sample jobs,
  3. run them through scripts/applied_history.py de-dupe,
  4. print the normalized, de-duplicated output list.

This does NOT call LinkedIn or Adzuna. Every job below is fake sample data,
labeled as such, per the "No fabrication" guardrail (dry-run only).

Config is parsed with PyYAML's ``yaml.safe_load`` — the same call the real
Job Finder uses on ``config/search.yaml`` (see requirements.txt: PyYAML>=6.0).
"""

from __future__ import annotations

import json
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import applied_history  # noqa: E402

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(_REPO_ROOT, "config", "search.example.yaml")


# ---------------------------------------------------------------------------
# Config reader — PyYAML (same as the real Job Finder on config/search.yaml)
# ---------------------------------------------------------------------------

def load_config(path: str) -> dict:
    """Read a WarmApply YAML config via yaml.safe_load()."""
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data or {}


# ---------------------------------------------------------------------------
# Fake sample jobs (DRY-RUN ONLY — none of these are real listings)
# ---------------------------------------------------------------------------

def sample_jobs() -> list:
    return [
        {
            "job_id": "linkedin:FAKE-0001",
            "source": "linkedin_easy_apply",
            "title": "Site Reliability Engineer",
            "company": "Globex Systems",
            "company_domain": None,
            "location": "Remote (India)",
            "url": "https://example.com/fake/0001",
            "posted_date": "2026-07-22",
            "easy_apply": True,
            "description_snippet": "[FAKE] Own SLOs, on-call, and Terraform-driven infra...",
            "found_at": "2026-07-24T18:30:00Z",
        },
        {
            "job_id": "adzuna:FAKE-0002",
            "source": "adzuna",
            "title": "DevOps Engineer",
            "company": "Initech",
            "company_domain": "initech.example",
            "location": "Bengaluru",
            "url": "https://example.com/fake/0002",
            "posted_date": "2026-07-23",
            "easy_apply": False,
            "description_snippet": "[FAKE] CI/CD pipelines, Kubernetes, and observability...",
            "found_at": "2026-07-24T18:30:05Z",
        },
        {
            # Duplicate of 0001 by company + normalized title (different casing/id)
            "job_id": "adzuna:FAKE-0003",
            "source": "adzuna",
            "title": "site   reliability   ENGINEER",
            "company": "globex systems",
            "company_domain": None,
            "location": "Remote (India)",
            "url": "https://example.com/fake/0003",
            "posted_date": "2026-07-22",
            "easy_apply": False,
            "description_snippet": "[FAKE] Same role as 0001, should be de-duped...",
            "found_at": "2026-07-24T18:30:07Z",
        },
        {
            # Blacklisted company (Acme Corp is in search.example.yaml blacklist)
            "job_id": "linkedin:FAKE-0004",
            "source": "linkedin_easy_apply",
            "title": "Platform Engineer",
            "company": "Acme Corp",
            "company_domain": None,
            "location": "Bengaluru",
            "url": "https://example.com/fake/0004",
            "posted_date": "2026-07-24",
            "easy_apply": True,
            "description_snippet": "[FAKE] Should be dropped — company is blacklisted...",
            "found_at": "2026-07-24T18:30:09Z",
        },
    ]


# ---------------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 72)
    print("WarmApply · Job Finder — DRY RUN (fake data, no network, no browser)")
    print("=" * 72)

    cfg = load_config(CONFIG_PATH)
    blacklist = cfg.get("blacklist_companies", []) or []
    cap = (cfg.get("caps") or {}).get("applies_per_day")

    print(f"\nConfig: {os.path.relpath(CONFIG_PATH, _REPO_ROOT)}")
    print(f"  roles              : {cfg.get('roles')}")
    print(f"  locations          : {cfg.get('locations')}")
    print(f"  sources            : {cfg.get('sources')}")
    print(f"  blacklist_companies: {blacklist}")
    print(f"  caps.applies_per_day: {cap}")
    print(f"  dry_run            : {cfg.get('dry_run')}")

    jobs = sample_jobs()
    print(f"\nFabricated {len(jobs)} FAKE sample jobs (labeled [FAKE] in snippets).")

    # Use a throwaway store so the demo never pollutes real history.
    demo_store = os.path.join(_REPO_ROOT, "data", "applied_history.dryrun.json")
    if os.path.exists(demo_store):
        os.remove(demo_store)

    fresh = applied_history.dedupe(jobs, blacklist, path=demo_store)

    # Respect caps: never surface more than can be actioned in a day.
    if isinstance(cap, int) and cap >= 0:
        fresh = fresh[:cap]

    # Mark each surfaced job as "seen" in the demo store (as the agent would).
    for job in fresh:
        applied_history.mark_seen(job, path=demo_store)

    dropped = len(jobs) - len(fresh)
    print(f"\nDe-dupe result: {len(fresh)} fresh, {dropped} dropped "
          "(duplicate / blacklisted).")
    print("\nNormalized, de-duplicated output list:")
    print(json.dumps(fresh, indent=2, ensure_ascii=False))

    os.remove(demo_store)  # clean up the throwaway store
    print(f"\n(Throwaway demo store {os.path.basename(demo_store)} removed; "
          "real data/applied_history.json untouched.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
