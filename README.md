# WarmApply

A **Claude-Code-native** job-application assistant that leads with **warm, direct-to-recruiter
outreach** over spray-and-pray. It finds IT jobs, researches the
company, tailors your resume & cover letter **truthfully** (your format and projects stay
locked — only wording is adjusted), tracks everything in **Notion**, and applies via the
job portal or a **direct recruiter email** — but only **after you approve each one on Telegram**.

> Built for a friends circle, not sold as a product. There is **no Claude API key and no
> per-token bill** — your own **Claude Code session is the brain**. You run it manually when
> you're job-hunting.

See [`SPEC.md`](SPEC.md) for the full design.

---

## How it works

- Your **Claude Code session** orchestrates a set of **subagents** in [`agents/`](agents).
- **External services** (Notion, LinkedIn/Easy Apply, Telegram, email) are reached through
  **MCP tools** in Claude Code.
- **Deterministic helpers** (DOCX→PDF, email verification, applied-history, match scoring)
  are small **Python scripts** in [`scripts/`](scripts) run via Bash.
- Nothing is submitted or emailed without your **explicit Telegram approval**.

---

## Setup (each user, on their own machine)

WarmApply installs as a **Claude Code plugin** — no cloning, no manual `cp`, no `.env` editing.

```
/plugin marketplace add kishanb1312-maker/WarmApply
/plugin install warmapply@warmapply
/warmapply-setup      # first-run wizard (guided, conversational)
/warmapply-run        # run the pipeline (keep dry_run: true for the first pass)
```

`/warmapply-setup` walks you through everything: it creates a venv and installs deps, initializes
`~/.warmapply/`, ingests your **master resume** (ATS-simple `.docx`), and collects your search +
screening answers **in chat**. Your data lives in `~/.warmapply/` (override with `WARMAPPLY_HOME`);
the plugin code stays read-only and updates with the plugin.

> **Secrets are never typed into chat.** The wizard has you run `warmapply set-secret <KEY>` in your
> **own terminal** (hidden `getpass` prompt) — Claude never sees a token or password. Non-secret
> config (roles, locations, screening answers) *is* collected conversationally.

### How each service is connected

**Channel A — secrets in `~/.warmapply/.env`** (set via `warmapply set-secret`, never in chat):

| Service | What you do | Keys |
|---|---|---|
| **Telegram** | Create a bot in `@BotFather` (~2 min) → copy the token. Message the bot once, then run `warmapply detect-telegram-chat-id`. **Not MCP** — the app calls the Bot API over HTTP with this token. | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |
| **Google / Gmail** | Use a **dedicated** job-hunt Gmail. Enable 2-Step Verification → create an **App Password** for "Mail". **Not OAuth, not MCP** — the app sends via SMTP with this app password. | `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD` |
| **Email finder** *(optional)* | Sign up for Hunter.io (free tier) or Apollo → copy the API key. | `HUNTER_API_KEY` *or* `APOLLO_API_KEY` |

A minimal working setup is the **4 required keys** — and `TELEGRAM_CHAT_ID` auto-fills — so it's
effectively **3 `set-secret` runs + messaging the bot once**.

**Channel B — MCP connectors** (authorized in Claude Code, no `.env`):

| Service | What you do |
|---|---|
| **Notion** | Connect the **Notion** connector in Claude Code (`/mcp` or connector settings). OAuth is per-user; the plugin only *declares* it. The tracker agent then uses the `notion-*` MCP tools. |
| **LinkedIn / browser** | Just stay logged in to LinkedIn in your real **Chrome**. The Claude-in-Chrome MCP drives it — **no LinkedIn password is ever stored.** |

> **Each user must create their OWN Telegram bot — do not share one.** The bot token is a master
> secret, and the approval-gate polls `getUpdates` with a saved offset that **consumes** updates.
> Telegram has one update queue per bot, so a shared bot would deliver one person's Approve/Skip tap to
> someone else's machine, breaking the human-in-the-loop safety model. Creating a bot is ~2 min in
> `@BotFather`; the wizard auto-detects your chat ID afterward.

---

## Running

Run the whole pipeline with **`/warmapply-run`** (or just say **"run WarmApply"**). It follows
[`RUNBOOK.md`](RUNBOOK.md) — reconcile → find → research → tailor → track → approve → apply → report —
invoking the six worker subagents in [`agents/`](agents), gated on a preflight check first.

Check readiness anytime with **`/warmapply-status`** (runs `warmapply doctor` + a run summary): it
confirms your config, resume, and required secrets are in place and reports whether **dry_run** is on and
whether **/pause** is set. Keep **`dry_run: true`** until you've watched a full pass.

Run a single stage manually with **`/warmapply-find`**, **`-research`**, **`-tailor`**, **`-track`**,
**`-approve`**, or **`-apply`** — each still honors `dry_run`, `/pause`, and daily caps. Use `/loop` to
repeat a run while the session stays open.

Telegram commands: **✅ Approve** / **⏭️ Skip** per job, and **/pause** to halt all sending.

See [`RUNBOOK.md`](RUNBOOK.md) for the full step-by-step sequence and the canonical job-object
data contract.

---

## Safety & guardrails

- **Truthful tailoring** — the agent only re-emphasizes experience already in your resume;
  it never invents skills or claims.
- **Format lock** — your layout, projects, and structure are never altered.
- **Human-in-the-loop** — you approve every application; the risky final click on ban-prone
  portals (LinkedIn, Workday) stays with you.
- **No secrets in git** — `.env`, `data/`, and your real `config/*.yaml` are gitignored.

---

## Repo layout

```
.claude-plugin/   plugin.json + marketplace.json (plugin & marketplace manifests)
agents/           Claude Code subagent definitions (the six workers)
commands/         slash-command triggers (/warmapply-run, /warmapply-setup, per-stage …)
skills/           onboarding wizard (warmapply-onboarding)
scripts/          deterministic Python helpers + the `warmapply` CLI (run via Bash)
config/           example search + screening config (committed; your real ones live in ~/.warmapply)
.mcp.json         declares the Notion connector (OAuth per-user; no credentials)
SPEC.md           full design spec

~/.warmapply/     YOUR data (config, resume, output, .env) — outside the repo, per user
```
