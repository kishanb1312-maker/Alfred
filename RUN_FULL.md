# Alfred — first full unattended run

Runs stages 1–5 back to back with no questions asked, then stops. You come back to
Telegram cards waiting for Approve/Skip.

## Before you start

```bash
grep dry_run config/search.yaml        # want: dry_run: true for run #1
ls data/paused.flag 2>/dev/null        # want: no such file
```

Stage 6 (apply) is NOT part of this run. After you tap Approve on the cards, run it
separately with `/alfred:alfred-apply`.

## The prompt

Paste this into Claude Code:

---

Run Alfred stages 1 through 5 end to end, unattended. I am away and will not answer
anything, so **never stop to ask me a question** — make the reasonable choice, write down
what you assumed, and keep going.

Run each stage as its own subagent, in order, one at a time, each reading the previous
stage's output:

1. `job-finder` → `data/finder_output.json`
2. `company-research` → scores + recruiter emails
3. `resume-cover-letter` → tailored artifacts in `output/<company>_<role>/`
4. `tracker` → one Notion row per job at "Ready for Review"
5. `approval-gate` → send the Telegram cards, then **STOP**

Rules for the whole run:

- **Do not run stage 6 (application-agent).** Stop after the cards are sent. I will approve
  in Telegram and run the apply stage myself later.
- **A blocked stage must not halt the run.** If Notion is not authorized, skip stage 4 with
  a note and continue to stage 5 — the Telegram cards matter more than the archive. Same for
  any source or capability that is unavailable.
- **Never fabricate.** A job, company, email, or resume claim you could not actually verify
  is reported as null or zero with the reason. This is more important than a full-looking
  result.
- Confirm `dry_run` and `data/paused.flag` before stage 1 and tell me what they were.
- Respect `max_age_days`, `seniority`, `locations`, `match_threshold`, `caps`, and `pacing`
  from `config/search.yaml` on every source.
- Use `./.venv/bin/python` for all script calls.

When you stop, give me one summary: per-source job counts and why any were zero, how many
survived scoring, how many got tailored, whether Notion worked, how many Telegram cards went
out, and every assumption you made along the way.

---

## What you should come back to

- Telegram cards, one per job, each with the match score, what-changed note, resume and
  cover-letter PDFs attached, and Approve / Skip buttons.
- A summary in the Claude session naming anything that was skipped and why.

## Then, after you approve

```
/alfred:alfred-apply
```

Check `dry_run` first. With `dry_run: true` it reports what it *would* do — read that once
before turning the flag off.
