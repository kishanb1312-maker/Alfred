---
description: Run any career-ops mode by name inside Alfred (deep, contacto, ats, add, expand, intake, discover, training, project, gambit, master-profile, latex, text, batch…). Usage: /alfred:alfred-mode <mode> [args]
disable-model-invocation: true
---

# /alfred-mode — any career-ops mode

Run Alfred's scripts with `${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python` (fall back to `python3`); scripts live in
`${CLAUDE_PLUGIN_ROOT}/scripts/`. career-ops lives in `${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops`: run its `node` scripts from
there with `CAREER_OPS_ROOT=${ALFRED_HOME:-$HOME/.alfred}` exported, so it reads and writes Alfred's own files.
Before running a career-ops mode: read `${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops/AGENTS.md` (its Data Contract, Source-of-Truth
Boundary and Untrusted External Content rules bind you) and `${ALFRED_HOME:-$HOME/.alfred}/modes/_custom.md` (Alfred's house
rules: no cover letters, Aside is the only browser — never Playwright MCP). Then follow
`${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops/modes/<mode>.md` exactly.

`$ARGUMENTS` = `<mode> [args]`. With no mode, list career-ops's modes (from
`${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops/.agents/skills/career-ops/SKILL.md` → Mode Routing) and what each does.

Not available inside Alfred: `cover` (Alfred sends no cover letters) and `update` (career-ops is
pinned; change the pin in `scripts/careerops_bridge.py` and run `alfred careerops-install`).
`apply` is replaced by `/alfred:alfred-apply`.
