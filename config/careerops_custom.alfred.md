<!-- ALFRED HOUSE RULES START — written by `alfred careerops-house-rules`; edit outside these markers -->
## Alfred house rules (career-ops runs inside Alfred)

These are procedural rules for every career-ops mode when Alfred calls it. They
never add facts about the candidate.

1. **No cover letters.** Do not write a `## Cover Letter Draft` section in reports,
   do not offer the cover-letter sub-flow after a PDF, and do not run `cover`.
   Alfred applies with the tailored CV and, where a contact exists, a short email.
2. **Browser = Aside.** Wherever a mode says Playwright MCP, `browser_navigate`,
   `browser_snapshot` or "a Playwright browser this project launches" for reading a
   page or a form, use Aside instead (`aside exec "<task>"`, or the `mcp__aside__exec`
   tool; run `aside guide` once first). Aside drives the user's own signed-in
   browser. Never use Playwright MCP, the Claude browser extension, or a built-in
   browser pane. Node scripts that use the Playwright *library* headless
   (`generate-pdf.mjs`, `check-liveness.mjs`, `browser-extract.mjs`) still run.
3. **LinkedIn / Indeed / Wellfound pages** are read through Aside only, one attempt
   per posting (the LinkedIn JD loading guard still applies).
4. **Unattended inside Alfred.** When Alfred runs a mode as part of a pipeline stage,
   follow `modes/_shared.md` → Unattended runs: never ask, never wait, return
   `needs_confirmation` lines. Alfred shows them to the user at the review step.
5. **Submitting is Alfred's job, not career-ops's.** career-ops modes still stop
   before Submit. Alfred's application agent submits only jobs the user approved in
   Alfred's review step (`data/approved_queue.json`).
6. **Tracker writes** go through `merge-tracker.mjs` and `set-status.mjs` as usual.
   Alfred has no Notion and no Telegram; never mention either.
7. **No community asks, no update prompts** inside Alfred runs.
<!-- ALFRED HOUSE RULES END -->
