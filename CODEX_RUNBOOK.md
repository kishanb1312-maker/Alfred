# Alfred — running it outside Claude Code (Codex and similar)

There is no automatic chaining here: run one stage per request. Each stage reads and writes
`data/`, so stopping after any stage is safe and resuming is just the next prompt.

> Keep `dry_run: true` until you have watched a full pass. Stage 7 is the only one that acts.

## Setup (once)

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
export ALFRED_HOME="$(pwd)"
./.venv/bin/python scripts/alfred_cli.py careerops-install
./.venv/bin/python scripts/alfred_cli.py doctor
./.venv/bin/python scripts/run_tests.py
```

## Prompts

| # | Prompt |
|---|---|
| 1 | Read `agents/job-finder.md` and run only that stage. Report per-source results. No sends. |
| 2 | Read `agents/job-verifier.md` and run only that stage on `data/finder_output.json`. |
| 3 | Read `agents/job-evaluator.md` and `vendor/career-ops/AGENTS.md`, then evaluate `data/verified_jobs.json`. |
| 4 | Read `agents/contact-finder.md` and run it on jobs with score ≥ `min_score`. |
| 5 | Read `agents/cv-tailor.md` and run it on the same jobs. |
| 6 | Run `./.venv/bin/python scripts/alfred_cli.py review` and show me the list. *(You decide: `alfred approve <id>` / `skip <id>`.)* |
| 7 | Read `agents/application-agent.md` and apply to `data/approved_queue.json`. |

Codex has no Aside MCP: the agents call the `aside` CLI through the shell (`aside exec "…"`).
Without Aside, the browser sources and portal applying are skipped with a note.

## After applying

Ask for any career-ops mode by name, e.g. "Read `vendor/career-ops/AGENTS.md`,
`modes/_custom.md` and `vendor/career-ops/modes/followup.md`, then run followup." The same works
for `interview-prep`, `interview/practice`, `offer-prep`, `patterns`, `calibrate`, `upskill`.
