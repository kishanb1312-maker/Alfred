# Alfred — instructions for any agent host

Alfred is a human-in-the-loop job-application assistant. This file is the entry point for
hosts that read `AGENTS.md` (ChatGPT Codex and similar). Claude Code users get the same
behaviour through the plugin's `/alfred:alfred-*` commands and do not need this file.

## What Alfred is

Six stages, run in order. Each is fully specified in its own file under `agents/` — those
files are the source of truth for behaviour, and this file only says how to invoke them:

| Stage | Spec | Acts on the world? |
|---|---|---|
| 1. Find jobs | `agents/job-finder.md` | No |
| 2. Research + score | `agents/company-research.md` | No |
| 3. Tailor resume | `agents/resume-cover-letter.md` | No |
| 4. Track in Notion | `agents/tracker.md` | Writes to Notion only |
| 5. Approval gate | `agents/approval-gate.md` | Sends Telegram cards |
| 6. Apply | `agents/application-agent.md` | **YES — the only stage that does** |

There is no automatic chaining outside Claude Code. Run one stage per request, read its
output, then start the next. Each stage writes its results to `data/` so the next one can
pick them up — that is what makes stage-at-a-time driving work.

## Non-negotiable rules

1. **`dry_run: true` in `config/search.yaml` means simulate, never send.** Log what would
   happen. This is the single most important setting in the repo.
2. **Nothing is applied or emailed without an explicit human Approve** on Telegram. Stage 6
   acts only on `data/approved_queue.json`.
3. **Never fabricate a job, a company, an email address, or a resume claim.** A stage that
   cannot find something reports zero and says why. An invented listing poisons every stage
   downstream.
4. **Never store credentials.** Browser stages rely on a session the user is already signed
   into. If there is no such session, skip that source with a note — do not attempt to log in.
5. Respect `caps`, `pacing`, and `max_age_days` from `config/search.yaml`.

## Setup (once)

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
export ALFRED_HOME="$(pwd)"          # data/output live here; add to your shell profile
./.venv/bin/python scripts/alfred_cli.py doctor
```

`doctor` prints a readiness checklist. Work through whatever it flags before running stages.

## Running a stage

Ask the host to read the stage's spec and follow it, e.g.:

> Read `agents/job-finder.md` and run only that stage. Report per-source results. No sends.

Use `./.venv/bin/python` for every script call so the venv's deps resolve.

## Capabilities this host may or may not have

Alfred degrades honestly rather than failing when a capability is missing:

- **Browser** — needed by `linkedin_easy_apply`, `linkedin_feed`, `indeed`, `wellfound`.
  Discovery order and the honest-skip rule are in `agents/job-finder.md`. Without one,
  those sources skip with a note and the API/RSS sources still run.
- **Notion MCP** — needed by stage 4 only. Without it, skip tracking; the pipeline still
  works, you just lose the permanent archive.
- **Telegram** — pure Python (`scripts/telegram_bot.py`), needs no host capability, only
  the bot token in `.env`.

## Verifying without touching the world

Every stage has an offline dry run:

```bash
for f in scripts/dry_run_*.py; do ./.venv/bin/python "$f"; done
```

15 suites, all offline, no network and no real history writes. Run these first if you are
unsure whether the environment is set up correctly.
