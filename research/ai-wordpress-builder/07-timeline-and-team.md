# 07 — Process, Timeline, Team & Budget

---

## 1. The process (phase by phase)

```
 P0 DISCOVERY      P1 PROVE          P2 BUILD           P3 BETA         P4 SCALE
 ─────────────     ─────────────     ──────────────     ────────────    ────────────
 Interviews        Compiler spike    Canvas             Private beta    Public beta
 JTBD              IR design         Generation         Design partners GA
 Competitive       Eval harness      Section library    Iterate hard    Round-trip
 Concept test      Design system     Export pipeline    PMF test        Agency features
 Design partners   GO / NO-GO ◀──────┤                   Gate ◀────────┤
```

**The single most important structural decision: P1 is a real gate.** Most teams start the canvas
in week 2 because it's the fun part, discover the compiler can't hit fidelity in month 7, and
then rationalise a runtime plugin — at which point they've built a worse Elementor. Put the
compiler first and let it kill the idea if it's going to.

---

## 2. Timeline — Standard scenario (6–8 people)

### Phase 0 — Discovery · **Weeks 1–6**
| Wk | Work |
|---|---|
| 1–2 | Competitive teardowns (hands-on: buy Bricks, Etch, Droip, ZipWP, 10Web, Relume, Pinegrow — dissect the output of every one). Recruit interviewees. |
| 2–4 | 24 discovery interviews. Synthesis. JTBD + persona validation. |
| 3–5 | Design system foundations: token model, section archetype taxonomy, first 12 archetypes designed properly in Figma by an actual designer |
| 4–6 | Clickable concept prototype → 12 concept tests. Recruit 12 paid design partners. |
| 5–6 | Architecture RFC: the IR schema. Reviewed by a WordPress core-adjacent developer you pay for two days of their time. |

**Exit:** validated ICP, IR schema v0, 12 committed design partners, kill-criteria checked.

### Phase 1 — Prove · **Weeks 7–14**
| Wk | Work |
|---|---|
| 7–12 | **Compiler spike** → all M0 pass criteria (`06-beta-scope-and-roadmap.md` §2) |
| 8–13 | Generation pipeline v0: stages 1–4 only, structured output, 20 golden briefs |
| 10–14 | Eval harness + baseline benchmark **against ZipWP / Big Sky / Elementor AI output**. Blind-rated. This number is your product's reason to exist — get it early. |
| 13–14 | **GO / NO-GO.** Written decision memo. Kill or commit. |

**Exit:** proof the thesis is buildable, with numbers.

### Phase 2 — Build · **Weeks 15–24**
| Wk | Work |
|---|---|
| 15–20 | Canvas + IR store + altitude 1 (section editing) |
| 17–22 | Altitude 2 (element inspector), responsive, token binding |
| 18–23 | Section library to 60 archetypes × 3–5 variants ← **this is the most under-estimated task in the plan. It is a full-time designer + a full-time engineer for 8 weeks.** |
| 19–23 | Generation stages 5–6 (content + critique/repair loop) |
| 20–24 | Export pipeline, output inspector, audit panel, install flow |
| 21–24 | Auth, billing, metering, BYOK router |
| 23–24 | Onboarding flow, docs, install guide, first 10 tutorial videos |

**Exit:** Definition of Done for private beta met, in-house.

### Phase 3 — Private Beta · **Weeks 25–34** (opens **Week 24–25, ~month 5.5–6**)
| Wk | Work |
|---|---|
| 25 | 12 design partners onboarded, 1:1, recorded |
| 26–30 | Ruthless iteration. Weekly release. Weekly 5 user calls. Expand to ~50 users. |
| 28–32 | Security audit of the companion plugin; pen test |
| 30–33 | Reliability, export success rate, cost optimisation |
| 33–34 | PMF test, public beta gate review, pricing validation interviews |

**Exit:** public beta gate criteria met (`06` §5).

### Phase 4 — Public Beta → GA · **Weeks 35–48**
| Wk | Work |
|---|---|
| 35 | **Public beta launch** — Product Hunt, WP Tavern outreach, YouTube seeding, the uninstall demo video |
| 35–42 | Scale: support, docs, onboarding, section library to 100+ archetypes |
| 38–44 | SHOULD-tier features that survived; multi-direction generation; preview links |
| 42–46 | Round-trip sync **alpha** (behind a flag, with 10 users) |
| 46–48 | **GA 1.0** — pricing locked, annual plans, affiliate program |

---

## 3. All three scenarios, side by side

| Milestone | **Lean** 3–4 people | **Standard** 6–8 | **Funded** 12–15 |
|---|---|---|---|
| Discovery complete | Wk 6 | Wk 6 | Wk 4 |
| Compiler proven (GO/NO-GO) | Wk 16 | **Wk 14** | Wk 10 |
| Internal alpha | Wk 22 | Wk 18 | Wk 13 |
| **Private beta opens** | **Wk 32 (~7.5 mo)** | **Wk 25 (~5.75 mo)** | **Wk 18 (~4 mo)** |
| Public beta | Wk 46 (~10.5 mo) | **Wk 35 (~8 mo)** | Wk 26 (~6 mo) |
| GA 1.0 | Wk 62 (~14 mo) | **Wk 48 (~11 mo)** | Wk 36 (~8.5 mo) |
| v1.5 round-trip | Mo 19 | Mo 15 | Mo 11 |
| v2 agency | Mo 26 | Mo 21 | Mo 15 |

