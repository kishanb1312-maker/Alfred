---
description: Run the full Alfred pipeline (reconcile → find → research → tailor → track → approve → apply → report), preflight-gated. Honors dry_run, /pause, and daily caps.
disable-model-invocation: true
---

# /alfred-run — the whole pipeline

Execute the Alfred runbook end to end. **This changes no agent behavior** — it is the exact
sequence in `RUNBOOK.md`, only gated by a preflight check. Invoke each subagent in order and
**stop on any blocker**.

Run the bundled scripts with the Alfred Python env — `${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python`
(fall back to `python3` if that venv is absent). Scripts live under `${CLAUDE_PLUGIN_ROOT}/scripts/`.

## 0. Preflight gate — MANDATORY, do this first
Run `${CLAUDE_PLUGIN_ROOT}/scripts/orchestrate.py --preflight`.
- **Non-zero exit** (missing `config/search.yaml`, `config/profile.yaml`, master resume in `data/`, or
  **/pause** is set) → STOP and report the issues. Do not run any stage.
- Record the reported **dry_run** state and carry it into every stage below.

## The sequence
1. **Reconcile** — invoke the `alfred:approval-gate` subagent to poll Telegram for taps made since
   the last run: apply Approvals (hand to `alfred:application-agent`), record Skips. Clears the backlog first.
2. **Find** — invoke `alfred:job-finder` → fresh, de-duped jobs (respects the configured sources).
3. **Research** — invoke `alfred:company-research` per job → company analysis + verified email
   (waterfall) + match score. Drop jobs below `match_threshold`.
4. **Tailor** — invoke `alfred:resume-cover-letter` per surviving job → tailored `.docx`/`.pdf`,
   cover letter, outreach email, and the mandatory `what_i_changed.md`. Merge into the canonical job
   object (see `RUNBOOK.md`).
5. **Track** — invoke `alfred:tracker` → create/update a Notion row per job at Status "Ready for Review".
6. **Approve** — invoke `alfred:approval-gate` → send a Telegram card per job; poll briefly for
   immediate taps. Un-tapped jobs wait for a later run.
7. **Apply** — invoke `alfred:application-agent` → process `data/approved_queue.json`, **respecting
   /pause, dry_run, and daily caps**: send verified emails; fill portal forms and hand the final Submit
   to the human on LinkedIn/Workday. Mark Applied in Notion + `applied_history`.
8. **Report** — run `${CLAUDE_PLUGIN_ROOT}/scripts/orchestrate.py --summary` with the run stats and
   report counts, caps remaining, and what needs the user.

## Guardrails (never bypass)
- **dry_run: true** → prepare everything, send/submit **nothing**.
- **/pause** (`data/paused.flag`) → the application-agent must not act; abort the Apply stage.
- **daily caps** → never exceed the configured applies/emails per day.
- A Telegram **Approve** is required before any send; the **human** makes the final Submit click on
  ban-prone portals. Nothing acts without an explicit Approve.
