# WarmApply — Plugin Build Spec (Claude Code plugin + marketplace)

> **Audience:** a fresh ("cold") Claude Code builder session opened in this repo.
> **Goal of this task:** convert WarmApply from a *clone-and-configure* repo into a
> **Claude Code plugin** that anyone installs from GitHub with `/plugin`, then sets up
> **interactively** — no manual `.env` editing, no manual `cp` of config files.
>
> **Do NOT change any agent behavior or the apply flow.** The reconcile → find → research →
> tailor → track → approve → apply sequence in `RUNBOOK.md` stays identical. This task only
> changes **packaging, path resolution, and first-run onboarding.**

---

## 0. Locked decisions (do not re-litigate)

| Decision | Value |
|---|---|
| Distribution | Claude Code **plugin** served from a **marketplace** in this same GitHub repo |
| User data dir | `~/.warmapply/` (override with env `WARMAPPLY_HOME`) |
| Code location | the installed plugin dir (reference via `${CLAUDE_PLUGIN_ROOT}`) — read-only, updated on plugin update |
| Secret handling | Secrets are **never** typed into chat and **never** written by Claude. A `warmapply set-secret` CLI (getpass, no echo) writes them to `~/.warmapply/.env`. Non-secret config *is* collected in chat. |
| Backward compat | Keep the old repo-relative "clone & run" path working. Path resolution falls back to repo root when `~/.warmapply` doesn't exist. |
| Marketplace repo | Same `WarmApply` repo (add `.claude-plugin/marketplace.json` at root) |

---

## 1. What a Claude Code plugin is (context for the builder)

- A **marketplace** = a git repo with `.claude-plugin/marketplace.json` at its root listing one or
  more plugins. Users run `/plugin marketplace add <owner>/<repo>` then `/plugin install <name>@<marketplace>`.
- A **plugin** = a dir with `.claude-plugin/plugin.json` plus auto-discovered component folders:
  `commands/`, `agents/`, `skills/`, `hooks/hooks.json`, and `.mcp.json`.
- `${CLAUDE_PLUGIN_ROOT}` is an env var available inside commands/hooks/mcp configs that points at
  the plugin's install directory. Use it for every reference to bundled code (scripts, etc.).

> Confirm the exact current manifest schema against the live Claude Code plugin docs before writing
> the manifests — field names may have changed since this spec was written.

---

## 2. Target file tree

```
WarmApply/                          # this repo == the marketplace AND the plugin
├── .claude-plugin/
│   ├── marketplace.json            # NEW — marketplace manifest
│   └── plugin.json                 # NEW — plugin manifest
├── agents/                         # MOVED from .claude/agents/  (plugin auto-discovers agents/)
│   ├── job-finder.md
│   ├── company-research.md
│   ├── resume-cover-letter.md
│   ├── tracker.md
│   ├── approval-gate.md
│   └── application-agent.md
├── commands/                       # NEW — slash commands (triggers)
│   ├── warmapply-setup.md          # onboarding wizard
│   ├── warmapply-status.md         # doctor + summary
│   ├── warmapply-run.md            # MAIN trigger — whole pipeline
│   ├── warmapply-find.md           # per-agent: job-finder
│   ├── warmapply-research.md       # per-agent: company-research
│   ├── warmapply-tailor.md         # per-agent: resume-cover-letter
│   ├── warmapply-track.md          # per-agent: tracker
│   ├── warmapply-approve.md        # per-agent: approval-gate
│   └── warmapply-apply.md          # per-agent: application-agent
├── skills/
│   └── warmapply-onboarding/       # NEW — the interactive setup wizard skill
│       └── SKILL.md
├── scripts/                        # unchanged code, but path resolution refactored (§4)
│   ├── warmapply_cli.py            # NEW — `warmapply` CLI entrypoint (setup helpers, set-secret)
│   ├── paths.py                    # NEW — single source of truth for all paths (§4)
│   ├── orchestrate.py              # EDIT — use paths.py instead of _REPO_ROOT
│   └── ... (all existing helpers + sources/ unchanged in logic)
├── config/                         # example configs stay committed
│   ├── search.example.yaml
│   └── profile.example.yaml
├── .env.example                    # stays as the template the wizard copies
├── requirements.txt
├── SPEC.md · RUNBOOK.md · README.md
└── PLUGIN_BUILD_SPEC.md            # this file
```

