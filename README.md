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

- Your **Claude Code session** orchestrates a set of **subagents** in [`.claude/agents/`](.claude/agents).
- **External services** (Notion, LinkedIn/Easy Apply, Telegram, email) are reached through
  **MCP tools** in Claude Code.
- **Deterministic helpers** (DOCX→PDF, email verification, applied-history, match scoring)
  are small **Python scripts** in [`scripts/`](scripts) run via Bash.
- Nothing is submitted or emailed without your **explicit Telegram approval**.

---

## Setup (each user, on their own machine)

1. **Clone** this private repo.
2. Install Python deps and LibreOffice:
   ```bash
   pip install -r requirements.txt
   # macOS:  brew install --cask libreoffice
   # Ubuntu: sudo apt-get install libreoffice
   ```
3. **Copy the templates** and fill in your own values (these copies are gitignored):
   ```bash
   cp .env.example .env
   cp config/search.example.yaml config/search.yaml
   cp config/profile.example.yaml config/profile.yaml
   ```
4. Put your **master resume** (ATS-simple `.docx`) in `data/`.
5. Create a **Telegram bot** via `@BotFather`, a **dedicated job-hunt Gmail** (App Password),
   and a **Hunter.io/Apollo** API key — put them in `.env`.
6. Connect the **Notion** MCP connector in Claude Code, and use your **real logged-in Chrome**
   (Claude-in-Chrome) so LinkedIn Easy Apply works without re-login.

---

## Running

Open a Claude Code session in this folder and tell it to start the job hunt.
Keep `dry_run: true` in `config/search.yaml` until you've watched it work end-to-end.
Use `/loop` if you want it to repeat while the session stays open.

Telegram commands: **✅ Approve** / **⏭️ Skip** per job, and **/pause** to halt all sending.

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
.claude/agents/   Claude Code subagent definitions (the sub-agents)
scripts/          deterministic Python helpers (run via Bash)
config/           search + screening-question config (examples committed; real ones gitignored)
data/             your master resume + applied-history (gitignored)
SPEC.md           full design spec
```
