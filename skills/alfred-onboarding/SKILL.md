---
name: alfred-onboarding
description: Guided first-run setup for Alfred — venv & deps, the pinned career-ops engine, cv.md built from the user's own resume, career-ops profile + portals (onboard-write.mjs), Alfred search + screening config, Gmail secrets via the CLI (never in chat), the Aside browser check, and `alfred doctor` until green. Keeps dry_run ON.
when_to_use: When the user runs /alfred-setup, or asks to set up / configure / onboard Alfred for the first time.
---

# Alfred onboarding wizard

Guide the user through setup one step at a time; confirm each step worked before the next.

## Rules for the whole wizard

1. **Secrets are never typed into chat and never written by you.** The user runs
   `alfred set-secret <KEY>` in their own terminal (hidden prompt).
2. **Non-secret config is collected in chat** and written by you. Keep `dry_run: true`.
3. **cv.md comes only from the user's resume and what they tell you.** Reorganize, never invent.

## Conventions

- **CLI:** `<venv python> "<CLAUDE_PLUGIN_ROOT>/scripts/alfred_cli.py" <subcommand>` (`alfred env`
  prints the venv python). Below, `alfred <sub>` means that.
- **Home:** `$ALFRED_HOME` or `~/.alfred`. Alfred's data AND career-ops's user files live there
  (`cv.md`, `config/profile.yml`, `portals.yml`, `modes/_profile.md`, `data/applications.md`,
  `reports/`). career-ops's code lives in `<home>/vendor/career-ops`.
- **career-ops scripts:** run from `<home>/vendor/career-ops` with `CAREER_OPS_ROOT=<home>`.

---

## Step 1 — Environment
`<system python> "<CLAUDE_PLUGIN_ROOT>/scripts/alfred_cli.py" bootstrap` — venv, Python deps,
`<home>/{config,data,output}`, templates, a blank `.env`. Idempotent.

## Step 2 — career-ops engine
Needs **Node.js 22.13+** and **git** (`node --version`). Missing Node → give the command for their
OS (`brew install node`, `winget install OpenJS.NodeJS.LTS`, or their distro's package) and let
them run it; never install system software silently.

Then tell the user what it downloads (career-ops at a pinned commit from GitHub, its npm packages,
and a headless Chromium for CV PDFs and liveness checks — about 200 MB) and, on their yes:
`alfred careerops-install`. It also copies career-ops's personalization templates and writes
Alfred's house rules into `modes/_custom.md`.

## Step 3 — CV → `cv.md`
Ask for the master resume `.docx` (or reuse the one already in `<home>/data/`).
1. `alfred parse-resume <path>` (copies it into `data/`, shows the extracted fields).
2. `alfred cv-from-docx <path>` → a first `cv.md`.
3. Reshape `cv.md` into the shape career-ops's checks read, **using only text already in it**:
   `## Summary`, `## Experience` with each job as `### Company — Location`, a `**Title**` line and a
   dates line, then bullets; `## Projects`, `## Education`, a heading containing "Skills". Show the
   user the result and fix what they point out.
4. Optional: proof points (case studies, metrics, portfolio pieces) the user wants to lead with →
   `article-digest.md`, in their words.

## Step 4 — career-ops profile + portals
Ask (in chat): full name, email, phone, location + timezone, target roles, years of experience,
salary target range + currency (+ minimum), countries/cities they will work in, titles to exclude,
and spend tier (economy / standard / premium). Reuse what `config/profile.yaml` already has.
Write the answers to a temp JSON in `onboard-write.mjs`'s shape (see
`vendor/career-ops/AGENTS.md` → First Run, Step 3) and run:
`alfred careerops-onboard <answers.json>` → `config/profile.yml` + `portals.yml`.

Then personalize `modes/_profile.md` (archetypes, North Star, comp targets, location policy) and
`modes/_brief.md` (the triage brief) **from cv.md and the user's answers**, so scores are measured
against the user's targeting, not the template author's. `node doctor.mjs --json` lists any file
still on the template under `unpersonalized`.

For Indian design roles, add the companies the user cares about to `portals.yml` (career-ops's
`discover` mode resolves company names to their ATS boards: `/alfred:alfred-mode discover`).

## Step 5 — Alfred config
- `config/search.yaml` (mirror `config/search.example.yaml`): roles, locations, seniority,
  `search_order` (keep `careerops_scan` first), `max_age_days`, blacklist, caps, `min_score`
  (default 4.0), `apply.auto_submit`, pacing, **`dry_run: true`**.
- `config/profile.yaml` (mirror `config/profile.example.yaml`): screening answers a form asks —
  work authorization, notice period, availability, salary expectation, relocation, remote
  preference, phone, LinkedIn/portfolio URLs, years per skill.

## Step 6 — Secrets (never in chat)
| Key | Where it comes from |
|---|---|
| `GMAIL_ADDRESS` | A dedicated job-hunt Gmail, not the personal inbox. |
| `GMAIL_APP_PASSWORD` | That Gmail → 2-Step Verification on → App Password for "Mail". |
| `HUNTER_API_KEY` / `APOLLO_API_KEY` *(optional)* | Hunter.io or Apollo. |

Give the exact `alfred set-secret <KEY>` command for each.

## Step 7 — Aside
Alfred's only browser. `aside --version` (or `~/.local/bin/aside`). Missing → point the user to
https://aside.com; without it LinkedIn/Indeed/Wellfound and portal applying are skipped, and the
zero-token sources still run. Ask them to stay signed in to LinkedIn, Indeed and Wellfound in
Aside. No password is ever stored.

## Step 8 — Verify
`alfred doctor` until **READY** (⚠️ advisories can wait). Then explain the flow:
`/alfred:alfred-run` (find → verify → evaluate → CV → review), `/alfred:alfred-approve` to decide,
`/alfred:alfred-apply` to apply — and that **dry_run stays ON** until they have watched a full pass.
