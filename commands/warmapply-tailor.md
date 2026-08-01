---
description: Run ONLY the resume-cover-letter stage — truthfully tailor resume/cover letter/email for above-threshold jobs. No sends.
disable-model-invocation: true
---

# /warmapply-tailor — resume-cover-letter only

Run just the tailoring stage for the surviving above-threshold jobs.

1. **Preflight** — run `${WARMAPPLY_HOME:-$HOME/.warmapply}/.venv/bin/python
   ${CLAUDE_PLUGIN_ROOT}/scripts/orchestrate.py --preflight` (fall back to `python3`). If it exits
   non-zero (missing config/resume, or **/pause** set), STOP and report.
2. **Invoke** the `warmapply:resume-cover-letter` subagent → per job: a tailored `.docx` + `.pdf`, a
   matching cover letter, a short outreach email, and the mandatory **"what I changed"** note. Written
   to `output/` and merged into the canonical job object, same as a full run.
3. Report which jobs were tailored and confirm each has a "what I changed" note.

**Guardrails:** truthful tailoring only — edit the summary and bullet emphasis, never invent experience
and never change the resume format. Tailoring produces files but sends nothing. Honor **/pause** and
keep **dry_run** state intact. (DOCX→PDF needs LibreOffice; if `soffice` is missing, note it — the
`.docx` still tailors.)
