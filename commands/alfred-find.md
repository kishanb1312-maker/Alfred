---
description: Run ONLY the job-finder stage — Alfred's boards, the career-ops zero-token scanner, and LinkedIn/Indeed/Wellfound through Aside. No sends.
disable-model-invocation: true
---

# /alfred-find — job-finder only

Run Alfred's scripts with `${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python` (fall back to `python3`); scripts live in
`${CLAUDE_PLUGIN_ROOT}/scripts/`. career-ops lives in `${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops`: run its `node` scripts from
there with `CAREER_OPS_ROOT=${ALFRED_HOME:-$HOME/.alfred}` exported, so it reads and writes Alfred's own files.

1. **Preflight** — `orchestrate.py --preflight`; non-zero → STOP and report.
2. **Invoke** `alfred:job-finder` → `data/finder_output.json` + `data/finder_report.json`.
3. Report per-source counts, what was skipped and why.

Finding never contacts anyone or submits anything.