> Keep the OLD `.claude/agents/` working too, OR move them and verify the plugin still loads them from
> `agents/`. Prefer **move** to `agents/` (plugin standard) and delete `.claude/agents/` only after
> confirming the plugin resolves them.

---

## 3. The two manifests

**`.claude-plugin/plugin.json`** (illustrative — verify field names):
```json
{
  "name": "warmapply",
  "version": "1.0.0",
  "description": "Warm, human-in-the-loop job-application assistant: finds IT jobs, researches companies, tailors your resume truthfully, and applies via portal or direct recruiter email after you approve each one on Telegram.",
  "author": { "name": "WarmApply" }
}
```

**`.claude-plugin/marketplace.json`** (illustrative):
```json
{
  "name": "warmapply",
  "owner": { "name": "WarmApply" },
  "plugins": [
    {
      "name": "warmapply",
      "source": "./",
      "description": "Warm, human-in-the-loop job-application assistant."
    }
  ]
}
```

Install UX after this ships:
```
/plugin marketplace add <owner>/WarmApply
/plugin install warmapply@warmapply
/warmapply-setup      # first-run wizard
/warmapply-run        # run the pipeline
```

---

## 4. Path refactor — THE core change (`scripts/paths.py`)

Today every script derives paths from `_REPO_ROOT` (see `orchestrate.py:31-35`). That breaks once code
lives in a managed plugin dir and user data lives in the home dir. Introduce one module and route
**every** script through it.

`scripts/paths.py` responsibilities:
- `DATA_HOME` = `os.environ.get("WARMAPPLY_HOME")` → else `~/.warmapply` **if it exists** → else fall back
  to the repo root (backward compat with clone-and-run).
- Expose: `search_config()`, `profile_config()`, `env_file()`, `resume_glob()`, `pause_flag()`,
  `output_dir()`, `applied_history_path()`, `approved_queue_path()`, and any other data path currently
  hardcoded.
- `CODE_ROOT` = `${CLAUDE_PLUGIN_ROOT}` if set, else repo root — for locating bundled example files.
- Load `.env` from `env_file()` (use `python-dotenv` or a tiny parser; add to requirements if needed).

Then edit `orchestrate.py` and **every** script/source that references `config/`, `data/`, `output/`,
`.env` to import from `paths.py`. Grep for `_REPO_ROOT`, `config/`, `data/`, `output`, `.env` and fix each.

**Acceptance:** with `WARMAPPLY_HOME=~/.warmapply` set and populated, `python scripts/orchestrate.py
--preflight` passes reading from `~/.warmapply`; with it unset in a bare clone, the old behavior still works.

---

## 5. The `warmapply` CLI (`scripts/warmapply_cli.py`)

A single host-agnostic entrypoint (also the seed of future non-Claude adapters). Subcommands:

- `warmapply init` — create `~/.warmapply/{config,data,output}/`, copy `config/*.example.yaml` →
  `~/.warmapply/config/*.yaml`, copy `.env.example` → `~/.warmapply/.env` (values blank). Idempotent.
- `warmapply set-secret <KEY>` — prompt with **getpass (no echo)**, write/replace `KEY=value` in
  `~/.warmapply/.env`. This is how Telegram/Gmail/API secrets get in **without Claude ever seeing them**.
- `warmapply detect-telegram-chat-id` — after `TELEGRAM_BOT_TOKEN` is set and the user has messaged the
  bot, call `getUpdates`, extract `chat.id`, and write `TELEGRAM_CHAT_ID` to `.env`. Prints instructions
  if no message found yet.
- `warmapply doctor` — check: Python deps importable, LibreOffice (`soffice`) present, `.env` keys filled,
  Notion MCP reachable (best-effort), configs valid. Prints a checklist. (Superset of `orchestrate --preflight`.)
- `warmapply parse-resume <path.docx>` — copy the resume into `~/.warmapply/data/`, extract skills/titles
  it can read, and print a JSON of "extracted" vs "still-needed" fields to drive the wizard's questions.

The CLI must run from the plugin dir via `${CLAUDE_PLUGIN_ROOT}` and be callable from a venv.

---

## 6. The setup wizard (`skills/warmapply-onboarding/SKILL.md` + `commands/warmapply-setup.md`)

`/warmapply-setup` triggers a guided, conversational flow. Sequence:

1. **Environment bootstrap** — create a venv, `pip install -r requirements.txt`, run `warmapply init`.
   Check LibreOffice; if missing, tell the user the exact `brew install --cask libreoffice` /
   `apt-get install libreoffice` command (do not attempt system installs silently).
