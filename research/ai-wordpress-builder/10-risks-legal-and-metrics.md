# 10 — Risks, Legal, Compliance & Metrics

---

## 1. Risk register

Scored: **P** = probability (1–5), **I** = impact (1–5), **S** = P×I.

### 🔴 Existential (S ≥ 16)

| # | Risk | P | I | S | Mitigation |
|---|---|---|---|---|---|
| R1 | **The compiler can't hit design fidelity with native blocks** — you're forced into a runtime plugin and become a worse Elementor | 3 | 5 | 15 | **The M0 spike exists solely to answer this in week 12.** Fallback: narrow the canvas's expressible design space. Never fall back to a runtime plugin — change the product instead. |
| R2 | **Generated output looks templated** — you fail the "not another ZipWP" test | 4 | 5 | **20** | Design-decision generation (not template retrieval), stage-6 critique loop, an eval harness measuring *layout variety across runs*, a large section library. Benchmark blind against competitors from week 14. |
| R3 | **Export-once-and-cancel** kills LTV | 4 | 4 | 16 | Round-trip sync in v1.5, annual plans, agency workspaces, per-project value. Track "exports per active account/month" from day one. |
| R4 | **Etch or Bricks ships AI generation** and arrives at your position with an existing audience | 3 | 5 | 15 | Speed. Own the *design-grade + non-developer* half they've declined to serve. Build community credibility now. |
| R5 | **Automattic extends Big Sky to self-hosted** | 3 | 5 | 15 | They will always be a hosting funnel with block-theme-only constraints and no agency workflow. Differentiate on design fidelity, multi-client workflow and BYOK. |

### 🟠 Serious (S 9–15)

| # | Risk | P | I | S | Mitigation |
|---|---|---|---|---|---|
| R6 | Security incident in the companion plugin across thousands of client sites | 2 | 5 | 10 | Pre-public-beta pen test, minimal endpoint surface, capability checks, signed payloads, a published disclosure policy, auto-update path |
| R7 | Section library under-scoped → beta slips 2–3 months | 4 | 3 | 12 | Staff it properly from week 15; treat it as critical path, not polish |
| R8 | AI inference cost outruns pricing | 3 | 4 | 12 | Model tiering, caching, soft caps, BYOK migration path, cost per generation as a tracked engineering metric |
| R9 | WordPress ecosystem instability (Automattic/WP Engine litigation, governance fights, plugin-directory politics) | 3 | 4 | 12 | You're a SaaS with file-based export — you don't depend on wordpress.org distribution. **This is an underrated structural advantage; keep it.** |
| R10 | Community rejects you as "AI slop for WordPress" | 3 | 4 | 12 | Technical honesty, published benchmarks, ship to sceptics first, never over-claim, admit weaknesses publicly |
| R11 | Key-person risk on the compiler engineer | 3 | 4 | 12 | Golden-file tests, documented IR spec, pair on the compiler from day one |
| R12 | Continued WordPress share decline (43.2% → 41.9% in six months) | 3 | 3 | 9 | Installed base is still enormous and *switching within it* is your market. Keep a headless/static export option in the v3 drawer as a hedge. |

### 🟡 Manageable (S ≤ 8)

Model provider outage (multi-provider routing) · trademark conflict (clear early) · font licensing
in the section library (audit) · stock image API terms (read them) · support load (hire before
public beta) · regional pricing arbitrage (accept it, it's cheaper than the lost TAM).

---

## 2. Legal & compliance

### 2.1 GPL and WordPress licensing — read this bit twice

- WordPress is **GPLv2+**. Anything that is a **derivative work** of WordPress — notably PHP that
  hooks into WordPress APIs, i.e. **your companion plugin and any exported theme PHP** — is
  generally required to be GPL-compatible under the widely-held ecosystem interpretation.
- **Your SaaS is not affected.** The canvas, the compiler service and the AI pipeline never run
  inside WordPress, are not derivative works, and can be fully proprietary. Elementor, Bricks and
  every commercial builder operate on exactly this basis: **GPL code, commercially licensed
  distribution and support.**
- **Practical position:** licence the companion plugin and the exported theme scaffolding as
  GPLv2+; keep the SaaS proprietary; sell access, updates and support, not the code. Get a lawyer
  who knows the WordPress ecosystem specifically to confirm — this is a well-trodden path and
  should cost you a few hours of counsel, not a research project.
- **Consequence you must accept:** users can legally redistribute the GPL parts. In practice this
  means nulled copies of the plugin will circulate. It doesn't matter — the plugin is worthless
  without the SaaS.

### 2.2 AI-specific

| Area | What you need |
|---|---|
| **Output ownership** | State plainly in the ToS: **the user owns the generated output.** Anything less is disqualifying for agencies selling client work. |
| **Training on user data** | Default **off**. Opt-in only, clearly worded. Agencies handle confidential client material. Getting this wrong once is unrecoverable. |
| **Provider terms** | Anthropic/OpenAI commercial terms; make sure your ToS passes through the necessary restrictions |
| **BYOK liability** | Explicit: the user is responsible for their key's usage, quota, and their provider's terms. You are responsible for storing it securely. |
| **AI image provenance** | Disclose the generator; pass through licence terms; consider C2PA metadata |
| **EU AI Act** | You're a limited-risk system at most. Transparency obligations (users know they're interacting with AI) are easy to meet. Document it once. |
| **Copy/plagiarism** | Generated marketing copy is low risk, but add a similarity check on long-form output and a ToS disclaimer |

