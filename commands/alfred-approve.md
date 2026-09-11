---
description: Run ONLY the approval-gate stage — send Telegram review cards and reconcile Approve/Skip taps. Enqueues approved jobs; nothing is applied here.
disable-model-invocation: true
---

# /alfred-approve — approval-gate only

Run just the human-in-the-loop approval stage.

1. **Preflight** — run `${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python
   ${CLAUDE_PLUGIN_ROOT}/scripts/orchestrate.py --preflight` (fall back to `python3`). If it exits
   non-zero (missing config/resume, or **/pause** set), STOP and report.
2. **Reconcile taps first** — run `${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python
   ${CLAUDE_PLUGIN_ROOT}/scripts/approval_poll.py --timeout 30`. It polls from the saved offset and
   acts on every tap in one pass: **Approve** → enqueue + **send the email preview card**
   (Send / Edit / Cancel), **Skip** → record, **Send/Cancel** → record the email decision,
   **Edit** → prompt, capture the reply, re-preview. It then sweeps any approved job still missing
   its preview card, and prints a JSON summary.
3. **Invoke** the `alfred:approval-gate` subagent → for each job at "Ready for Review": send a
   Telegram card (summary + match score + what-changed + attached resume/cover-letter PDFs) with
   Approve/Skip, apply the summary's `approved`/`skipped` lists to Notion, and confirm approved jobs
   are in `data/approved_queue.json`. Sending a card also stages that job's email draft, so a tap
   arriving days later can still be answered. Uses the same state files as a full run.
4. **Apply `notion_updates`** — the summary's `notion_updates` list is `{job_id, status, reason}`
   for **every** locally decided job, not just the taps this poll read. Push each one with
   `notion-update-page`. No Alfred script can write Notion, so a run that skips this step leaves
   rows reading "Ready for Review" for jobs the user already answered — the exact complaint this
   stage exists to prevent.
5. Report how many cards were sent, how many taps were reconciled, how many email preview cards
   went out, and how many Notion rows you moved. If `approval_poll.py --status` still lists anything
   under `pending_email_previews`, say so — that is an approved job whose email the user was never
   asked about. If it lists anything under `approved_without_draft`, say that too: those are
   portal-only jobs with no email to preview, and the user gets a notice saying so.

## If the user says an Approve tap did nothing

`approval_poll.py --status` names the fault. Not under `approved` → the tap was never polled (run
it). Under `approved_without_draft` → no recruiter email was ever staged, so there is no second card
to send. Under `awaiting_email_answer` but not `pending_email_previews` → Alfred thinks it delivered
the card and the user disagrees: `approval_poll.py --resend` puts it back on their phone, which
decides nothing and is always safe. Row still wrong in Notion → apply `--notion-plan`.

**Guardrails:** the Telegram card is the approval channel itself (to the user, over the Bot API) — but
**no job is applied or sent to a recruiter here**; this stage only records decisions and enqueues.
Honor **/pause**. Approving does not itself apply — the application-agent (`/alfred-apply` or a full
run) still enforces **dry_run**, **/pause**, and daily caps before anything leaves.
