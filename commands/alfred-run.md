---
description: Run the full Alfred pipeline (find → verify → evaluate → contacts → CV → review list → apply approved → report), preflight-gated. Honors dry_run, /pause and daily caps.
disable-model-invocation: true
---

# /alfred-run — the whole pipeline

Execute `RUNBOOK.md` end to end, invoking each subagent in order and **stopping on any blocker**.
Run Alfred's scripts with `${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python` (fall back to `python3`); scripts live in
`${CLAUDE_PLUGIN_ROOT}/scripts/`. career-ops lives in `${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops`: run its `node` scripts from
there with `CAREER_OPS_ROOT=${ALFRED_HOME:-$HOME/.alfred}` exported, so it reads and writes Alfred's own files.

## 0. Preflight — MANDATORY, first
`orchestrate.py --preflight`. Non-zero exit (missing `config/search.yaml`, `config/profile.yaml`,
`cv.md`, or **/pause** set) → STOP and report. Then `careerops_bridge.py status`: no career-ops
install → tell the user to run `/alfred:alfred-setup` and STOP. Carry the **dry_run** state into
every stage.

## The sequence
1. **Apply what you already approved** — if `data/approved_queue.json` has jobs from earlier runs,
   invoke `alfred:application-agent` first.
2. **Find** — `alfred:job-finder`: Alfred's API/RSS boards + `careerops_scan` (both zero-token),
   then LinkedIn / Indeed / Wellfound through Aside.
3. **Verify** — `alfred:job-verifier`: confirm at the employer, liveness, reposts. Closed and stale
   postings are dropped here, before any tokens are spent on them.
4. **Evaluate** — `alfred:job-evaluator`: career-ops triage, then the full A–H report + 1–5 score
   for jobs that pass, saved to `reports/` and the tracker.
5. **Contacts** — `alfred:contact-finder` for jobs at or above `min_score` (default 4.0).
6. **CV** — `alfred:cv-tailor`: tailored CV PDF + fact gate + short email draft → review list.
7. **Review** — show the review list (`alfred_cli.py review`) and stop for the user's decisions.
   Nothing new is applied in this run unless the user approves jobs now
   (`/alfred:alfred-approve`), in which case run step 8.
8. **Apply** — `alfred:application-agent` on `data/approved_queue.json`, respecting /pause,
   dry_run and caps.
9. **Report** — `orchestrate.py --summary` with the run stats: counts, caps left, what needs the
   user, and every `needs_confirmation` line.

## Guardrails (never bypass)
- **dry_run: true** → prepare everything, submit and send **nothing**.
- **/pause** → the application agent does not act.
- **Daily caps** → never exceeded.
- Nothing is applied without the user's explicit approve; no email without its own clear.
