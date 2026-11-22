---
description: Show and maintain the career-ops tracker (data/applications.md) — status overview, update a status, health check, dedup. Replaces Notion.
disable-model-invocation: true
---

# /alfred-tracker — where every application stands

Run Alfred's scripts with `${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python` (fall back to `python3`); scripts live in
`${CLAUDE_PLUGIN_ROOT}/scripts/`. career-ops lives in `${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops`: run its `node` scripts from
there with `CAREER_OPS_ROOT=${ALFRED_HOME:-$HOME/.alfred}` exported, so it reads and writes Alfred's own files.
Before running a career-ops mode: read `${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops/AGENTS.md` (its Data Contract, Source-of-Truth
Boundary and Untrusted External Content rules bind you) and `${ALFRED_HOME:-$HOME/.alfred}/modes/_custom.md` (Alfred's house
rules: no cover letters, Aside is the only browser — never Playwright MCP). Then follow
`${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops/modes/<mode>.md` exactly. Mode: `tracker`.

- Overview: follow `modes/tracker.md`, or `node stats.mjs --summary` for the funnel.
- Update a status: `node set-status.mjs --report <report#> <State> [--note "…"]` with a canonical
  state (Evaluated, Applied, Responded, Assessment, Interview, Offer, Hired, Rejected, Discarded,
  SKIP). Never hand-edit the table.
- Health: `node verify-pipeline.mjs`; dedup: `node dedup-tracker.mjs`; statuses:
  `node normalize-statuses.mjs`.
- Terminal dashboard (optional): `npm run serve:dashboard` in `${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops`.
