---
description: Alfred health + summary — runs `alfred doctor` (incl. career-ops and Aside checks), the tracker funnel, the review list size, and reports dry_run / /pause state.
disable-model-invocation: true
---

# /alfred-status — doctor + summary

Run Alfred's scripts with `${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python` (fall back to `python3`); scripts live in
`${CLAUDE_PLUGIN_ROOT}/scripts/`. career-ops lives in `${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops`: run its `node` scripts from
there with `CAREER_OPS_ROOT=${ALFRED_HOME:-$HOME/.alfred}` exported, so it reads and writes Alfred's own files.

1. **Doctor** — `alfred_cli.py doctor`; call out ❌ (blocking) vs ⚠️ (advisory).
2. **Tracker** — `node stats.mjs --summary` in `${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops` (skip if career-ops is not installed).
3. **Waiting for you** — `alfred_cli.py review` (count) and `alfred_cli.py queue` (approved, not
   yet applied).
4. State whether **dry_run** is ON, `apply.auto_submit` is on, and whether **/pause** is set.

Read-only: never sends, submits or invokes a worker subagent.
