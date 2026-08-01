---
description: WarmApply health + summary — runs `warmapply doctor` and the orchestrator run-summary, and reports dry_run / /pause state.
disable-model-invocation: true
---

# /warmapply-status — doctor + summary

Report WarmApply's readiness and last-run summary. Run the bundled scripts with
`${WARMAPPLY_HOME:-$HOME/.warmapply}/.venv/bin/python` (fall back to `python3`).

1. **Doctor** — run `${CLAUDE_PLUGIN_ROOT}/scripts/warmapply_cli.py doctor` and show the checklist.
   Call out any ❌ items (they block a run) versus ⚠️ advisories (fine to defer).
2. **Summary** — run `${CLAUDE_PLUGIN_ROOT}/scripts/orchestrate.py --summary`, passing the latest run
   stats file if one exists; otherwise note that no run has been recorded yet.
3. Explicitly state whether **dry_run** is ON and whether **/pause** (`data/paused.flag`) is set.

This command only reads and reports — it never sends, submits, or invokes a worker subagent.
