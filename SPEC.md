# WarmApply — Build Spec (v2, Claude-Code-native)

> Project & repo name: **WarmApply** (`warmapply`).

> Status: **Design locked. Claude-Code-native architecture.** Ready to build agent-by-agent.
> The only things provided at build/runtime are the user's resume + personal inputs (Section 10).

---

## 1. Goal

An AI agent system that finds jobs, researches the company, tailors the resume &
cover letter **truthfully** (never changing format/projects), tracks everything in
Notion, and applies — either through job portals or by **direct email to a recruiter** —
only after the user approves each one via **Telegram**.

Built as **multiple sub-agents** (not one monolithic agent). Code lives on GitHub.
It is a **friends-circle tool, not a product** — minimal spend, each user runs it themselves.

---

## 2. Runtime architecture — Claude-Code-native (no Claude API)

**The Claude Code session IS the brain.** There is **no Claude API key and no per-token cost.**
Each friend clones the GitHub repo and runs it inside **their own Claude Code** session using
**their own Claude subscription**.

- **Sub-agents = real Claude Code subagent files** (`agents/*.md` with
  `name` / `description` / `tools` frontmatter). The session's Claude orchestrates them.
- **External actions** — Notion, browser/Easy Apply, Telegram, email — run through **MCP tools**
  (already available in Claude Code).
- **Deterministic helpers** — DOCX→PDF conversion, email verification, applied-history,
  match-score math — run as **Python scripts via Bash**.
- **Run mode: manual.** You open a Claude Code session and kick it off. Optionally `/loop`
  to repeat while the session stays open.
- **Accepted trade-off:** it only runs **while a Claude Code session is open** — it can't hunt
  jobs while you're asleep. Fine for a run-it-when-you're-job-hunting tool, and it keeps cost at zero.

```
CLAUDE CODE SESSION (the orchestrator / brain — you kick it off)
├── 1. Job Finder subagent          → find + de-dupe jobs from multiple sources
├── 2. Company Research subagent    → analyze company + email waterfall + match score
├── 3. Resume + Cover Letter subagent → tailor TEXT ONLY, truthfully; .docx + .pdf + email msg
├── 4. Tracker subagent             → write full record to Notion (MCP)
├── 5. Approval Gate (Telegram MCP) → send review card; wait for Approve/Skip
└── 6. Application subagent         → apply via portal OR send email; update status
     (deterministic helpers run as Python scripts via Bash)
```

---

## 3. End-to-end flow

1. **User opens a Claude Code session** and starts the run (manual; `/loop` optional).
2. **Job Finder** pulls listings for target roles/locations, de-dupes against applied-history.
3. **Company Research** analyzes the company, runs the **email waterfall**, computes a **match score**.
   - Jobs **below the match threshold are dropped** (70%).
4. **Resume + Cover Letter** tailors text only (guardrails below), outputs tailored
   `.docx` + `.pdf` + cover letter + short email message + a **"what I changed" note**.
5. **Tracker** writes the full record to **Notion**.
6. **Telegram approval card** is sent: summary + match% + "what I changed" + attached
   resume.pdf + coverletter.pdf + (if email path) recipient + confidence.
   - Buttons: **✅ Approve** / **⏭️ Skip**  (Edit = later version).
7. On **Approve** → job enters a **paced queue** (human-like gaps).
8. **Application Agent** acts:
   - **Easy Apply / friendly boards** → fill + submit.
   - **Fragile ATS (Workday, etc.)** → fill form, **user gives the final click**.
   - **Direct email path** → send email with attachments.
9. Notion status → **Applied ✅** + Telegram confirmation.

---

## 4. Two apply channels

### A. Job portal
- Priority target: **LinkedIn Easy Apply** + API-friendly boards.
- Fragile ATS: agent fills, human does the final submit click (ban-safety).

### B. Direct email (runs alongside)
- **Email discovery waterfall — Option B (prefer-personal + generic fallback):**
  1. Company career/contact page → `careers@`, `jobs@`, `hr@`, `recruiting@`
  2. Email-finder API (Hunter → Apollo → RocketReach) → person-specific + confidence
  3. LinkedIn recruiter profile → get NAME → resolve via finder API
  4. Pattern guess (`first.last@`, `f.last@`, …) → **must pass verification**
  5. None found → mark "portal-only"
