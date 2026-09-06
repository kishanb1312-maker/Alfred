# Alfred — Codex Runbook (all six stages, with prompts)

Everything needed to run Alfred on a host that is **not** Claude Code. Each stage has a
copy-paste prompt, what a pass looks like, and what to do when it fails.

There is no automatic chaining here — you run one stage per request. State passes between
stages through `data/`, so stopping after any stage is safe and resuming is just running
the next prompt.

> Keep `dry_run: true` in `config/search.yaml` until you have watched a full pass. Stage 6
> is the only stage that acts on the world.

---

## Setup (once)

```bash
cd ~/Documents/WarmApply && git pull
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
export ALFRED_HOME="$(pwd)"        # add to your shell profile if not already there
./.venv/bin/python scripts/alfred_cli.py doctor
for f in scripts/dry_run_*.py; do ./.venv/bin/python "$f"; done
```

Expect a green `doctor` and 15/15 dry runs. Blank Hunter/Notion credentials are
non-blocking — they degrade stages 2 and 4, they do not stop the pipeline.

---

## Stage 1 — Find jobs

**Prompt**

> Read `agents/job-finder.md` and run ONLY that stage.
>
> First tell me which browser capability you found and where it landed in the preference
> order (host browser → Playwright MCP → other browser MCP → skip).
>
> Then run the stage. For each source in `search_order`, report one line: how many jobs,
> and if zero, why. Apply `max_age_days`, `seniority`, and `locations` from
> `config/search.yaml` to every source, not just some. Write results to
> `data/finder_output.json` and a per-source report to `data/finder_report.json`.
>
> Use `./.venv/bin/python` for script calls. No sends, no other stages.

**Pass** — it names a concrete browser capability, or says it has none and skips the four
browser sources (`linkedin_easy_apply`, `linkedin_feed`, `indeed`, `wellfound`) with notes
while the API/RSS sources still return jobs. Both are correct outcomes.

**Fail** — browser-source results appear without any browser tool being named. That means
an HTTP fetch was substituted for a JS-rendered page, or the gap was filled from memory.
Discard the run and re-prompt.

**If it returns very few jobs:** check `max_age_days` (3 is tight) and `seniority` before
assuming a bug. Both filters were recently made to apply on every source.

---

## Stage 2 — Research + score

**Prompt**

> Read `agents/company-research.md` and run ONLY that stage against
> `data/finder_output.json`.
>
> For each job: research the company, find a recruiter/contact email via the Alfred
> waterfall (prefer-personal, generic fallback, verified), and compute a 0–100 match score
> against my resume. Drop anything below `match_threshold` in `config/search.yaml`.
>
> Report per job: company, score, kept or dropped, and the email you found with its
> confidence. Never invent an address — null is the correct answer when you cannot verify.
>
> Use `./.venv/bin/python` for script calls. No sends.

**Pass** — every kept job has a score and either a verified email or an explicit null.

**Note** — with `HUNTER_API_KEY` blank this falls back to a lower-confidence pattern guess.
That is expected, not a failure; it just means weaker outreach until you add a key.

---

## Stage 3 — Tailor resume + cover letter

**Prompt**

> Read `agents/resume-cover-letter.md` and run ONLY that stage for the jobs that survived
> stage 2.
>
> For each: tailor my master resume by editing ONLY the summary and bullet emphasis. Never
> invent experience, never change the format, never touch the projects section. Produce the
> tailored .docx, a PDF, a cover letter, a short outreach email, and a mandatory "what I
> changed" note listing every edit.
>
> Write to `output/<company>_<role>/`. Use `./.venv/bin/python` for script calls. No sends.

**Pass** — every job has all five artifacts and a what-changed note you can actually audit.

**Fail** — a resume claiming skills or dates the master resume does not contain. This is
Alfred's truthfulness core; a fabricated claim here reaches a real employer. Reject the
output and re-run rather than editing around it.

---

## Stage 4 — Track in Notion

**Prompt**

> Read `agents/tracker.md` and run ONLY that stage. Create or update one Notion row per
> job at status "Ready for Review", using `scripts/notion_schema.py` as the single source
> of truth for the schema and field mapping. Report what you wrote.

**Pass** — one row per job with all fields populated.

**Skip is fine** — without Notion MCP configured on this host, skip the stage and continue.
You lose the permanent archive, not the pipeline. Say so explicitly rather than faking it.

---

## Stage 5 — Approval gate (human in the loop)

**Prompt**

> Read `agents/approval-gate.md` and run ONLY that stage.
>
> For each job at "Ready for Review", send a Telegram card with the summary, match score,
> what-changed note, and the resume/cover-letter PDFs attached, with Approve/Skip buttons.
> Then poll for my decisions and record them. Enqueue approved jobs to
> `data/approved_queue.json`.
>
> Nothing is applied or emailed in this stage. Use `./.venv/bin/python` for script calls.

**Pass** — cards arrive in Telegram, your taps are recorded, approved jobs land in the
queue. Telegram is pure Python, so this works on any host with the bot token in `.env`.

**This is the safety gate.** Nothing downstream acts on a job you did not explicitly
Approve. Late taps are reconciled on the next run via a saved offset, so you can walk away
mid-review.

---

## Stage 6 — Apply  ⚠️ the only stage that acts on the world

**Prompt**

> Read `agents/application-agent.md` and run ONLY that stage against
> `data/approved_queue.json`.
>
> Confirm `dry_run` from `config/search.yaml` before doing anything and tell me its value.
> Respect `caps.applies_per_day` and `caps.emails_per_day`, and `pacing`.
>
> For each approved job do both channels: the portal application, and the cold email if an
> address was found. On ban-prone sites, fill the form but hand the final Submit click to
> me — do not click it yourself. Then mark the job Applied.
>
> Report exactly what you did or, in dry run, exactly what you would have done.

**Before your first live run:** verify it printed `dry_run: true` and that its report reads
as a simulation. Only then consider flipping the flag.

**Fail** — anything sent or submitted while `dry_run` is true. Stop immediately and check
the flag was actually read.

---

## Recovery and state

| File | Written by | Purpose |
|---|---|---|
| `data/finder_output.json` | Stage 1 | The job list |
| `data/finder_report.json` | Stage 1 | Per-source status and drop reasons |
| `data/approved_queue.json` | Stage 5 | Jobs you approved |
| `data/applied_history.json` | Stages 1 & 6 | De-dupe + applied record |
| `output/<company>_<role>/` | Stage 3 | Tailored artifacts |

Stages are resumable: re-running a stage reads the previous stage's file and rewrites its
own. To redo a stage, delete its output file and run its prompt again.

**Pause everything:** create `data/paused.flag`. Stages check it and stop.

**Check state any time:**

```bash
./.venv/bin/python scripts/orchestrate.py --preflight
```
