# Alfred — Plugin Build Progress & Change List

> **Companion to [`PLUGIN_BUILD_SPEC.md`](PLUGIN_BUILD_SPEC.md).** That file has the full design;
> **this file is the actionable checklist** the builder works through in order, and the architect
> session reviews against. Update the checkboxes as each step is approved.
>
> **Rules (every step):** keep `dry_run: true` while testing · show the architect the real changed
> code + a dry-run result before committing · **nothing is committed until the architect approves** ·
> never touch the user's real `~/.alfred` or home dir during tests (use isolated fixtures).

---

## Step 1 — path foundation ✅ DONE & APPROVED
`scripts/paths.py` (new) + `scripts/orchestrate.py` (refactored).
- Two roots: `DATA_HOME` (user data) and `CODE_ROOT` (bundled code), with correct fallbacks.
- `.env` auto-loads on import; real exported env vars win over the file.
- Proven: plugin mode reads from `ALFRED_HOME`; bare clone falls back to repo root.
- *Reviewed by architect against the real code — correct.*

---

## Step 2 — route EVERY other script through `paths.py`  ✅ DONE & APPROVED
Replaced all per-script `_REPO_ROOT` derivations and hardcoded paths with `paths.*()` calls.

**Core scripts fixed:**
- [x] `scripts/applied_history.py` → `paths.applied_history_path()`
- [x] `scripts/daily_caps.py` → `paths.daily_counts_path()`
- [x] `scripts/bounce_check.py` → `paths.email_paused_flag()`
- [x] `scripts/telegram_bot.py` → `paths.telegram_state_path()` / `pause_flag()` / `approved_queue_path()`
      *(helper renamed `telegram_offset_path`→`telegram_state_path`; real filename `telegram_state.json` kept)*
- [x] `scripts/email_send.py` — **no-op confirmed**: no hardcoded path; reads pause via `bounce_check.is_email_paused()`
- [x] `scripts/notion_schema.py` — **no-op confirmed**: `output/` only in a docstring
- [x] `scripts/sources/greenhouse_lever.py` — triple-dirname removed → `paths.search_config()` / `search_example()`

**dry-run harnesses audited:**
- [x] `dry_run_company_research.py`, `dry_run_orchestrate.py` → example refs routed to `CODE_ROOT`
- [x] `dry_run_job_finder.py` → writable demo store moved to `tempfile`
- [x] `dry_run_resume.py` → no change needed (isolated fixtures)

**Cross-cutting — all satisfied:**
- [x] Sibling-import trap → **Rule A** (every entry-point ensures `scripts/` on `sys.path`); subdir files
      under `scripts/sources/` add the explicit parent-insert mirroring `source_dispatch.py:26`.
- [x] Write safety → all writers already had `os.makedirs(exist_ok=True)`; preserved.
- [x] Doc fix → `orchestrate.py` comment corrected; `ALFRED_HOME`-must-be-exported note added to `paths.py`.

**Architect verification (real code + runtime, not summary):** `_REPO_ROOT` lives only in `paths.py`;
full tree byte-compiles; all sibling imports resolve at runtime; every data filename preserved
(`telegram_state.json`, `applied_history.json`, `daily_counts.json`, `email_paused.flag`);
email-pause writer & reader share one path source. **Correct.**

---

## Step 3 — the `alfred` CLI  (`scripts/alfred_cli.py`)  ✅ DONE & APPROVED
- [x] `init` — creates `~/.alfred/{config,data,output}/`, copies templates, `.env` 0600, idempotent.
- [x] `set-secret <KEY>` — getpass (no echo), value never in argv/printed, atomic 0600 upsert.
- [x] `detect-telegram-chat-id` — `getUpdates` → `TELEGRAM_CHAT_ID`; network isolated behind injectable `_fetch`.
- [x] `doctor` — deps/configs/resume/secrets/LibreOffice/Notion; required-vs-advisory split; delegates to preflight.
- [x] `parse-resume <path>` — read-only extraction (invents nothing), prints extracted vs still-needed.

**Security fixes found in review & verified (independent tests):**
- [x] **Token leak** — `cmd_detect` error path printed the raw exception, which embeds the token in the
      request URL. Fixed with `_redact(str(exc), token)`. *Architect re-tested the real error path: token
      redacted to `bot***REDACTED***/getUpdates`, absent from output.*
- [x] **Temp-file perm race** — `write_secret` now creates the temp `0600` from the start via
      `os.open(..., O_CREAT, 0o600)` (was chmod-after-write). Proven under hostile `umask 000`.

**Acceptance:** `init` → `set-secret` → `doctor` produces a green checklist; real `~/.alfred` never touched.

---

## Step 4 — plugin packaging  ✅ DONE & APPROVED
- [x] Moved all 6 `.claude/agents/*` → `agents/` via `git mv` (renames, history preserved); `.claude/` removed.
- [x] Added `.claude-plugin/plugin.json` (name/version/description/author/repo; component keys omitted → auto-discovery kept)
      and `.claude-plugin/marketplace.json` (name + owner + one plugin `source: "./"`).
- [x] Schema verified against LIVE docs first (Claude Code v2.1.195); both pass `claude plugin validate --strict`.
- [x] Reversible real install proved all 6 agents discovered, then reverted — user's Claude config untouched.

