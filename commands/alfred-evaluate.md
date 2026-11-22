---
description: Run ONLY evaluation — career-ops triage, then the full A–H report with a 1–5 score per verified job, saved to reports/ and the tracker; then find contact emails for jobs at or above min_score. Read-only on the world.
disable-model-invocation: true
---

# /alfred-evaluate — score the jobs (career-ops)

Run Alfred's scripts with `${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python` (fall back to `python3`); scripts live in
`${CLAUDE_PLUGIN_ROOT}/scripts/`. career-ops lives in `${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops`: run its `node` scripts from
there with `CAREER_OPS_ROOT=${ALFRED_HOME:-$HOME/.alfred}` exported, so it reads and writes Alfred's own files.

1. Needs `data/verified_jobs.json` (run `/alfred:alfred-verify` first). A pasted job URL or JD
   works too: evaluate just that one.
2. Invoke `alfred:job-evaluator` → `reports/*.md`, tracker rows (`Evaluated`),
   `data/evaluation_output.json`.
3. Invoke `alfred:contact-finder` for jobs at or above `min_score`.
4. Report a table: score, recommendation, legitimacy, company, role, report link. Jobs below 4.0
   are listed as "not recommended".
