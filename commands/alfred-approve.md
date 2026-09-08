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
4. Report how many cards were sent, how many taps were reconciled, and how many email preview cards
   went out. If `approval_poll.py --status` still lists anything under `pending_email_previews`,
   say so — that is an approved job whose email the user was never asked about.

**Guardrails:** the Telegram card is the approval channel itself (to the user, over the Bot API) — but
**no job is applied or sent to a recruiter here**; this stage only records decisions and enqueues.
Honor **/pause**. Approving does not itself apply — the application-agent (`/alfred-apply` or a full
run) still enforces **dry_run**, **/pause**, and daily caps before anything leaves.