### 2.3 Accessibility — a sales opportunity, not just a duty

The **European Accessibility Act** has applied since **June 2025**, pulling a wide class of
commercial digital services into WCAG-shaped obligations. Elementor monetises this via the paid
Ally add-on.

**Your move: make accessible output the default and free.** Semantic landmarks, correct heading
order, focus states, contrast enforced at the *token* level (so it's structurally impossible to
generate a failing palette), alt-text generated as part of the content stage, and an audit panel
in the editor.

Then market it: *"every site we generate passes WCAG AA contrast by construction."* That's a
procurement checkbox with a legal deadline behind it, and none of your AI-builder competitors can
say it.

### 2.4 Data protection
GDPR/UK-GDPR (your beachhead is heavily European): DPA, standard contractual clauses for
sub-processors (your model providers!), a published sub-processor list, data residency questions
answered, deletion that actually deletes, and a DPIA if you ever touch end-visitor data. Agencies
will ask for a DPA in month one. Have one ready.

---

## 3. Metrics

### North Star
> **Sites exported and launched per active account per month.**

Why this one: it captures value delivered (a real site shipped), frequency (their business is
repeat), and quality (a site that isn't good enough doesn't get launched). It resists the
vanity-metric failure mode of "time in app" — which, for a tool whose promise is *speed*, is
actively the wrong direction.

### Metric tree

```
                    SITES EXPORTED & LAUNCHED / ACTIVE ACCOUNT / MONTH
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        │                               │                               │
   ACTIVATION                     GENERATION QUALITY              RETENTION
        │                               │                               │
 · Signup → first gen            · Regens per section            · D7 / D30 / M3
   (target < 10 min)               (↓ = better; a proxy          · Monthly logo churn
 · Signup → first export           for first-draft quality)        (< 4%)
   (target < 45 min)             · Sections kept vs replaced     · Export → return
 · % reaching first export       · Eval harness score              within 30 days
   (target > 45%)                  vs competitor baseline          (THE metric for R3)
 · Onboarding drop-off by step   · Manual fixes needed post-      · Annual plan mix
                                   export (target: 0)            · Seat expansion rate
        │                               │                               │
        └───────────────────────────────┼───────────────────────────────┘
                                        │
                              QUALITY / TRUST GUARDRAILS
                    · Export success rate (> 95%)
                    · Compiled page Lighthouse perf & a11y (≥ 95)
                    · DOM depth & CSS bytes vs competitor benchmark
                    · Support tickets per active user (< 1.5/mo)
                    · Cost per generated site (managed tier)
```

### Leading indicators worth more than they look

| Metric | Why it matters |
|---|---|
| **Regenerations per section** | The purest available proxy for first-draft quality. If it climbs, your generation is getting worse regardless of what the demo feels like. |
| **Code-panel open rate** | If it's high, altitude 1 and 2 aren't good enough. If it's zero, you built the escape hatch for nobody (unlikely — but measure). |
| **Section-override rate** | How often users abandon a generated section entirely. Tells you which archetypes to rebuild. |
| **Export → return within 30 days** | The single best early warning for the export-and-churn death spiral. Watch it from your first ten exports. |
| **Time from export to *launch*** | If exports never become live sites, your output isn't good enough and no one is telling you. |

### Quarterly review questions
1. Is our blind-rated generation quality still ahead of ZipWP / Big Sky / Elementor AI? *(Re-run
   the benchmark. Every quarter. Don't assume.)*
2. Are exported sites getting launched, or dying in a downloads folder?
3. Has anyone shipped a native-block compiler? *(Set a Google Alert. Seriously.)*
4. Is the compiler's fidelity budget holding, or has it quietly regressed?
5. What percentage of revenue is BYOK, and what is that doing to margin?

---

## 4. The three assumptions this entire dossier rests on

Everything above is downstream of three beliefs. If any one of them is wrong, the strategy needs
rewriting rather than adjusting. **Test each one deliberately.**

| # | Assumption | How to test it | By when |
|---|---|---|---|
| **A1** | A visual design canvas can compile to native WordPress blocks at design-grade fidelity | The M0 compiler spike | Week 12 |
| **A2** | AI can generate genuinely design-grade layout — not template assembly — from a brief | Blind benchmark vs ZipWP / Big Sky / Elementor AI, rated by working designers | Week 14 |
| **A3** | Professional WordPress builders will pay ~$40/mo for speed + portability, and will *keep* paying after export | Design partner interviews (Phase 0) + export-to-return metric (private beta) | Week 6 / Week 30 |

**A1 and A2 are engineering questions with dates on them. A3 is a market question you can start
answering next week, for free, by talking to twelve people.**

Start there.
