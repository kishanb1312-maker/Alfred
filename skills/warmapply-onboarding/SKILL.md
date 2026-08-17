---
name: warmapply-onboarding
description: Guided first-run setup for WarmApply — creates the venv & installs deps, initializes ~/.warmapply, ingests the resume, collects search + screening config conversationally, walks the user through setting secrets via the CLI (never in chat), detects the Telegram chat id, points at the Notion + browser connectors, and loops on `warmapply doctor` until green. Keeps dry_run ON.
when_to_use: When the user runs /warmapply-setup, or asks to set up / configure / onboard WarmApply for the first time.
---

# WarmApply onboarding wizard

Guide the user through setup, one step at a time. Confirm each step succeeded before moving on.
**Do not change any agent behavior or the apply flow — this is setup only.**

## Two rules that hold for the ENTIRE wizard

1. **Secrets are NEVER typed into chat and NEVER written by you.** For every secret, show the user how
   to obtain it and have them run `warmapply set-secret <KEY>` **in their own terminal** (it prompts
   with `getpass`, no echo). Never ask the user to paste a token/password into the chat, never put a
   secret in a file yourself, and never echo one back.
2. **Non-secret config IS collected conversationally.** Ask for roles, locations, screening answers,
   etc. in chat and write them directly to `~/.warmapply/config/*.yaml`. Always keep `dry_run: true`.

## Works on Windows, macOS, and Linux

WarmApply runs natively on all three — **no WSL / Ubuntu install is required on Windows.** The one thing
that differs between OSes is shell syntax and the venv layout, so **first detect the OS** and use the
matching column throughout. On Windows, prefer **PowerShell** (the default Claude Code shell there).

| | Windows (PowerShell) | macOS / Linux (bash/zsh) |
|---|---|---|
| Home dir | `$env:USERPROFILE\.warmapply` | `$HOME/.warmapply` |
| Venv python | `~\.warmapply\.venv\Scripts\python.exe` | `~/.warmapply/.venv/bin/python` |
| Plugin dir var | `$env:CLAUDE_PLUGIN_ROOT` | `$CLAUDE_PLUGIN_ROOT` |
| System python | `py -3` or `python` | `python3` |

You usually don't need to hand-build the venv path — **`warmapply env` prints the correct one for the
user's OS**. And **`warmapply bootstrap` does the whole environment setup in one cross-platform step**, so
you rarely touch shell-specific venv commands at all.

## Conventions used below

- **Python env:** the venv python created in Step 1 — get its exact path with `warmapply env`. Until the
  venv exists, use `python3` (macOS/Linux) or `py -3` / `python` (Windows).
- **CLI:** `<python> "<CLAUDE_PLUGIN_ROOT>/scripts/warmapply_cli.py" <subcommand>`. Resolve the plugin dir
  first — `echo "$CLAUDE_PLUGIN_ROOT"` (bash) or `echo $env:CLAUDE_PLUGIN_ROOT` (PowerShell) — and quote
  the path so a Windows `C:\Program Files\...` with spaces still works.
- User data lives in `~/.warmapply/` (override: `WARMAPPLY_HOME`); the plugin code is read-only.

---

## Step 1 — Environment bootstrap
**One cross-platform command does it all** — venv, dependency install, and data-dir init:

```
<system-python> "<CLAUDE_PLUGIN_ROOT>/scripts/warmapply_cli.py" bootstrap
```

`bootstrap` creates `~/.warmapply/.venv`, installs `requirements.txt` into it, and runs `init` (creating
`~/.warmapply/{config,data,output}/` + the config templates + a blank `.env`). It is idempotent and runs
identically on Windows, macOS, and Linux — no shell-specific venv syntax. If `py -3`/`python`/`python3`
isn't found on Windows, tell the user to install Python from **python.org** and tick *"Add python.exe to
PATH"* during install, then re-run.

After it finishes, capture the venv python for later steps with `warmapply env`.

> Prefer `bootstrap`. Only fall back to manual venv creation
> (`python -m venv <home>\.venv` on Windows, `python3 -m venv <home>/.venv` on POSIX) if `bootstrap` fails.