### The risk-adjusted version (what actually happens)

Add **25–40%** to any of the above and you'll be roughly right. The three things that always
blow the estimate on products of this shape:

1. **The section library.** Everyone budgets "a few weeks." It's 60 archetypes × 4 variants × 3
   breakpoints = 720 designed, built, compiled, tested states. Budget 10 weeks of two people, and
   hire a designer who has actually shipped a component library before.
2. **Compiler edge cases.** The first 80% of fidelity takes 6 weeks. The last 15% takes 6 months.
   This is where the moat lives, so it's *good* time — but plan for it.
3. **Beta support.** At 50 beta users you will lose a full engineer-equivalent to support and
   bespoke debugging. If you haven't staffed it, it comes out of the roadmap.

**Realistic answer to "how long?": a credible private beta at ~6 months with a proper team, a
paid public beta at ~8–9 months, GA at ~12 months. If someone on your team says 3 months, they
have not thought about the compiler.**

---

## 4. Team

### Minimum viable team (Standard scenario, 7 people)

| Role | Why they're essential | Notes |
|---|---|---|
| **Product/founder** (you) | Positioning, ICP discipline, community presence | You'll spend 40% of your time on community |
| **Compiler / WordPress engineer** | IR → blocks, `theme.json`, companion plugin | **The hardest hire and the most important.** Must have shipped block themes and know Gutenberg internals — not "has used WordPress." Look in the Bricks/Etch/GenerateBlocks orbit. |
| **Frontend engineer × 2** | Canvas, IR store, inspector, code panel | One should have built a visual editor or a design tool before |
| **AI/backend engineer** | Generation pipeline, structured output, eval harness, BYOK router, cost | Evals matter more than prompting |
| **Product designer** | Section library, design system, the three-altitude UX | This role *is* the product quality. Do not treat it as decoration. |
| **Design engineer / DX + docs + community** | Section library implementation, templates, docs, video, forums | The unglamorous role that decides whether the WP community adopts you |

**Later:** support lead (before public beta, not after), growth/content marketer (month 7),
second WP engineer (v1.5 sync).

### Hiring order if you're going lean
1. Compiler/WordPress engineer *(before anyone — the spike is the company)*
2. Product designer
3. Frontend engineer
4. AI/backend engineer

### Advisors worth paying for
- A **WordPress core / Gutenberg contributor** for 2 days/quarter on the compiler
- A **respected WP agency owner** as a design partner + advisor (distribution + credibility)
- A **security consultant** for the companion plugin, one engagement pre-public-beta

---

## 5. Budget (indicative, 12 months to GA — Standard scenario)

| Line | Range (USD) | Notes |
|---|---|---|
| Salaries (7 people, blended, mixed geography) | $550k – $1.1M | The whole ballgame. Varies 3× by location. |
| AI inference (dev + evals + beta users) | $25k – $70k | Evals are surprisingly expensive; budget for them explicitly |
| Infrastructure | $15k – $40k | Canvas is client-heavy; cost is mostly storage + asset processing |
| Design assets, stock, fonts, licences | $8k – $20k | Font licensing for the section library is a real, often-forgotten line |
| Competitor licences (you must buy all of them) | $2k – $4k | Cheapest research money you'll ever spend |
| Security audit + pen test | $10k – $25k | Non-negotiable before public beta |
| Legal (ToS, privacy, GPL review, trademark) | $8k – $20k | See `10-risks-legal-and-metrics.md` |
| Community/content/GTM | $30k – $80k | Video production, sponsorships, WordCamp presence |
| Contingency (20%) | — | Add it. You'll use it. |
| **Total** | **≈ $700k – $1.4M** | |

**Lean scenario:** ≈ $280k–$450k over 14 months, with founders unpaid or half-paid and a smaller
section library. Viable. Slower. Higher risk that a funded competitor arrives at your position
first.

---

## 6. Critical path

```
IR schema ──▶ Compiler spike ──▶ [GO/NO-GO] ──▶ Export pipeline ──▶ Private beta
     │                                                  ▲
     └──▶ Canvas ──▶ Altitude 1 ──▶ Altitude 2 ─────────┤
     │                                                  │
     └──▶ Generation pipeline ──▶ Eval harness ─────────┤
                                                        │
          Section library ────────────────────────────  ┘   ← the sleeper critical path
```

**Two items are on the critical path that people always mis-schedule:**
- **The IR schema** blocks literally everything. Spend three weeks on it, not three days. It is
  the one artefact you cannot cheaply change later (round-trip depends on it).
- **The section library** looks parallelisable and isn't — you can't ship a beta with 12
  archetypes, because the generated sites will all look identical and you'll fail your own
  differentiation test.

---

## 7. Weekly operating cadence (from Phase 2)

| When | What |
|---|---|
| Mon | Metrics review: activation, TTFE, export success rate, eval scores, AI cost/user |
| Tue–Thu | Build |
| Wed | 2 user calls (rotating, always, forever) |
| Thu | **Eval run in CI** — generation quality is a tracked metric, and a regression blocks release |
| Fri | Ship. Weekly release, always, even in beta. Changelog published publicly — the WP community reads changelogs and infers whether you're alive. |
