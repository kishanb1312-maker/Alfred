---
description: Alfred health + summary — runs `alfred doctor` and the orchestrator run-summary, and reports dry_run / /pause state.
disable-model-invocation: true
---

# /alfred-status — doctor + summary

Report Alfred's readiness and last-run summary. Run the bundled scripts with
`${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python` (fall back to `python3`).

1. **Doctor** — run `${CLAUDE_PLUGIN_ROOT}/scripts/alfred_cli.py doctor` and show the checklist.
   Call out any ❌ items (they block a run) versus ⚠️ advisories (fine to defer).
2. **Summary** — run `${CLAUDE_PLUGIN_ROOT}/scripts/orchestrate.py --summary`, passing the latest run
   stats file if one exists; otherwise note that no run has been recorded yet.
3. Explicitly state whether **dry_run** is ON and whether **/pause** (`data/paused.flag`) is set.

This command only reads and reports — it never sends, submits, or invokes a worker subagent.
