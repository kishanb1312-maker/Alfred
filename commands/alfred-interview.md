---
description: Interview help from career-ops — company-specific prep, a time-blocked plan, practice questions with feedback, a post-interview debrief, and an employer red-flag check.
disable-model-invocation: true
---

# /alfred-interview — interview prep and practice

Run Alfred's scripts with `${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python` (fall back to `python3`); scripts live in
`${CLAUDE_PLUGIN_ROOT}/scripts/`. career-ops lives in `${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops`: run its `node` scripts from
there with `CAREER_OPS_ROOT=${ALFRED_HOME:-$HOME/.alfred}` exported, so it reads and writes Alfred's own files.
Before running a career-ops mode: read `${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops/AGENTS.md` (its Data Contract, Source-of-Truth
Boundary and Untrusted External Content rules bind you) and `${ALFRED_HOME:-$HOME/.alfred}/modes/_custom.md` (Alfred's house
rules: no cover letters, Aside is the only browser — never Playwright MCP). Then follow
`${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops/modes/<mode>.md` exactly.

Pick the mode from what the user asks:
- `interview-prep` — company-specific prep doc (in `interview-prep/`)
- `interview/plan` — time-blocked plan up to the interview date
- `interview/practice` — one question at a time, with feedback
- `interview/debrief` — after a real round: gaps and the next round
- `interview-redflag` — is this employer safe to join?

When the user moves to interviews, update the tracker: `set-status.mjs --report <n> Interview`.