2. **Resume** — ask for the `.docx` path, run `warmapply parse-resume`, show what was extracted.
3. **Search config (chat → search.yaml)** — ask roles, locations, seniority, blacklist companies,
   daily cap, match threshold (default 70), keep `dry_run: true`. Write to `~/.warmapply/config/search.yaml`.
4. **Screening answers (chat → profile.yaml)** — the SPEC §10.13 list that a resume can't give:
   work authorization/visa, notice period/availability, salary expectation, relocate/remote preference,
   phone, LinkedIn/portfolio URLs. Write to `~/.warmapply/config/profile.yaml`.
5. **Secrets (NEVER in chat)** — for each of `TELEGRAM_BOT_TOKEN`, `HUNTER_API_KEY` **or** `APOLLO_API_KEY`,
   `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`: show the user how to obtain it (§8 of this file), then instruct
   them to run `warmapply set-secret <KEY>` **in their own terminal**. Claude must not ask them to paste
   secret values into the chat.
6. **Telegram chat id** — after the token is set, tell them to message their bot once, then run
   `warmapply detect-telegram-chat-id`.
7. **Notion + browser (MCP)** — instruct the user to connect the **Notion** connector and use their
   logged-in **Chrome (Claude-in-Chrome)**; these are authorized in Claude Code, not via `.env`.
8. **Verify** — run `warmapply doctor`; loop until green. Remind them `dry_run` stays ON for the first pass.

The wizard writes non-secret files directly; secrets are always user-run CLI calls.

---

## 7. Commands (triggers)

Two tiers: **one main trigger** for the whole pipeline, and **one trigger per subagent** so the user
can run any single stage manually (for debugging, re-running a failed stage, or partial runs). These do
NOT exist today — there is no `commands/` dir, and subagents are currently only reachable via the
orchestrator. Create all of them.

**Lifecycle commands**
- `commands/warmapply-setup.md` — thin wrapper that loads the onboarding skill (§6).
- `commands/warmapply-status.md` — runs `warmapply doctor` + `orchestrate.py --summary` and reports.

**Main trigger (whole pipeline)**
- `commands/warmapply-run.md` — the operator command. Its body = the existing `RUNBOOK.md` sequence,
  with a preflight/doctor gate first. No logic change; it invokes the same agents in order:
  reconcile → find → research → tailor → track → approve → apply → report.

**Per-subagent triggers (run ONE stage manually)** — each is a thin command that invokes exactly one
subagent and prints its output. They share the same canonical job-object contract, so a user can chain
them by hand or re-run just the stage that failed:

| Command | Invokes subagent | Purpose |
|---|---|---|
| `commands/warmapply-find.md` | `job-finder` | just find + de-dupe fresh jobs |
| `commands/warmapply-research.md` | `company-research` | research + email waterfall + match score on found jobs |
| `commands/warmapply-tailor.md` | `resume-cover-letter` | tailor resume/cover letter for surviving jobs |
| `commands/warmapply-track.md` | `tracker` | write/update Notion rows |
| `commands/warmapply-approve.md` | `approval-gate` | send Telegram cards + reconcile taps |
| `commands/warmapply-apply.md` | `application-agent` | process the approved queue (respects dry_run/pause/caps) |

Rules for the per-agent commands:
- Each still honors `dry_run`, `/pause`, and daily caps — running a stage manually must NOT bypass the
  guardrails (esp. `warmapply-apply`).
- Each reads/writes the same intermediate state files the orchestrator uses, so manual and full runs are
  interchangeable.
- Keep them thin: the command just invokes the subagent; all logic stays in the subagent `.md` files.

---

## 8. HOW EACH SERVICE IS CONNECTED (put this in README + the wizard's help text)

This is the answer to "how do users connect Telegram / Google / Notion" once there's no repo `.env`.
There are **two channels**:

**Channel A — secrets in `~/.warmapply/.env`** (set via `warmapply set-secret`, never in chat):

| Service | What the user does | Keys |
|---|---|---|
| **Telegram** | Create a bot in `@BotFather` (~2 min) → copy token. Message the bot once, then `warmapply detect-telegram-chat-id`. **Not MCP** — the app calls the Bot API over HTTP with this token. | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |
| **Google / Gmail** | Use a **dedicated** job-hunt Gmail. Enable 2-Step Verification → create an **App Password** for "Mail". **Not OAuth, not MCP** — the app sends via SMTP with this app password. | `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD` |
| **Email finder** | Sign up for Hunter.io (free tier) or Apollo → copy API key. | `HUNTER_API_KEY` *or* `APOLLO_API_KEY` |

