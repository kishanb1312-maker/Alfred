---
description: Learn from results with career-ops — rejection patterns, whether scores predict outcomes (calibrate), skill gaps across your pipeline (upskill), and adjacent job titles to widen the search.
disable-model-invocation: true
---

# /alfred-learn — what the results say

Run Alfred's scripts with `${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python` (fall back to `python3`); scripts live in
`${CLAUDE_PLUGIN_ROOT}/scripts/`. career-ops lives in `${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops`: run its `node` scripts from
there with `CAREER_OPS_ROOT=${ALFRED_HOME:-$HOME/.alfred}` exported, so it reads and writes Alfred's own files.
Before running a career-ops mode: read `${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops/AGENTS.md` (its Data Contract, Source-of-Truth
Boundary and Untrusted External Content rules bind you) and `${ALFRED_HOME:-$HOME/.alfred}/modes/_custom.md` (Alfred's house
rules: no cover letters, Aside is the only browser — never Playwright MCP). Then follow
`${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops/modes/<mode>.md` exactly.

- `patterns` — `node analyze-patterns.mjs --summary`, then the mode's advice
- `calibrate` — are 4+/5 scores turning into interviews? Advisory; never changes scoring
- `upskill` — `node upskill.mjs` skill-gap map from your reports
- `titles` — adjacent titles from `cv.md`; offer to add them to `config/search.yaml` roles and
  `portals.yml` title_filter (write only after the user agrees)
- `retro` — keep a correction as a rule (writes only what the user accepts)
