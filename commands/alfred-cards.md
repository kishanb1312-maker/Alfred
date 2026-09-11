---
description: Rehydrate every job from Notion and send its email preview card to Telegram, so a backlog of prepared jobs can be reviewed and sent one tap at a time. Sends no email.
disable-model-invocation: true
---

# /alfred-cards — put the email for every Notion job back on the phone

For the state this exists to fix: jobs are prepared and sitting in Notion, and Telegram is
empty. Either the cards were never sent, or the taps answering them were lost, or the jobs
never got an Approve in the first place. Either way the user wants to see each email and
decide, and no amount of re-polling Telegram will produce a card for a job that has none.

**This collapses the two gates into one for these jobs.** Normally a job earns its email
preview by being Approved first. Here every prepared job gets its preview directly. That is
a deliberate change in posture and worth saying out loud when you report — but it removes no
human decision: a preview card sends nothing, and the email still leaves only on a Send tap.

## Steps

1. **Preflight** — `${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python
   ${CLAUDE_PLUGIN_ROOT}/scripts/orchestrate.py --preflight` (fall back to `python3`).
   Stop and report if it exits non-zero.

2. **Export the Notion rows.** Query the tracker data source with
   `notion-query-data-sources` and write the **raw response** to
   `${ALFRED_HOME:-$HOME/.alfred}/data/notion_rows.json`. Do not reshape it — the staging
   step already understands `{"results": [...]}`, full page objects, and bare properties
   maps. Include every row the user means; filter by Status only if they asked you to.

3. **Stage and card them in one call:**
   ```
   ${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python \
     ${CLAUDE_PLUGIN_ROOT}/scripts/approval_poll.py \
     --stage ${ALFRED_HOME:-$HOME/.alfred}/data/notion_rows.json --preview-all
   ```
   It rebuilds each job from its row (recruiter address, tailored file paths), stages the
   email draft, and sends one **📧 READY TO SEND** card per job with Send / Edit / Cancel.
   One command rather than two on purpose: staging and carding separately leaves a window
   where the drafts exist and the phone is still empty, and that window is where this keeps
   getting stuck.

4. **Report the rows that could not be carded, by name and reason.** The `staged` list gives
   one entry per row; `staged: false` with `no recruiter address or no email_message.txt`
   means one of two honest failures:
   - **no recruiter address** — the job is portal-only. Nothing to email. Say so.
   - **no `email_message.txt`** — the tailored output is gone or was never written for that
     job. Re-run the tailor stage for it (`/alfred-tailor`) and then re-run this command.

   **Never invent an email body to fill the gap.** A fabricated cold email goes to a real
   company under the user's name. A missing draft is reported, not improvised.

5. **Apply `notion_updates`** with `notion-update-page`, then tell the user how many cards
   went out, how many rows were skipped and why, and that tapping **Send** is what actually
   emails a company.

## Guardrails

Sending these cards sends no email. Each one still needs a **Send** tap, and every send then
passes `email_gate`'s guardrails — `dry_run`, `/pause`, the bounce throttle, the daily cap,
and send-once. A job whose email is already decided (`cleared` or `cancelled`) is never
re-carded, so running this twice cannot re-ask a question the user has answered.
