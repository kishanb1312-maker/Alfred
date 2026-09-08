---
description: Recover jobs already prepared in Notion — stage their emails and send the Send/Edit/Cancel card — so a prepared backlog can go out without re-running the pipeline.
disable-model-invocation: true
---

# /alfred-backfill — email the jobs you already have

Use this when Notion holds jobs that were tailored and reviewed, but whose email never got
asked about — anything prepared before the two-gate fix, or approved while nothing was
polling. It does **not** find, research, or tailor anything: it recovers what already exists.

Notion is the only durable record of a job's recruiter address and tailored file paths (the
enriched job object lived in the agent turn that built it). So the recovery reads Notion.

1. **Preflight** — `${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python
   ${CLAUDE_PLUGIN_ROOT}/scripts/orchestrate.py --preflight`. Non-zero (missing config/resume,
   or **/pause**) → STOP and report.

2. **Query Notion** for rows whose Status is **"Approved"** or **"Ready for Review"**, using
   `notion-query-data-sources`. Write the raw response to
   `${ALFRED_HOME:-$HOME/.alfred}/data/backfill_rows.json`. Do not hand-map the properties —
   `scripts/notion_schema.py :: job_from_row` is the single source of truth for that mapping
   and `--stage` applies it for you.

3. **Stage them** — `python ${CLAUDE_PLUGIN_ROOT}/scripts/approval_poll.py --stage
   "${ALFRED_HOME:-$HOME/.alfred}/data/backfill_rows.json"`. For each row this recovers the
   recruiter address and the tailored PDFs into a staged draft, and — for a row already at
   **Approved** — records that approval locally, which is what makes it qualify for its email
   preview card. Rows with no recruiter address stage nothing (portal-only, correctly). Rows
   at Skipped are never resurrected. Re-running is safe: it never overwrites a draft the user
   has edited, and never sends a duplicate card.

4. **Send the cards** — `python ${CLAUDE_PLUGIN_ROOT}/scripts/approval_poll.py --sweep`.
   Every approved job with a staged draft gets its **[📧 Send] [✏️ Edit] [🚫 Cancel]** card.

5. **Report**, honestly and per job: how many rows were read, how many staged, how many cards
   went out, and — separately — the ones that staged **nothing** and why. A job whose
   `email_message.txt` is missing cannot be emailed until it is re-tailored; say so rather
   than letting the user believe a card is coming.

# What this does NOT do

- **It sends no email.** It sends the preview cards. Nothing reaches a company until the user
  taps 📧 Send, and then only through `email_gate.perform_send` with every guardrail —
  `dry_run`, `/pause`, the bounce throttle, `caps.emails_per_day`, send-once.
- **It does not re-tailor.** A job whose `output/<company>_<role>/` is gone needs a real run.
- **It does not apply on portals.** That is the application agent, and it needs the browser.

# Guardrails

- **The daily email cap still applies.** A backlog of thirty jobs does not become thirty
  emails today; `caps.emails_per_day` meters them and the rest go tomorrow. Do not raise the
  cap to drain a backlog faster — it exists to protect the sending Gmail from looking like a
  bulk sender, and the bounce throttle behind it assumes a human-scale rate.
- **Never fabricate a recruiter address** to make a job emailable. No address in Notion means
  portal-only. That is a correct outcome, not a gap to fill.
- **Idempotent.** Safe to re-run; a job already sent, cancelled, or previewed is left alone.
