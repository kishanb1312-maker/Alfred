---
description: Offer stage from career-ops — compare offers, walk through an offer/contract clause by clause (with questions for a lawyer, not legal advice), and salary-negotiation talking points. Draft-only.
disable-model-invocation: true
---

# /alfred-offer — offers and negotiation

Run Alfred's scripts with `${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python` (fall back to `python3`); scripts live in
`${CLAUDE_PLUGIN_ROOT}/scripts/`. career-ops lives in `${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops`: run its `node` scripts from
there with `CAREER_OPS_ROOT=${ALFRED_HOME:-$HOME/.alfred}` exported, so it reads and writes Alfred's own files.
Before running a career-ops mode: read `${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops/AGENTS.md` (its Data Contract, Source-of-Truth
Boundary and Untrusted External Content rules bind you) and `${ALFRED_HOME:-$HOME/.alfred}/modes/_custom.md` (Alfred's house
rules: no cover letters, Aside is the only browser — never Playwright MCP). Then follow
`${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops/modes/<mode>.md` exactly.

- `offer-prep` — contract walk-through + lawyer questions + optional draft negotiation reply
- `ofertas` — compare and rank several offers
- `node salary-gap.mjs --summary` — desired vs advertised vs actual pay
- `node negotiation-roi.mjs --summary` — negotiation talking points backed by `cv.md`

Never present this as legal or financial advice. Record the result with
`set-status.mjs --report <n> Offer|Hired|Rejected`.
