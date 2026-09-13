---
description: Write every prepared job's email into your Gmail Drafts folder (resume attached, cover letter omitted), so you can review, edit and send each one by hand. Sends nothing.
disable-model-invocation: true
---

# /alfred-drafts — put the emails in Gmail, not on the phone

For when the user would rather work in Gmail than tap Telegram cards: same tailored
emails, same recipients, but each one lands in **Gmail Drafts** with the resume attached.
Nothing is sent. The user opens Gmail, reads each draft, edits freely, and presses Send
(or Gmail's own Schedule-send) themselves.

Uses `GMAIL_ADDRESS` + `GMAIL_APP_PASSWORD` — the credentials already in `.env` for SMTP.
No new secret, no OAuth. **Gmail IMAP must be on** (Gmail → Settings → Forwarding and
POP/IMAP → Enable IMAP); if it is off, drafting fails with a login error and the result
says so.

## Steps

1. **Preflight** — `${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python
   ${CLAUDE_PLUGIN_ROOT}/scripts/orchestrate.py --preflight` (fall back to `python3`).

2. **Export the Notion rows** with `notion-query-data-sources` to
   `${ALFRED_HOME:-$HOME/.alfred}/data/notion_rows.json` — the raw response, unreshaped.

3. **Stage and draft in one call:**
   ```
   ${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python \
     ${CLAUDE_PLUGIN_ROOT}/scripts/approval_poll.py \
     --stage ${ALFRED_HOME:-$HOME/.alfred}/data/notion_rows.json --draft
   ```

4. **Report per job**: drafted, skipped, or failed. Three results need calling out by name:
   - `warning: no Resume_*.pdf found` — the draft exists but carries **no attachment**.
     Say which companies, so the user attaches the resume in Gmail before sending.
   - `reason: no staged email draft` — no recruiter address, or the tailored
     `email_message.txt` is missing. Portal-only, or re-run `/alfred-tailor` for it.
   - `status: FAILED` — usually IMAP disabled or an app password Google has rotated.
     Give the real error text.

5. Remind the user that **nothing has been sent**, and that Gmail's own Schedule-send
   (the arrow beside Send) is how a draft goes out at a set time — the Gmail API has no
   scheduling, so Alfred cannot do it for them.

## What this deliberately does

- **Resume only, no cover letter.** A draft that quietly carries a second PDF is one the
  user has to notice and remove. If they want the cover letter too, that is a change to
  `draft_to_gmail`, not a flag to guess at.
- **Not gated by `dry_run`.** A draft reaches no company; gating it would make the feature
  useless for the users who correctly keep `dry_run` on. The **send** path is untouched and
  keeps every guardrail.
- **Honours `/pause`.** Filling a Drafts folder while the user thinks Alfred is stopped is
  exactly the surprise the flag prevents.
- **Idempotent.** A job already recorded as drafted is skipped, so re-running does not
  leave the user two copies of nineteen emails. `--redraft` overrides, on purpose.

Never invent an email body for a job whose tailored text is missing. A fabricated cold
email goes to a real company under the user's name.
