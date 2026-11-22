---
description: First-run Alfred setup — venv, the career-ops engine, cv.md from your resume, career-ops profile + portals, Alfred search + screening config, Gmail secrets (via CLI, never in chat), Aside check, and a doctor run.
disable-model-invocation: true
---

# /alfred-setup — first-run wizard

Load and follow the **alfred-onboarding** skill now — invoke the Skill tool with
`alfred:alfred-onboarding`.

Rules that hold throughout:
- **Secrets are NEVER collected in chat.** `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD` and optional API
  keys are entered by the user with `alfred set-secret <KEY>` in their own terminal.
- **Non-secret config IS collected conversationally** and written to `config/search.yaml`,
  `config/profile.yaml`, and (through career-ops's writer) `config/profile.yml` + `portals.yml`,
  keeping `dry_run: true`.
- `cv.md` is built only from the user's own resume and what they say — nothing invented.
