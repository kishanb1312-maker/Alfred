---
description: Run ONLY the application-agent stage — process the approved queue. The ONLY stage that acts on the world; strictly honors dry_run, /pause, and daily caps.
disable-model-invocation: true
---

# /alfred-apply — application-agent only

Run just the apply stage against `data/approved_queue.json`. **This is the only stage that acts on the
world**, so the guardrails are hard gates, not reminders.

1. **Preflight gate — MANDATORY.** Run `${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python
   ${CLAUDE_PLUGIN_ROOT}/scripts/orchestrate.py --preflight` (fall back to `python3`).
   - **If it exits non-zero, or /pause (`data/paused.flag`) is set → STOP. Do NOT invoke the agent.**
     Running a stage manually must never bypass a pause.
   - Read the reported **dry_run** state and pass it through unchanged.
2. **Invoke** the `alfred:application-agent` subagent to process the approved queue. It must, on its
   own, still enforce every guardrail below — do not instruct it to skip any of them:
   - **dry_run: true** → prepare/serialize the email or form fill and return, **sending/submitting
     nothing**.
   - **/pause** → do not act. **email_paused.flag** (bounce auto-throttle) → skip the email channel;
     the portal channel may continue.
   - **daily caps** → never exceed the configured applies/emails per day; stop when a cap is reached.
   - On ban-prone portals (LinkedIn/Workday), fill the form but **hand the final Submit click to the
     human**.
3. On real (non-dry_run) sends, mark the job Applied in Notion + `applied_history`. Report applied,
   skipped, caps remaining, and anything left pending.

**Guardrails (never bypass):** dry_run blocks all real sends/submits · /pause halts this agent · daily
caps limit volume · the human makes the final Submit on ban-prone portals · nothing is applied without a
prior Telegram **Approve**.
