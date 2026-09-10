# AI Website Builder for WordPress — Research Dossier

Strategy and research for an AI-native visual site builder whose output is a **clean, native
WordPress block theme** — no page-builder runtime, no shortcode lock-in.

Compiled September 2026.

## Read in this order

| # | Document | What's in it |
|---|---|---|
| 00 | [Executive Summary](00-executive-summary.md) | The thesis, what I'd change about the original framing, beachhead, timeline at a glance, the three things to do first |
| 01 | [Market & Positioning](01-market-and-positioning.md) | Sizing (TAM/SAM/SOM), six enabling trends, the positioning map and the empty quadrant, messaging house, competitive-response plan |
| 02 | [Competitive Landscape](02-competitive-landscape.md) | 60+ competitors in 7 categories, deep dives on Etch / Relume / Pinegrow / Big Sky / ZipWP, feature matrix, the four gaps to own |
| 03 | [User Research & Personas](03-user-research-and-personas.md) | Research plan with kill criteria, JTBD, 6 personas + 4 anti-personas, journey maps, pain→feature mapping |
| 04 | [Product Strategy](04-product-strategy.md) | The three-altitude editing model, five differentiation pillars, moat analysis, feature architecture, what to cut |
| 05 | [Technical Architecture](05-technical-architecture.md) | The Design IR, the block compiler, the 6-stage generation pipeline, BYOK routing, round-trip sync, security |
| 06 | [Beta Scope & Roadmap](06-beta-scope-and-roadmap.md) | The M0 compiler spike and its pass criteria, Beta 1 MoSCoW, definition of done, release train to v2 |
| 07 | [Timeline & Team](07-timeline-and-team.md) | Phase-by-phase schedule, three staffing scenarios, budget, critical path, the risk-adjusted truth |
| 08 | [Pricing & Business Model](08-pricing-and-business-model.md) | Competitor price table, recommended tiers, unit economics, BYOK margin math, why not to do a lifetime deal |
| 09 | [GTM & Launch](09-gtm-and-launch.md) | WordPress community playbook, launch sequence, content engine, naming, homepage, objection handling |
| 10 | [Risks, Legal & Metrics](10-risks-legal-and-metrics.md) | Risk register, GPL position, EAA/accessibility, AI legal, North Star metric tree, the three core assumptions |
| — | [Sources](SOURCES.md) | Every source cited, with a note on what is *not* primary research |

## The short version

The gap is **design-grade + WordPress-native + AI-first**. Every quadrant around it is crowded;
that box is empty. Webflow/Framer/Figma can't reach WordPress. Etch and Bricks reach it cleanly
but exclude non-developers and have no AI. ZipWP/10Web/Big Sky have AI but produce template-swap
output and are mostly hosting funnels. Lovable/Bolt/v0 produce React apps a client can't edit.

**The moat is the compiler, not the canvas.** Prove it in a six-week spike before building
anything else.

**The business risk is export-and-churn**, which is why round-trip sync is architected in v1 even
though it ships in v1.5.