**LibreOffice** (needed for DOCX→PDF): check with `warmapply doctor` (it now detects Windows installs off
PATH too). If missing, give the user the command for **their OS** and let them run it — **do not install
system software silently**:
- Windows: `winget install TheDocumentFoundation.LibreOffice`
- macOS: `brew install --cask libreoffice`
- Ubuntu/Debian: `sudo apt-get install libreoffice`

## Step 2 — Resume
Ask for the path to their master resume `.docx`. Run `warmapply parse-resume <path>`. Show the extracted
fields (name, emails, skills, titles) and the `still_needed` list — you'll fill those gaps in Steps 3–4.
The resume is copied into `~/.warmapply/data/`.

## Step 3 — Search config → `~/.warmapply/config/search.yaml`
Collect conversationally, then **write the file yourself** (mirror the structure of the committed
`config/search.example.yaml`, keeping every comment-worthy key):
- target **roles** / titles, **locations**, **seniority**
- **blacklist_companies** to skip
- **caps.applies_per_day** (daily cap)
- **match_threshold** (default **70**)
- **`dry_run: true`** — keep it ON for the first pass; do not turn it off.
Confirm the written values back to the user.

## Step 4 — Screening answers → `~/.warmapply/config/profile.yaml`
These are the things a resume can't supply (mirror `config/profile.example.yaml`). Ask for:
- **work_authorization / visa**, **notice_period / availability**
- **salary_expectation**, **willing_to_relocate**, **remote_preference**
- **phone**, **linkedin_url**, **portfolio_url / github_url**, and any common **screening_answers**.
Write the file yourself and confirm the values. (None of this is secret — it's fine in chat.)

## Step 5 — Secrets (NEVER in chat)
For each key below: explain briefly where it comes from, then have the user run
`warmapply set-secret <KEY>` **in their own terminal**. Give them the exact command (resolve
`${CLAUDE_PLUGIN_ROOT}` to an absolute path). Do not proceed to detect the chat id until the token is set.

| Key | Where the user gets it |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Create **their OWN** bot in `@BotFather` (~2 min) → copy the token. **Each user must create their own bot** — a shared bot's `getUpdates` queue is consumed per-bot, so taps would be delivered to the wrong machine and the approval safety model breaks. |
| `GMAIL_ADDRESS` | A **dedicated** job-hunt Gmail (not their personal inbox). |
| `GMAIL_APP_PASSWORD` | In that Gmail: enable 2-Step Verification → create an **App Password** for "Mail" (SMTP). Not their normal password. |
| `HUNTER_API_KEY` **or** `APOLLO_API_KEY` *(optional)* | Hunter.io free tier or Apollo → API key. Optional; leave blank if unused. |

Remind them: `TELEGRAM_CHAT_ID` is **auto-detected** in Step 6 — they don't set it by hand.

## Step 6 — Telegram chat id
Once `TELEGRAM_BOT_TOKEN` is set, tell the user to open Telegram and **send any message to their bot
once**. Then run `warmapply detect-telegram-chat-id` — it reads `getUpdates`, extracts `chat.id`, and
writes `TELEGRAM_CHAT_ID`. If it reports no message yet, have them message the bot and re-run.

## Step 7 — Notion + browser (MCP — no `.env`)
These are authorized **in Claude Code**, not via secrets:
- **Notion:** connect the **Notion** connector (`/mcp` or connector settings). The tracker agent uses the
  `notion-*` MCP tools; OAuth is per-user.
- **LinkedIn / browser:** just stay logged in to LinkedIn in their real **Chrome** — the Claude-in-Chrome
  MCP drives it. **No LinkedIn password is ever stored.**

## Step 8 — Verify
Run `warmapply doctor` and show the checklist. Resolve any ❌ (required) items and re-run until it reports
**READY**; ⚠️ advisories (LibreOffice, optional keys, Notion-via-MCP) are fine to defer. Finish by
reminding the user that **dry_run stays ON** for the first pass — a full `/warmapply-run` will prepare
everything but send/submit nothing — and that they can run any single stage with `/warmapply-find`,
`-research`, `-tailor`, `-track`, `-approve`, or `-apply`.
