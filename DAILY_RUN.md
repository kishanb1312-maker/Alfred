# Alfred — daily 6PM run

Health-gate first, full pipeline second. If LinkedIn is logged out, nothing runs and you
get told why.

## The prompt

Paste this into Claude Code (or schedule it):

---

Run Alfred's daily cycle. I am away — **never ask me a question**; assume, log it, continue.

**STEP 1 — Health gate.** Open each site in the browser and report LIVE / LOGGED-OUT / BLOCKED /
UNREACHABLE: LinkedIn (`/jobs/search`), Indeed (`in.indeed.com`), Wellfound (`/jobs`). Then confirm
Telegram and Notion respond, and that `data/paused.flag` is absent.

**LinkedIn is a hard gate.** If it is logged out, blocked, or shows a login wall: send me a Telegram
message saying LinkedIn needs a re-login and **STOP THE ENTIRE RUN**. Do not run any stage. Do not
substitute an HTTP fetch. A silent failure at 6PM is the one outcome I cannot accept — I must always
get a Telegram message, whether the run proceeded or aborted.

Indeed or Wellfound being down is NOT a hard gate: note it, skip that source, continue.

**STEP 2 — Full pipeline**, only if the gate passed. Run each as its own subagent, in order:

1. `job-finder` → `data/finder_output.json`
2. `company-research` → scores + recruiter emails
3. `resume-cover-letter` → tailored artifacts
4. `tracker` → Notion rows at "Ready for Review"
5. `approval-gate` → first `scripts/approval_poll.py` to reconcile yesterday's taps (an Approve
   there must produce its **email preview card** — Send / Edit / Cancel — not just a Notion
   status change), then a Telegram card per new job, then **STOP**

Rules: do **not** run stage 6 (application-agent) — I approve in Telegram myself. A blocked
non-LinkedIn stage is skipped with a note, never fatal. Never fabricate a job, company, email, or
resume claim — zero with a reason beats a full-looking lie. Respect `max_age_days`, `seniority`,
`locations`, `match_threshold`, `caps`, `pacing`. Use `./.venv/bin/python` for script calls.

**Finish by sending me ONE Telegram summary**: gate result per site, jobs per source, how many
scored / tailored / tracked, cards sent, email preview cards sent, and anything skipped. If
`approval_poll.py --status` reports anything under `pending_email_previews`, name those jobs —
they are approved jobs whose email I was never asked about.

---

## Before scheduling

```bash
grep dry_run config/search.yaml     # true until you've watched a full pass
ls data/paused.flag 2>/dev/null     # should not exist
```

## What has to be true at 6PM

- The Mac is **awake** and Claude Code can run — a sleeping machine runs nothing.
- The browser still carries your **signed-in LinkedIn session**. This is what the gate exists to
  catch; LinkedIn expires sessions on its own schedule, not yours.
- Telegram bot token in `.env` — it is the only way an aborted run can reach you.

## Reading the result

| Telegram message | Meaning |
|---|---|
| ⚠️ LinkedIn needs re-login | Nothing ran. Log in, then re-run the prompt manually. |
| Summary + review cards | Normal run. Approve/Skip at your leisure. |
| Approve tapped, then an email preview card | Expected. The preview arrives on the next poll — immediately if the run is still going, otherwise on the next run's reconcile. |
| Summary, 0 jobs | Ran fine, found nothing new — `max_age_days: 3` is tight. |
| **Nothing at all** | The run never started (Mac asleep, Claude Code not running). Check the schedule. |

That last row is why the summary is mandatory: silence means the scheduler failed, not that
Alfred found nothing.
