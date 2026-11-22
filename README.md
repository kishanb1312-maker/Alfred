# Alfred

A **Claude-Code-native** job-application assistant, now running on the
[career-ops](https://github.com/career-ops-hq/career-ops) engine.

Alfred finds jobs (its own boards, career-ops's 150+ ATS scanner, and LinkedIn / Indeed /
Wellfound through your signed-in browser), drops postings that are closed or look like ghost jobs,
scores every real one with career-ops's A–H report, tailors a fact-checked CV, keeps everything in
a local tracker, and applies through **Aside** — but only to jobs **you approve**.

> Built for a friends circle. No Claude API key and no per-token bill: your own Claude Code
> session is the brain.

## How a run works

1. **Find** — zero-token sources first (RemoteOK, We Work Remotely, Jobspresso, Greenhouse/Lever,
   and career-ops `scan.mjs` across Greenhouse, Lever, Ashby, Workday, SmartRecruiters, Keka,
   Darwinbox, Zoho Recruit and 150+ more), then LinkedIn Easy Apply, LinkedIn "we're hiring"
   posts, Indeed and Wellfound through Aside.
2. **Verify** — aggregator listings are confirmed on the employer's own ATS; postings are checked
   live; roles re-listed again and again are flagged.
3. **Evaluate** — career-ops triage, then the full A–H report (role summary, CV match with
   requirement weights, level strategy, pay research, customization plan, interview plan, posting
   legitimacy) with a **1–5 score**. Below 4.0 is not recommended.
4. **Contacts** — Alfred's verified email waterfall (careers page → Hunter/Apollo → recruiter via
   Aside → one MX-checked guess).
5. **CV** — career-ops tailors `cv.md` into an ATS-friendly PDF and its fact gate blocks any claim
   that is not in your own files. No cover letters.
6. **You review** — `/alfred:alfred-approve` (or `alfred review` / `alfred approve <id>` in a
   terminal). Approving a job approves the application; its cold email needs its own yes.
7. **Apply** — Aside fills the form in your own browser (LinkedIn Easy Apply and every ATS
   career-ops supports) and submits it when `apply.auto_submit: true`. Cleared emails go out
   through your Gmail. Marked **Applied** only with the site's confirmation.

Then: follow-ups, reply classification, interview prep and practice, offer review, and learning
from results — all career-ops modes, run from Alfred (see [`RUNBOOK.md`](RUNBOOK.md)).

## Setup

```
/plugin marketplace add kishanb1312-maker/Alfred
/plugin install alfred@alfred
/alfred:alfred-setup
```

You need **Python 3.8+**, **Node.js 22.13+**, **git**, and **[Aside](https://aside.com)** for the
browser parts. The wizard:

- builds the venv (`alfred bootstrap`);
- installs career-ops at a pinned commit, its npm packages and a headless Chromium
  (`alfred careerops-install`);
- turns your resume `.docx` into `cv.md` (`alfred cv-from-docx`) — reorganized, never invented;
- writes the career-ops profile and portal list (`alfred careerops-onboard`) and personalizes
  the archetypes the scores are measured against;
- collects your search and screening answers in chat;
- has you enter Gmail secrets in **your own terminal** with `alfred set-secret` (never in chat);
- runs `alfred doctor` until it is green.

Your data lives in `~/.alfred/` (or `$ALFRED_HOME`). career-ops's code lives in
`~/.alfred/vendor/career-ops`; its user files (`cv.md`, `config/profile.yml`, `portals.yml`,
`data/applications.md`, `reports/`) sit in the same home, so both share one folder.

## Commands

| Command | Does |
|---|---|
| `/alfred:alfred-run` | the whole pipeline, up to your review |
| `/alfred:alfred-find` · `-verify` · `-evaluate` · `-cv` | one stage at a time |
| `/alfred:alfred-approve` | review and decide |
| `/alfred:alfred-apply` | apply to approved jobs |
| `/alfred:alfred-tracker` | where every application stands |
| `/alfred:alfred-followup` | follow-ups, replies, outcomes |
| `/alfred:alfred-interview` | prep, plan, practice, debrief, red flags |
| `/alfred:alfred-offer` | offer walk-through, comparison, negotiation |
| `/alfred:alfred-learn` | patterns, calibration, skill gaps, titles |
| `/alfred:alfred-mode <mode>` | any other career-ops mode |
| `/alfred:alfred-status` | doctor + tracker funnel + what is waiting |
| `/alfred:alfred-setup` | first-run wizard |

Terminal: `alfred review`, `alfred approve <id> [--email]`, `alfred skip <id>`, `alfred queue`,
`alfred pause`, `alfred resume`, `alfred doctor`.

## Safety

- **dry_run** (`config/search.yaml`) — everything is prepared, nothing is submitted or sent.
- **Your approval** is required for every application, and separately for every cold email.
- **Truthful CVs** — career-ops's fact gate blocks numbers and claims not in `cv.md`.
- **Aside never logs in, never solves a CAPTCHA, never auto-DMs** on LinkedIn.
- **Caps and pacing** limit how many applications and emails go out per day.
- **No secrets in git** — `.env`, `data/`, `cv.md`, the profiles, reports and `vendor/` are ignored.

## Tests

```bash
./.venv/bin/python scripts/run_tests.py
```

Runs every offline suite (no network, no real sends, no real history writes) and, when career-ops
is installed, its own self-tests for the fact gate and the repost detector.

## Credits

The evaluation, scanning, liveness, CV, fact-check, tracker, follow-up, interview, offer and
pattern features are [career-ops](https://github.com/career-ops-hq/career-ops) by Santiago
Fernández de Valderrama and contributors (MIT). Alfred calls it unmodified, from a pinned commit.
