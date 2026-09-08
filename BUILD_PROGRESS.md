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
- [x] Browser omitted from `plugin.json` on purpose: agents discover a browser by capability at run time (host browser → Playwright MCP → other browser MCP → honest skip), so there is nothing vendor-specific to declare.

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

## Step 9 — fix: the email preview card never arrived after Approve  ✅

**Symptom:** tap Approve on a job with a recruiter email → Notion flips to "Approved" correctly, then
nothing. The second card (📧 Send / ✏️ Edit / 🚫 Cancel) never comes, so the email can never be sent.

**Cause:** the second gate was prose executed mid-run ("a tap on Approve is followed immediately by a
second card"), but a tap and the card that prompted it are almost never in the same run — the run
sends the card and ends, the user taps later, a later run reconciles it from the saved offset. That
reconcile path only updated Notion and enqueued. And even if it had wanted to send the preview, it
could not: the email body, subject and attachment paths lived only in the turn that built them, so
nothing was left on disk to build a preview from. Silent, and permanent.

- [x] `stage_email_draft(job)` — writes to/subject/body/attachments + a job snapshot BEFORE the review
      card goes out, read from `output/<company>_<role>/email_message.txt` and the built PDFs. Never
      overwrites a draft the user already edited.
- [x] `send_review_card` stages it automatically, so no agent has to remember; staging failures are
      non-fatal.
- [x] `record_job_decision` / `job_decision` — approve/skip recorded durably, because
      `approved_queue.json` gets drained and cannot answer "was this approved?".
- [x] `mark_preview_sent` inside `send_email_preview_card`, and `pending_email_previews()` — the
      stall is now a list you can read instead of silence.
- [x] **`scripts/approval_poll.py`** — the tap → next-card step in code, not instructions: approve →
      enqueue + preview card, edit → prompt + capture + re-preview, send/cancel → recorded, plus a
      `--sweep` that heals jobs already stuck and `--status` that names them. Prints JSON for Notion;
      exits non-zero if any card failed.
- [x] `poll_responses(timeout=…)` — real long-poll, so a tap made during a run is caught in that run.
- [x] `scripts/dry_run_approval_poll.py` — 45 checks, incl. the cross-run regression itself. Telegram
      and SMTP both patched to explode; neither fires.
- [x] Docs updated: approval-gate, application-agent (never drop a queue entry while its email
      decision is still `None`), RUNBOOK, DAILY_RUN, /alfred-approve. Plugin → 1.5.0.

**Unchanged on purpose:** the poller never sends email and never touches Notion. The recruiter email
still goes only through the application agent, gated on a `"cleared"` decision, `dry_run`, `/pause`
and the daily caps.

---

## Step 10 — the always-on worker: Telegram works with the laptop off  ✅

Step 9 fixed *what* happens on a tap. This fixes *when*: a tap only did something while a run
happened to be polling, so approving at midnight meant waiting for tomorrow — and Telegram
drops un-fetched updates after 24h, so a slow week could lose the tap entirely.

- [x] **`scripts/email_gate.py`** — the single place a `"cleared"` decision becomes a sent
      email, shared by the worker and the application agent so one send-once record
      (`data/email_sent.json`) covers both. Guardrails in order: already-sent → cleared-only →
      `/pause` → bounce throttle → daily cap → `dry_run` → send → notify. An unreadable
      `search.yaml` reads as `dry_run: true`; a failing send gives up after 3 attempts instead
      of re-notifying on every cycle.
- [x] **`scripts/alfred_worker.py`** — long-poll loop, exponential backoff, SIGTERM handled so
      a container restart never lands mid-send. Sweeps missing preview cards AND cleared-unsent
      emails on every cycle, so whatever it missed while down is picked up from disk.
- [x] `approval_poll.py --send` — the same behavior for a one-shot/cron run; a plain poll is
      still send-free.
- [x] **Portable drafts** — attachment paths stored relative to the Alfred home, so a draft
      staged on the laptop resolves on the worker host. `rsync` is the whole sync story.
- [x] `daily_caps` now resolves its path at call time; the module-level default argument bound
      it at import, so the cap guardrail could not be tested against a temp store — and a dry
      run was writing to the real counts file.
- [x] **`deploy/`** — Dockerfile, systemd unit, and a README covering the three hosting
      options, the sync step, and what the worker deliberately cannot do.
- [x] `scripts/dry_run_worker.py` — 44 checks with `_smtp_send` patched to raise, so any check
      that passes while SMTP fires is a failure. Includes a full laptop-off round trip.

**The honest boundary, stated everywhere:** the worker is the EMAIL half. Portal applications
need the user's signed-in browser and still happen on their machine; Notion catches up on the
next laptop run. Plugin → 1.6.0.

---

## Step 11 — backfill: emailing the jobs already prepared  ✅

Steps 9 and 10 fixed the flow going forward. They did nothing for the jobs already sitting in
Notion, tailored and reviewed, whose email was never asked about — and those are the ones the
user wants to send today.

The blocker: a job's recruiter address and tailored file paths only ever lived in the agent turn
that built them. Nothing local kept them. But **Notion did** — HR Email, Job ID, Resume File,
Cover Letter File, Status — so a Notion row is a complete recovery source.

- [x] `notion_schema.job_from_row()` / `jobs_from_rows()` — the inverse of `row_properties`, in the
      module that already owns the property names so the mapping cannot drift. Handles both the
      query and fetch response shapes; drops rows with no Job ID rather than half-staging them.
- [x] `approval_poll.py --stage` now accepts raw Notion rows as well as job objects, and **records
      the approval for a row at "Approved"** — the missing piece, since a job approved before the
      local decision store existed reads as never-approved and never qualifies for its card.
- [x] `/alfred-backfill` — query Notion → stage → `--sweep` → report, including an honest per-job
      account of what staged nothing and why.
- [x] `scripts/dry_run_backfill.py` — 32 checks: full round trip, the backlog case, re-run safety
      (never clobbers a user's edit, never duplicates a card), and the rows that must NOT produce
      an email (portal-only, Skipped).

**Guardrails held, deliberately:** `caps.emails_per_day` still meters a backlog — thirty recovered
jobs are not thirty emails today. No address in Notion stays portal-only; a recruiter address is
never invented to make a job emailable.

---

## Guardrails (unchanged, never violate)
Truthful tailoring · format lock · mandatory "what I changed" note · Telegram approve before any send ·
human final click on ban-prone portals · `dry_run` blocks real sends · `/pause` halts the application
agent · secrets never in git and never in chat.
