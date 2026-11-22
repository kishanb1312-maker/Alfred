---
description: After you apply — who is due a follow-up (with drafts), classify employer replies into tracker updates, and record outcomes. career-ops followup, reply-watch and outcome modes. Draft-only; nothing is sent without your yes.
disable-model-invocation: true
---

# /alfred-followup — after you apply

Run Alfred's scripts with `${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python` (fall back to `python3`); scripts live in
`${CLAUDE_PLUGIN_ROOT}/scripts/`. career-ops lives in `${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops`: run its `node` scripts from
there with `CAREER_OPS_ROOT=${ALFRED_HOME:-$HOME/.alfred}` exported, so it reads and writes Alfred's own files.
Before running a career-ops mode: read `${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops/AGENTS.md` (its Data Contract, Source-of-Truth
Boundary and Untrusted External Content rules bind you) and `${ALFRED_HOME:-$HOME/.alfred}/modes/_custom.md` (Alfred's house
rules: no cover letters, Aside is the only browser — never Playwright MCP). Then follow
`${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops/modes/<mode>.md` exactly.

Pick the mode from what the user asks (default: `followup`):
- **followup** — `node followup-cadence.mjs --summary`, then drafts for overdue ones.
- **reply-watch** — the user pastes a reply (or `node paste-reply.mjs`); classify it and suggest the
  tracker update; apply it with `set-status.mjs` only after they agree.
- **outcome** — `node outcome.mjs <selector> <type>` to record the result and archive the files.

A follow-up email the user approves goes out through Alfred's Gmail path: stage it with
`review_store.py` (`save_draft`), then `email-send <job_id>` and `/alfred:alfred-apply`.
