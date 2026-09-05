---
description: Run ONLY the company-research stage — company analysis + verified recruiter email (waterfall) + match score on found jobs. No sends.
disable-model-invocation: true
---

# /alfred-research — company-research only

Run just the research/enrichment stage on the jobs the finder already surfaced.

1. **Preflight** — run `${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python
   ${CLAUDE_PLUGIN_ROOT}/scripts/orchestrate.py --preflight` (fall back to `python3`). If it exits
   non-zero (missing config/resume, or **/pause** set), STOP and report.
2. **Invoke** the `alfred:company-research` subagent → for each fresh job: company analysis, a
   verified contact email via the Alfred waterfall, and a 0–100 match score. Drop jobs below
   `match_threshold`. Read/write the same intermediate state files as a full run.
3. Report how many were enriched and how many dropped below threshold.

**Guardrails:** research reads the web but sends nothing. Still honor **/pause** and keep **dry_run**
state intact; email discovery/verification must not send any message to the candidate address.
