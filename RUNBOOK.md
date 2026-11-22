# Alfred — Runbook

What the main session executes for **"run Alfred"** / `/alfred:alfred-run`. Keep `dry_run: true`
in `config/search.yaml` until you have watched a full pass.

**Paths.** Everything below is relative to the Alfred home (`$ALFRED_HOME`, else `~/.alfred`, else
the repo root). career-ops's code is `vendor/career-ops/`; its user files (`cv.md`,
`config/profile.yml`, `portals.yml`, `modes/_profile.md`, `data/applications.md`, `reports/`,
`output/`) live in the home itself, so Alfred and career-ops share one folder. Every career-ops
`node` script runs from `vendor/career-ops` with `CAREER_OPS_ROOT=$ALFRED_HOME`.

## Preconditions

`scripts/orchestrate.py --preflight` — `config/search.yaml`, `config/profile.yaml`, `cv.md`
present; reports dry_run and /pause. `scripts/careerops_bridge.py status` — career-ops installed,
Node 22.13+. Either fails → stop.

## The sequence

| # | Stage | Agent | Cost | Writes |
|---|---|---|---|---|
| 0 | Apply earlier approvals | `application-agent` | browser | tracker → Applied |
| 1 | **Find** | `job-finder` | zero-token first (API/RSS + `careerops_scan`), then Aside | `data/finder_output.json` |
| 2 | **Verify** — is the job real? | `job-verifier` | zero-token (career-ops scripts) | `data/verified_jobs.json`, `data/verify_dropped.json` |
| 3 | **Evaluate** | `job-evaluator` | triage (cheap) → full A–H only for passes | `reports/*.md`, tracker row `Evaluated`, `data/evaluation_output.json` |
| 4 | **Contacts** | `contact-finder` | small | contact fields |
| 5 | **CV + fact gate** | `cv-tailor` | medium | `output/*.pdf`, `data/tailor_output.json`, review list |
| 6 | **Review** — you decide | you (`/alfred:alfred-approve`, `alfred review`) | none | `data/job_decisions.json`, `data/approved_queue.json` |
| 7 | **Apply** | `application-agent` | browser | tracker → Applied, follow-up seeded |
| 8 | **Report** | `orchestrate.py --summary` | none | — |

Only jobs with score ≥ `min_score` (default **4.0**, career-ops's own line) reach stages 4–6.
Lower ones stay in the tracker as `Evaluated` with their report.

## After you apply (any time)

- `/alfred:alfred-tracker` — status overview, update a status (`set-status.mjs`).
- `/alfred:alfred-followup` — who is due a follow-up, reply classification, outcomes.
- `/alfred:alfred-interview` — prep, plan, practice, debrief, red flags.
- `/alfred:alfred-offer` — offer walk-through, comparison, negotiation points.
- `/alfred:alfred-learn` — rejection patterns, calibration, skill gaps, adjacent titles.
- `/alfred:alfred-mode <mode>` — any other career-ops mode.

## Canonical job object (the data contract between agents)

```
# job-finder
job_id, source, title, company, company_domain, location, url, posted_date, easy_apply,
description_snippet, found_at
# job-verifier
employer_url, verification {status: live|unconfirmed, reason, employer_check}, repost
# job-evaluator (career-ops)
triage, score ("4.3/5"), recommendation, legitimacy, report, tracker_num, needs_confirmation
# contact-finder
contact_email, recipient_name, email_source, email_confidence, verified_mailbox
# cv-tailor
cv_pdf, cv_html, fact_check (pass|warn|block), fact_warnings, output_dir, email_staged
# application-agent
applied_date, apply_result {status, confirmation, final_url}
```

`scripts/orchestrate.py :: merge_job` assembles it; any missing key is null.

## Safety recap

`dry_run` blocks every submit and send · `/pause` (`alfred pause`) halts the application agent ·
daily caps and pacing limit volume · nothing is applied without your approve, and no email without
its own clear · the fact gate blocks invented CV claims · Aside never solves a CAPTCHA or logs in ·
an application counts as submitted only with the site's confirmation.
