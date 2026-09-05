---
description: Run ONLY the approval-gate stage — send Telegram review cards and reconcile Approve/Skip taps. Enqueues approved jobs; nothing is applied here.
disable-model-invocation: true
---

# /alfred-approve — approval-gate only

Run just the human-in-the-loop approval stage.

1. **Preflight** — run `${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python
   ${CLAUDE_PLUGIN_ROOT}/scripts/orchestrate.py --preflight` (fall back to `python3`). If it exits
   non-zero (missing config/resume, or **/pause** set), STOP and report.
2. **Invoke** the `alfred:approval-gate` subagent → for each job at "Ready for Review": send a
   Telegram card (summary + match score + what-changed + attached resume/cover-letter PDFs) with
   Approve/Skip, record the decision to Notion, and enqueue approved jobs to `data/approved_queue.json`.
   It also reconciles late taps from a previous run via the saved offset. Uses the same state files as a
   full run.
3. Report how many cards were sent and how many taps were reconciled.

**Guardrails:** the Telegram card is the approval channel itself (to the user, over the Bot API) — but
**no job is applied or sent to a recruiter here**; this stage only records decisions and enqueues.
Honor **/pause**. Approving does not itself apply — the application-agent (`/alfred-apply` or a full
run) still enforces **dry_run**, **/pause**, and daily caps before anything leaves.
