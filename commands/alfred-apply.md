---
description: Run ONLY the application agent on approved jobs — portal applications through Aside (LinkedIn Easy Apply + every career-ops ATS), submitted automatically when apply.auto_submit is on, and cleared cold emails via Gmail. Honors /pause, dry_run, daily caps.
disable-model-invocation: true
---

# /alfred-apply — apply to approved jobs

Run Alfred's scripts with `${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python` (fall back to `python3`); scripts live in
`${CLAUDE_PLUGIN_ROOT}/scripts/`. career-ops lives in `${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops`: run its `node` scripts from
there with `CAREER_OPS_ROOT=${ALFRED_HOME:-$HOME/.alfred}` exported, so it reads and writes Alfred's own files.

1. **Preflight** — `orchestrate.py --preflight`; non-zero (or /pause) → STOP.
2. `alfred_cli.py queue` — nothing approved → say so and stop.
3. Say what will happen before starting: how many jobs, `dry_run` on/off, `apply.auto_submit`
   on/off, caps left today.
4. Invoke `alfred:application-agent`.
5. Report per job: submitted (with confirmation) / filled, waiting for you (what is left + URL) /
   blocked (captcha, login) / failed; emails sent or refused and why.
