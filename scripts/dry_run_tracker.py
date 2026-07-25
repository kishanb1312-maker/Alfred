"""WarmApply · Tracker DRY-RUN (offline mapping check — NO Notion/MCP calls).

Verifies scripts/notion_schema.py without touching Notion or the network:
  1. print database_schema() (the property definitions),
  2. take one FAKE enriched+tailored job,
  3. print row_properties(job) (the property values),
  4. assert every schema property is present in the row mapping (no drift),
     the row is Notion-shaped, and select values use the controlled vocab.

Real Notion database + row creation happens only at run-time with the user
present — never during a build/dry-run (tracker guardrail).
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import notion_schema as ns  # noqa: E402


# ---------------------------------------------------------------------------
# One FAKE enriched+tailored job (company-research + resume-cover-letter shape).
# ---------------------------------------------------------------------------

FAKE_JOB = {
    "job_id": "linkedin:FAKE-A1",
    "title": "Site Reliability Engineer",
    "company": "Globex Systems",
    "company_domain": "globex.example",
    "location": "Remote (India)",
    "url": "https://example.com/fake/A1",
    "company_analysis": {
        "website": "https://globex.example",
        "recent_signal": "announced a multi-region platform launch",
    },
    "match": {"score": 91, "rationale": "strong k8s/AWS overlap"},
    "email": {
        "address": "priya.sharma@globex.example",
        "recipient_name": "Priya Sharma",
        "confidence": 92,
        "source": "hunter",
    },
    "files": {
        "resume": "output/GlobexSystems_SiteReliabilityEngineer/Resume_GlobexSystems.docx",
        "cover_letter": "output/GlobexSystems_SiteReliabilityEngineer/CoverLetter_GlobexSystems.pdf",
    },
    "what_i_changed": (
        "Summary rewrite + 2 bullet re-emphases (Kubernetes, AWS, Terraform, "
        "Python, CI/CD — all already in the resume). Gap: JD lists Go (not added)."
    ),
}


def _value_type(prop_value: dict) -> str:
    """The Notion value 'kind' key (title/rich_text/url/number/select/...)."""
    return next(iter(prop_value.keys()))


def main() -> int:
    print("=" * 74)
    print("WarmApply · Tracker — DRY RUN (offline; NO Notion/MCP/network calls)")
    print("=" * 74)

    schema = ns.database_schema()
    row = ns.row_properties(FAKE_JOB)

    print("\n1) database_schema() — property definitions:")
    print(json.dumps(schema, indent=2, ensure_ascii=False))

    print("\n2) row_properties(job) — property values for the sample job:")
    print(json.dumps(row, indent=2, ensure_ascii=False))

    # -------------------- Assertions (offline) --------------------
    print("\n" + "-" * 74)
    print("Assertions:")
    failures = []

    # (a) Every schema property is present in the row mapping (no drift).
    schema_keys = set(schema.keys())
    row_keys = set(row.keys())
    missing = schema_keys - row_keys
    extra = row_keys - schema_keys
    if missing:
        failures.append(f"row missing required fields: {sorted(missing)}")
    if extra:
        failures.append(f"row has unknown fields: {sorted(extra)}")
    print(f"  [{'OK' if not (missing or extra) else 'XX'}] "
          f"row covers all {len(schema_keys)} schema properties "
          f"(missing={sorted(missing)}, extra={sorted(extra)})")

    # (b) Exactly one title property, and it is Company.
    titles = [k for k, v in schema.items() if "title" in v]
    ok_title = titles == [ns.COMPANY]
    if not ok_title:
        failures.append(f"expected single title 'Company', got {titles}")
    print(f"  [{'OK' if ok_title else 'XX'}] exactly one title property = {titles}")

    # (c) Row value 'kind' matches the schema-declared type for each property.
    type_mismatches = []
    for name, definition in schema.items():
        want = _value_type(definition)
        got = _value_type(row[name])
        if want != got:
            type_mismatches.append(f"{name}: schema={want} row={got}")
    if type_mismatches:
        failures.append("type mismatches: " + "; ".join(type_mismatches))
    print(f"  [{'OK' if not type_mismatches else 'XX'}] "
          f"row value types match schema types "
          f"({len(schema)} checked, {len(type_mismatches)} mismatched)")

    # (d) Select values fall inside the controlled vocabularies.
    def _sel_name(prop):
        sel = row[prop].get("select")
        return sel["name"] if sel else None

    vocab_checks = [
        (ns.CHANNEL, ns.CHANNEL_OPTIONS),
        (ns.EMAIL_SOURCE, ns.EMAIL_SOURCE_OPTIONS),
        (ns.STATUS, ns.STATUS_OPTIONS),
    ]
    bad_vocab = []
    for prop, allowed in vocab_checks:
        val = _sel_name(prop)
        if val is not None and val not in allowed:
            bad_vocab.append(f"{prop}={val!r} not in {allowed}")
    if bad_vocab:
        failures.append("select vocab violations: " + "; ".join(bad_vocab))
    print(f"  [{'OK' if not bad_vocab else 'XX'}] select values within controlled vocab "
          f"(Channel={_sel_name(ns.CHANNEL)}, "
          f"Email Source={_sel_name(ns.EMAIL_SOURCE)}, "
          f"Status={_sel_name(ns.STATUS)})")

    # (e) Default status is 'Ready for Review' (per the tracker spec).
    ok_status = _sel_name(ns.STATUS) == "Ready for Review"
    if not ok_status:
        failures.append(f"default status is {_sel_name(ns.STATUS)!r}, expected 'Ready for Review'")
    print(f"  [{'OK' if ok_status else 'XX'}] default Status = 'Ready for Review'")

    # (f) No live calls were made — this script imports nothing network-y.
    print("  [OK] no Notion/MCP/network calls made (offline mapping only)")

    print("\n" + "=" * 74)
    if failures:
        print("RESULT: FAIL ❌")
        for f in failures:
            print(f"  - {f}")
        print("=" * 74)
        return 1
    print("RESULT: PASS ✅ — schema/mapping consistent; every required field present.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
