# Alfred — daily run

Health check first, pipeline second, then it waits for your review. Paste into Claude Code (or
schedule it with `/schedule`).

---

Run Alfred's daily cycle. I am away — **never ask me a question**; make the reasonable choice,
write what you assumed to `data/run_assumptions.md`, and continue.

**STEP 1 — Health check.**
- `./.venv/bin/python scripts/alfred_cli.py doctor` — stop on any ❌.
- Through **Aside** (run `aside guide` first), open LinkedIn `/jobs/search`, `in.indeed.com` and
  Wellfound `/jobs` and report each as LIVE / LOGGED-OUT / BLOCKED / UNREACHABLE. A logged-out or
  blocked site is skipped for this run, with a note; it never stops the zero-token sources.
- `data/paused.flag` present → run stages 1–5 but not apply.

**STEP 2 — Pipeline**, each stage as its own subagent, in order, each reading the previous output:

1. `job-finder` → `data/finder_output.json`
2. `job-verifier` → `data/verified_jobs.json` (closed and stale postings dropped)
3. `job-evaluator` → career-ops triage, then A–H reports + 1–5 scores, tracker rows
4. `contact-finder` → contact emails for jobs at or above `min_score`
5. `cv-tailor` → tailored CV PDFs + fact gate + email drafts → review list

Do **not** run the application agent on new jobs: I approve them myself. Jobs already in
`data/approved_queue.json` from earlier approvals may be applied (stage 7), respecting dry_run,
caps and pacing.

Rules: never fabricate a job, company, email or CV claim — zero with a reason beats a full-looking
lie. Respect `max_age_days`, `seniority`, `locations`, `min_score`, `caps`, `pacing`. Use
`./.venv/bin/python` for script calls; run career-ops scripts from `vendor/career-ops` with
`CAREER_OPS_ROOT` set to the Alfred home.

**Finish with one summary**: health per site, jobs per source, verified / dropped (why),
evaluated with scores, CVs passed / blocked by the fact gate, how many wait for my review
(`alfred review`), anything applied, every `needs_confirmation` line, caps left.

---

## When you are back

```bash
./.venv/bin/python scripts/alfred_cli.py review
./.venv/bin/python scripts/alfred_cli.py approve <job_id>          # portal only
./.venv/bin/python scripts/alfred_cli.py approve <job_id> --email  # portal + cold email
./.venv/bin/python scripts/alfred_cli.py skip <job_id>
```

Then `/alfred:alfred-apply`.