**Architect verification:** git shows 6 renames; `.claude/` gone; manifests valid JSON with required fields;
the two `.claude/agents/` refs in code (`orchestrate.py:11`, `indeed.py:9`) are **docstrings only — non-functional**.
**Correct.**

**Note:** ~597 always-on tokens added per session by bundling 6 agents — inherent to the design, not a defect.
**Carry to Step 7 (docs):** 8 stale `.claude/agents/` doc references remain in `RUNBOOK.md`, `SPEC.md`,
`README.md`, `orchestrate.py`, `indeed.py` — update to `agents/`.

---

## Step 5 — commands (triggers) + onboarding skill  ✅ DONE & APPROVED
- [x] `commands/alfred-setup.md` (loads onboarding skill), `alfred-status.md` (read-only doctor+summary).
- [x] `commands/alfred-run.md` — MAIN trigger (full RUNBOOK sequence, preflight-gated).
- [x] Per-agent triggers: `alfred-find / -research / -tailor / -track / -approve / -apply.md`.
- [x] `skills/alfred-onboarding/SKILL.md` — the interactive wizard (all 8 steps of §6).
- [x] All 9 commands: `disable-model-invocation: true` → **Claude can never auto-fire them** (esp. `apply`);
      only recognized frontmatter fields → passes `--strict`. Reversible install showed 10 skills + 6 agents.

**Architect verification (read the real files):**
- `alfred-apply.md` — preflight is a **hard STOP** (won't invoke the agent if preflight fails or `/pause`);
  dry_run/`/pause`/`email_paused`/caps/human-final-Submit/prior-Approve all enforced and "never bypass" stated. ✅
- `SKILL.md` — rule #1 is "secrets NEVER in chat and NEVER written by you" (getpass only); non-secret config
  collected conversationally; own-bot rationale baked in. ✅
- venv path consistent between wizard (`~/.alfred/.venv`) and commands (`${ALFRED_HOME:-$HOME/.alfred}/.venv`). ✅

**Carry to Step 7 (docs polish):** SKILL.md lines 33-34 hardcode `~/.alfred/.venv` — switch to the
`${ALFRED_HOME:-$HOME/.alfred}` variable form for custom-home users. Always-on cost now ~1,080 tok/session (inherent).

---

## Step 6 — MCP declaration (optional)  ✅ DONE & APPROVED
- [x] Added `.mcp.json` at plugin root: single `notion` server (`type: http`, `url: https://mcp.notion.com/mcp`).
- [x] Schema verified against live MCP docs first (remote server needs `type`+`url`; `url` without `type` is an error).
- [x] Browser omitted (Claude-in-Chrome is built-in, not a declarable server). `plugin.json` untouched (auto-discovered).

**Architect verification:** valid JSON; only the Notion connector; **zero credential fields** (no token/key/secret/
password/bearer/authorization) — OAuth stays per-user via `/mcp`. Passes `--strict`; install showed `MCP servers (1): notion`. **Correct.**

---

## Step 7 — docs  ✅ DONE & APPROVED
- [x] `README.md` — Setup now shows `/plugin marketplace add` → `install` → `/alfred-setup`; Running shows
      the main + 6 per-stage commands; added §8 service-connection tables, §8b own-bot note, updated repo tree.
- [x] `RUNBOOK.md` — added the paths-resolve-under-`~/.alfred` note (ALFRED_HOME override + bare-clone
      fallback); sequence itself unchanged.
- [x] All 8 stale `.claude/agents/` refs → `agents/` (RUNBOOK ×1, SPEC ×3, README ×2, orchestrate.py docstring ×1, indeed.py comment ×1).
- [x] `SKILL.md` lines 33-34 → `${ALFRED_HOME:-$HOME/.alfred}/.venv` (no more hardcoded path).

**Architect verification:** grep confirms no `.claude/agents/` left in code/user-docs; venv now variable-form;
README setup flow matches the built plugin (install → wizard → secrets-via-CLI → own-bot). No code behavior changed. **Correct.**

---

## Step 8 — end-to-end acceptance (simulated fresh install)  ✅ DONE & APPROVED
- [x] Fresh-install onboarding on a throwaway `ALFRED_HOME`: init → set-secret ×4 (fake) → detect-chat-id
      → parse-resume → fill configs → `doctor` READY.
- [x] `/alfred-run` pipeline (preflight + all 6 stage harnesses) ran green under `dry_run: true`.
- [x] Send chokepoints proven closed (SMTP/IMAP/Telegram patched to explode — never fired).
- [x] `/alfred-apply` hard-STOP on `/pause` proven (preflight exit 1 → agent never invoked).

**Architect independent verification (own runs, not the summary):**
- paused preflight → exit 1; unpaused → exit 0. ✅
- `email_send.send(dry_run=True)` returned `DRY_RUN` with `_smtp_send` patched to raise — SMTP never reached;
  `send()` **defaults to dry_run=True**. ✅
- real `~/.alfred` does not exist — untouched. ✅

---

# 🎉 BUILD COMPLETE — Steps 1–8 all done & approved. Plugin is feature-complete and passes `--strict`.
Everything sits **uncommitted** on branch `plugin-setup`, per the review-first rule. Next decision: how to land it.

---

## Guardrails (unchanged, never violate)
Truthful tailoring · format lock · mandatory "what I changed" note · Telegram approve before any send ·
human final click on ban-prone portals · `dry_run` blocks real sends · `/pause` halts the application
agent · secrets never in git and never in chat.