**Channel B — MCP connectors (authorized in Claude Code, no `.env`):**

| Service | What the user does |
|---|---|
| **Notion** | Connect the Notion connector in Claude Code (`/mcp` or connector settings). OAuth is per-user; the plugin only *declares* it as needed. The tracker agent then uses the `notion-*` MCP tools. |
| **LinkedIn / browser** | Just stay logged in to LinkedIn in their real Chrome. The Claude-in-Chrome MCP drives it; **no LinkedIn password is ever stored.** |

> Optionally add a `.mcp.json` to the plugin that lists Notion (and browser, if applicable) as
> recommended MCP servers so `/plugin install` can prompt the user to connect them. Verify the current
> `.mcp.json` schema before adding.

### 8a. Exact `.env` contents (what the wizard collects)

Confirmed by grepping the scripts — only **4 vars are actually consumed by code today**:

**Required (4):**
- `TELEGRAM_BOT_TOKEN` — from `@BotFather`
- `TELEGRAM_CHAT_ID` — auto-detected via `warmapply detect-telegram-chat-id`
- `GMAIL_ADDRESS` — dedicated job-hunt Gmail
- `GMAIL_APP_PASSWORD` — Gmail App Password (requires 2FA)

**Optional / not yet wired (leave blank unless used):**
- `HUNTER_API_KEY` **or** `APOLLO_API_KEY` — email-finder waterfall. Current code verifies emails via
  DNS/MX (`email_verify.py`), so these are not consumed yet; keep as optional placeholders.
- `NOTION_API_KEY`, `NOTION_DATABASE_ID` — normally **blank**; Notion is reached via MCP, not `.env`.

So a minimal working setup = the 4 required keys, one of which auto-fills → effectively **3 `set-secret`
runs + messaging the bot once.**

### 8b. Each user MUST create their own Telegram bot (do NOT share one)

The wizard must instruct every user to create their **own** bot. A shared bot breaks WarmApply because:
1. The bot token is a master secret — anyone holding it can read all the bot's messages and impersonate it.
2. The approval-gate polls `getUpdates` with a saved offset and **consumes** updates. Telegram has one
   update queue per bot, so if multiple users share a bot, one user's poll swallows another user's
   Approve/Skip tap → approvals get delivered to the wrong machine and the human-in-the-loop safety model
   breaks. WarmApply is server-less (local polling), so one bot = one poller.

Creating a bot is ~2 min in `@BotFather`; the wizard auto-detects the chat ID afterward.

---

## 9. Docs to update

- `README.md` — replace the "clone + cp + pip" setup section with the `/plugin` install + `/warmapply-setup`
  flow, and add the §8 connection tables.
- `RUNBOOK.md` — note that paths now resolve to `~/.warmapply`; the sequence itself is unchanged.
- Keep `SPEC.md` as the design record; add a one-line pointer to this plugin spec.

---

## 10. Build order (do in this sequence, verify each before moving on)

1. `scripts/paths.py` + refactor `orchestrate.py` to use it; prove preflight works from both `~/.warmapply`
   and a bare clone. **(Highest-risk change — do first, test hard.)**
2. Route every other script/source through `paths.py` (grep-driven).
3. `scripts/warmapply_cli.py` — `init`, `set-secret`, `detect-telegram-chat-id`, `doctor`, `parse-resume`.
4. Move `.claude/agents/` → `agents/`; add `.claude-plugin/plugin.json` + `marketplace.json`.
5. `commands/` (setup, run, status) + `skills/warmapply-onboarding/SKILL.md`.
6. Optional `.mcp.json` declaring Notion/browser.
7. Update `README.md` + `RUNBOOK.md`.
8. **End-to-end dry-run acceptance:** from a simulated fresh install, run `/warmapply-setup` to green
   `doctor`, then `/warmapply-run` with `dry_run: true` and confirm the full pipeline prepares (but sends
   nothing) exactly as it does today.

## 11. Non-negotiables (unchanged from SPEC.md)

Truthful tailoring · format lock · mandatory "what I changed" note · Telegram approve before any send ·
human final click on ban-prone portals · `dry_run` blocks real sends · `/pause` halts the application
agent · secrets never in git and never in chat.
