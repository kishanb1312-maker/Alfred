---
description: Run ONLY the tracker stage — create/update the Notion row for each job at "Ready for Review".
disable-model-invocation: true
---

# /warmapply-track — tracker only

Run just the Notion tracking stage.

1. **Preflight** — run `${WARMAPPLY_HOME:-$HOME/.warmapply}/.venv/bin/python
   ${CLAUDE_PLUGIN_ROOT}/scripts/orchestrate.py --preflight` (fall back to `python3`). If it exits
   non-zero (missing config/resume, or **/pause** set), STOP and report.
2. **Invoke** the `warmapply:tracker` subagent → find-or-create the tracking database (first run), then
   create/update a row per job with all fields at Status **"Ready for Review"**, using
   `scripts/notion_schema.py` as the single source of truth. Reads/writes the same state as a full run.
3. Report rows created vs updated and the database URL.

**Guardrails:** the tracker writes to **Notion via the MCP connector** (authorized in Claude Code, not
via `.env`) — it is the permanent archive, not an application action, so it runs regardless of dry_run.
Still honor **/pause**: if paused, you may still record rows, but do not let this trigger any downstream
send. It never emails, submits, or contacts a recruiter.
