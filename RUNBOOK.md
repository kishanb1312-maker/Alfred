# Alfred — Runbook

This is what the **main Claude Code session** executes when you say **"run Alfred"** (or run
`/alfred-run`). It sequences the six worker subagents in `agents/`. Keep `dry_run: true` in your
search config until you've watched a full pass.

> **Paths:** config, resume, and runtime data (`config/*.yaml`, `data/`, `output/`) now resolve under
> **`~/.alfred/`** (override with `ALFRED_HOME`); a bare clone falls back to the repo root. The
> sequence itself is unchanged.

## Preconditions
Run `python scripts/orchestrate.py --preflight` first. It confirms `config/search.yaml`,
`config/profile.yaml`, and a master resume in `data/` exist, and reports whether **dry_run** is on
and whether **/pause** (`data/paused.flag`) is set. If paused, stop.

## The sequence

0. **Preflight** — `scripts/orchestrate.py --preflight`. Abort on missing configs/resume or if paused.
1. **Reconcile** — invoke **approval-gate** to poll Telegram for taps made since the last run;
   apply Approvals (→ **application-agent**), record Skips. This clears the backlog first.
2. **Find** — invoke **job-finder** → fresh, de-duped jobs (respects sources + caps).
3. **Research** — invoke **company-research** per job → company analysis + verified email (waterfall)
   + match score. Drop jobs below `match_threshold`.
4. **Tailor** — invoke **resume-cover-letter** per surviving job → tailored .docx/.pdf + cover letter
   + email text + `what_i_changed.md`. Merge into the canonical job object (below).
5. **Track** — invoke **tracker** → create/​update a Notion row per job at Status "Ready for Review".
6. **Approve** — invoke **approval-gate** → send a Telegram card per job; poll briefly for immediate
   taps. Un-tapped jobs wait for a later run.
7. **Apply** — invoke **application-agent** → process `data/approved_queue.json` (respecting /pause,
   dry_run, daily caps): send verified emails; fill portal forms and hand the final Submit to you on
   LinkedIn/Workday. Mark Applied in Notion + `applied_history`.
8. **Report** — `scripts/orchestrate.py --summary` → counts + caps remaining + what needs you.

`/loop` may repeat this while the session stays open; otherwise run it whenever you're job-hunting.

## Canonical job object (the data contract between agents)

Every agent reads/writes this shape so hand-offs never drift:

    {
      # from job-finder
      "job_id", "source", "title", "company", "company_domain",
      "location", "url", "posted_date", "easy_apply", "description_snippet",
      # added by company-research
      "company_analysis": {summary, industry, size, tech_stack, values_culture,
                           recent_signal, website},
      "email": {address, recipient_name, confidence, source, verified, is_personal},
      "match": {score, rationale, meets_threshold},
      "channel": "portal" | "email",
      # added by resume-cover-letter
      "files": {resume, cover_letter},         # local paths in output/
      "what_i_changed": "...",                  # from what_i_changed.md
      # added by tracker
      "notion_url": "...",
      # updated by application-agent
      "applied_date", "reply", "follow_up_sent"
    }

## Safety recap
dry_run blocks all real sends/submits · /pause halts the application-agent · daily caps limit volume
· the human makes the final Submit click on ban-prone portals · nothing acts without a Telegram Approve.
