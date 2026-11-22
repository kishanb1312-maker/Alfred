---
description: The manual approval step — show the jobs waiting for review (score, report, CV, fact check, email draft) and record your Approve / Skip, and separately whether each cold email may be sent.
disable-model-invocation: true
---

# /alfred-approve — you decide

Run Alfred's scripts with `${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python` (fall back to `python3`); scripts live in
`${CLAUDE_PLUGIN_ROOT}/scripts/`. career-ops lives in `${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops`: run its `node` scripts from
there with `CAREER_OPS_ROOT=${ALFRED_HOME:-$HOME/.alfred}` exported, so it reads and writes Alfred's own files.

1. Run `alfred_cli.py review` and show the list (best score first) as a table: score,
   recommendation, company, role, location, flags (repost, fact-check warnings, email guessed),
   report path, CV path.
2. For any job the user asks about, run `review_store.py show <job_id>` and summarize the report's
   Verdict and Risk Summary and the email draft.
3. Record **only what the user says**, job by job, in their own words:
   - approve → `alfred_cli.py approve <job_id>`
   - approve and send the email → `alfred_cli.py approve <job_id> --email`
   - skip → `alfred_cli.py skip <job_id>`
   - edit the email → write their text to a temp file, `review_store.py edit-email <job_id> <file>`
   - clear / cancel an email later → `review_store.py email-send <job_id>` / `email-cancel <job_id>`
   Never approve a job the user did not name. "Approve all" covers exactly the jobs shown in this
   list; repeat them back before recording.
4. Offer to run `/alfred:alfred-apply` for the approved ones.

The same commands work in a terminal without Claude: `alfred review`, `alfred approve <id>`.
