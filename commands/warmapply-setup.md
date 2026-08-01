---
description: First-run WarmApply setup wizard — venv & deps, resume, search + screening config, secrets (via CLI, never in chat), Telegram, Notion, and a doctor check.
disable-model-invocation: true
---

# /warmapply-setup — first-run wizard

Load and follow the **warmapply-onboarding** skill now — invoke the Skill tool with
`warmapply:warmapply-onboarding`. That skill runs the complete guided setup (§6 of the build spec).

Two rules that must hold throughout:
- **Secrets are NEVER collected in chat.** For every secret (`TELEGRAM_BOT_TOKEN`, `GMAIL_ADDRESS`,
  `GMAIL_APP_PASSWORD`, optional API keys), the wizard shows the user how to obtain it and has them run
  `warmapply set-secret <KEY>` in **their own terminal** (getpass, no echo). Do not ask the user to
  paste a secret value, and never write a secret yourself.
- **Non-secret config IS collected conversationally** (roles, locations, seniority, blacklist, caps,
  match threshold, work authorization, notice period, salary, relocate/remote, phone, profile URLs) and
  written directly to `~/.warmapply/config/search.yaml` and `~/.warmapply/config/profile.yaml`, keeping
  `dry_run: true`.
