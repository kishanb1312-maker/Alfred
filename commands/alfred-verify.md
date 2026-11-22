---
description: Run ONLY the job-verifier — is each found job still open and real? Confirms at the employer, checks liveness, flags reposts (career-ops). Read-only.
disable-model-invocation: true
---

# /alfred-verify — is the job real?

Run Alfred's scripts with `${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python` (fall back to `python3`); scripts live in
`${CLAUDE_PLUGIN_ROOT}/scripts/`. career-ops lives in `${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops`: run its `node` scripts from
there with `CAREER_OPS_ROOT=${ALFRED_HOME:-$HOME/.alfred}` exported, so it reads and writes Alfred's own files.

1. Needs `data/finder_output.json` (run `/alfred:alfred-find` first).
2. Invoke `alfred:job-verifier` → `data/verified_jobs.json`, `data/verify_dropped.json`.
3. Report checked / live / unconfirmed / dropped (with reasons) / reposts.

To check one posting by hand: `careerops_bridge.py liveness <url>`.