- **Prefer-personal:** still try the finder even when a generic inbox exists; use the
  personal email if found, fall back to generic.
- **Verify at EVERY step** before accepting an address (no unverified sends).
- **Confidence thresholds:** ≥85% send normally · 60–85% send but flag in card · <60% skip.
- Record **`Email Source`** in Notion (`career-page` / `hunter` / `linkedin` / `pattern` / `none`).

---

## 5. Guardrails (non-negotiable)

- 🛡️ **Truthfulness:** the Resume Agent may only **re-emphasize experience that already
  exists** in the master resume. It must **NEVER invent skills, experience, or claims.**
  (This is the #1 failure of AIHawk — directly avoided here.)
- 🛡️ **Format lock:** projects, structure, layout, and design are never changed. Only the
  **summary/objective** and **bullet emphasis/keywords** are edited.
- 🛡️ **"What I changed" note** is mandatory on every application, shown in the Telegram card.
- 🛡️ **Human confirms:** nothing is submitted or emailed without an explicit Telegram Approve.
- 🛡️ **Risky final click stays human** on fragile/ban-prone portals (LinkedIn, Workday).

---

## 6. Included improvements (all approved)

1. **Screening-question knowledge base** — YAML profile of answers (years of X, work auth,
   salary expectation, etc.) so Easy Apply auto-fill is correct, not guessed. **v1 must-have.**
2. **Match-score threshold filter** — skip jobs below 70% to protect application quality.
3. **Never double-apply** — applied-history store keyed by job ID + company across all sources.
4. **Personal data OUT of the public GitHub repo** — resume, tokens, and personal config live
   in **gitignored** files. Repo ships code + `.env.example` only.
5. **Dry-run mode** — flag that runs the full pipeline but never submits/sends. Use on day one.
6. **Response analytics** — leverage Notion's `Email Source` / `Channel` / `Status` fields to
   see which methods & channels actually get replies, and double down.
7. **Kill switch** — Telegram `/pause` command halts all sending immediately.
8. **Follow-up email** (optional, later) — after N days of no reply, gated behind approval.

---

## 7. Tech stack

| Concern | Choice |
|---|---|
| Brain / AI | **Claude Code session** (user's own subscription) — **no API key, no per-token cost** |
| Orchestration | Session's Claude drives **Claude Code subagents** (`agents/*.md`) |
| External actions | **MCP tools** — Notion, browser (Easy Apply), Telegram, email/Zapier |
| Deterministic helpers | **Python scripts run via Bash** (DOCX→PDF, verify, history, scoring) |
| Browser automation | Browser MCP / Playwright as needed for Easy Apply + scraping |
| Resume | Master **DOCX** → tailor → convert to PDF via LibreOffice headless (`soffice`); keep both |
| Tracker | Notion (full archive, via MCP) |
| Approval/notifications | Telegram bot (inline buttons + file attachments) |
| Email finding | Hunter.io / Apollo API (choice at build time) |
| Email sending | Dedicated job-hunt Gmail (App Password) |
| Secrets/personal config | gitignored files on each user's machine; `.env.example` in repo |
| Run mode | **Manual** — open a session, kick off; `/loop` optional. No scheduler (that would need the API). |

---

## 8. Notion record — fields

Company · Company website · Role · Location · Job link · Match score · Channel
(portal/email) · HR name · HR email · Email confidence · Email source · Resume (file) ·
Cover letter (file) · "What I changed" note · Status (New → Ready for Review → Approved →
Applied / Skipped) · Timestamps · Reply/follow-up tracking.

---

## 9. Repo structure (planned)

```
warmapply/
├── .claude/
│   └── agents/                    # REAL Claude Code subagent files
│       ├── job-finder.md
│       ├── company-research.md    # email waterfall + match score
│       ├── resume-cover-letter.md # truthfulness core
│       ├── tracker.md             # Notion
│       └── application-agent.md    # portal + email send
├── scripts/                       # deterministic Python helpers (run via Bash)
│   ├── docx_to_pdf.py
│   ├── email_verify.py
│   ├── applied_history.py
│   └── match_score.py
├── config/
│   ├── profile.example.yaml       # screening-question answers (real one gitignored)
│   └── search.example.yaml        # roles, locations, sources, caps
├── data/                          # master resume, applied-history (gitignored)
├── SPEC.md
├── .env.example                   # shows required tokens, no secrets
├── .gitignore                     # excludes .env, data/, config/*.yaml (real)
├── requirements.txt
└── README.md                      # how a friend clones + runs it in Claude Code
```

---

## 10. Confirmed values + what's still provided at build/runtime

**✅ Locked:**
- Focus: **IT jobs**
- Daily cap: **20–25 applies/day**
- Match threshold: **70%**
- Confidence thresholds: **≥85 send · 60–85 flag · <60 skip**
- Email waterfall: **Option B** (prefer-personal + generic fallback, verify every step)
- Apply mode: **prepare → Telegram approve → apply** (risky final click stays human)
- Architecture: **Claude-Code-native**, run **manually**, subagents as `agents/*.md`

**🕒 Provide at build/runtime (per user, kept out of the repo):**
1. **Target roles / job titles** (specific IT roles)
2. **Target locations** (remote / countries / cities)
3. **Seniority level(s)**
4. **Companies to blacklist** (e.g. current employer)
5. **Email-finder API** — Hunter.io (free tier) or Apollo → API key
6. **Dedicated job-hunt Gmail** + App Password
7. **Telegram bot** — token + chat ID (create via `@BotFather`, ~2 min)
8. **Notion** — workspace + integration (already connected here)
9. **GitHub** — repo where the code lives
10. **LinkedIn** — normal login, used locally by the browser, never committed
11. **Master resume as DOCX** — single column, no text boxes/layout tables, standard fonts
    (Calibri/Arial/Georgia), real headings. **Most important file.**
12. *(Optional)* a cover-letter sample/tone
13. **Screening-question answers** (`profile.yaml`): years per key skill, work authorization/visa,
    notice period/availability, salary expectation, relocate/remote preference, phone,
    location, LinkedIn/portfolio URL.

> **Absolute minimum to start building:** the DOCX resume + target roles/locations +
> which email-finder API. Account setups (Telegram, Gmail, keys) can be done step-by-step
> during the build.

---

## 11. Build workflow — two-session (architect ↔ builder)

```
THIS SESSION (architect)            YOUR BUILDER SESSION (Claude = builder, same MCP tools)
────────────────────────           ──────────────────────────────────────────────────────
For each sub-agent, I produce:
  1. a .md file (full definition)  ──►  you paste it + the prompt
  2. a short kick-off prompt            builder creates code/files, tests, reports
                                   ◄──  you bring the response back to me
I review → decide → refine or
move to the next sub-agent
```

- **This session = planner/reviewer.** The other session = the **hands** that write and run code.
- The `.md` is a **real Claude Code subagent file** (native, self-contained — the builder starts
  cold, so each `.md` carries all context it needs).
- **Confirmed:** the builder session has the **same MCP tools** connected, so it can test each
  agent live.
- Short prompt example:
  > "Read the attached `job-finder.md`. Build it as described: create the file(s), implement the
  > job-search logic for LinkedIn Easy Apply + Adzuna, and show me the code + a dry-run output.
  > Ask me if anything is unclear."

### Build order (one by one, dependencies first)
1. **Project scaffold** — repo structure, `.gitignore`, `.env.example`, config files
2. **Job Finder Agent**
3. **Company Research Agent** (email waterfall + match score)
4. **Resume + Cover Letter Agent** (truthfulness core)
5. **Tracker** (Notion)
6. **Approval Gate** (Telegram)
7. **Application Agent** (portal + email send)
8. **Orchestrator** (ties them together)

---

## 12. Reference / lessons from market research

- **LinkedIn_AIHawk** (Python + Selenium + GPT) — same modular architecture; **its top
  failure was fabricating resume content** → our truthfulness guardrail exists to prevent this.
- **JobCopilot** — same "review before applying" human-in-the-loop model we adopted.
- Community consensus: mass auto-apply on LinkedIn **risks bans** → low volume + human-in-loop
  + human-like pacing + human final click.
- ATS + PDF: a **text-based** PDF (not an image, single-column) is ATS-safe. Keep both DOCX and
  PDF and upload whichever the portal prefers.

---

**Next step:** bring the resume + inputs (Section 10), then say **"start with the scaffold"** —
I produce the first `.md` + kick-off prompt for your builder session.
