---
description: Run ONLY CV tailoring — career-ops tailored CV PDF from cv.md, the fact gate that blocks invented claims, and a short email when a contact exists. Puts passing jobs on the review list. No cover letters, no sends.
disable-model-invocation: true
---

# /alfred-cv — tailored CV + fact check

Run Alfred's scripts with `${ALFRED_HOME:-$HOME/.alfred}/.venv/bin/python` (fall back to `python3`); scripts live in
`${CLAUDE_PLUGIN_ROOT}/scripts/`. career-ops lives in `${ALFRED_HOME:-$HOME/.alfred}/vendor/career-ops`: run its `node` scripts from
there with `CAREER_OPS_ROOT=${ALFRED_HOME:-$HOME/.alfred}` exported, so it reads and writes Alfred's own files.

1. Needs `data/evaluation_output.json`. For one job: `/alfred:alfred-cv <report number>`.
2. Invoke `alfred:cv-tailor`.
3. Report per job: CV path, fact-check verdict (pass / warn / block with the claims), email drafted
   or not. Then point to `/alfred:alfred-approve`.
