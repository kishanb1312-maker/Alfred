---
description: Run ONLY the job-finder stage — find + de-dupe fresh IT jobs from the configured sources. No sends.
disable-model-invocation: true
---

# /alfred-find — job-finder only

Run just the discovery stage. Keep it thin: this command only invokes the subagent; all logic stays
in the agent definition.

1. **Preflight** — run `${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python
   ${CLAUDE_PLUGIN_ROOT}/scripts/orchestrate.py --preflight` (fall back to `python3`). If it exits
   non-zero (missing config/resume, or **/pause** set), STOP and report.
2. **Invoke** the `alfred:job-finder` subagent → a normalized, de-duped list of fresh jobs, read
   from and written to the same intermediate state files the full run uses (so this is interchangeable
   with a full `/alfred-run`).
3. Report the count found and dropped.

**Guardrails:** finding never sends or submits, but still honors the run guardrails — respect
**/pause**, keep **dry_run** state intact, and do not bypass daily caps by pre-fetching more than a
day's work. Nothing here contacts a recruiter or portal.
