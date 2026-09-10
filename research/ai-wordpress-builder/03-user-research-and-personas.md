# 03 — User Research, Jobs-to-be-Done & Personas

---

## 1. Research plan (do this before writing product code)

You have no primary research yet. Everything below is a **hypothesis built from secondary
sources** — treat it as a script to validate, not a finding to build on. Here's the plan that
turns it into evidence.

### Phase 1 — Discovery interviews (Weeks 1–4)

| | |
|---|---|
| **N** | 24 interviews: 12 solo freelancers, 8 boutique-agency leads, 4 WP developers |
| **Recruit from** | Bricks/Etch Facebook groups & Discords, r/Wordpress, r/webdev, WPBeginner comment sections, Elementor subreddit, YouTube comment sections (WPCrafter, WPTuts, Kevin Geary), Upwork/Fiverr top-rated WP sellers, local WordCamp Slack |
| **Incentive** | $75–100 or a lifetime founder licence. Pay people. Free interviews select for the wrong people. |
| **Length** | 45 min, recorded, semi-structured |

**Interview guide (the questions that actually matter):**

1. Walk me through the last client site you built, from the kickoff call to handoff. *(Timeline
   the whole thing. Where did the hours actually go?)*
2. What did you use, and why that? What did you *want* to use?
3. Show me the moment in that project you'd most like to never do again.
4. Have you ever migrated a site off a builder? What happened?
5. When a client asks to change something after handoff — what actually happens?
6. Have you used Lovable / Bolt / v0 / ChatGPT to make anything web-shaped? What did you do with
   the output?
7. If your builder vendor shut down tomorrow, what happens to your 40 client sites?
8. What do you charge for a 5-page brochure site, and how many hours is it?
9. Show me your last three sites. *(Design fidelity calibration — are they actually design-led,
   or template-swappers? This determines your ICP.)*

**Kill criteria — if these come back true, rethink the whole thing:**
- Fewer than 8/24 have ever *tried* to leave a builder and been blocked by lock-in
- Fewer than 6/24 express any dissatisfaction with their current builder's design ceiling
- More than 16/24 say "my clients never edit the site anyway" (kills the round-trip value prop)

### Phase 2 — Concept testing (Weeks 5–7)
Clickable Figma prototype of the three-altitude editor + the export moment. 12 users,
think-aloud, task-based. **Primary measure: do they believe the "no plugin dependency" claim
without a demo?** If not, the demo *is* the marketing.

### Phase 3 — Diary study (Weeks 8–14, runs in parallel with build)
6 design partners, 6 weeks, log every client project. What you're hunting: how often design
changes happen *after* content is populated (this sizes the round-trip feature) and how often a
project needs something outside your section library (this sizes the escape-hatch feature).

### Phase 4 — Continuous (from private beta)
- Weekly 30-min calls with 5 rotating beta users, forever
- In-product: time-to-first-export, section-override rate, code-panel open rate, AI-regenerate
  count per page (a proxy for generation quality — see `10-risks-legal-and-metrics.md`)
- Quarterly WP-community survey published as content marketing (doubles as GTM — see
  `09-gtm-and-launch.md`)

---

## 2. Jobs to be Done

### Primary job
> **When** a client signs off on a brief and I have to produce a WordPress site,
> **I want to** get from "blank page" to "on-brand, working, multi-page draft" without spending
> two days assembling boxes,
> **so I can** spend my hours on the parts the client actually pays for — strategy, copy,
> and polish — and take on more projects at the same rate.

### Related jobs
| Job | Currently solved by | How badly |
|---|---|---|
| Present 2–3 real design directions before I've built anything | Figma mockups, template screenshots | Slowly. Days of unpaid pre-sales work. |
| Hand over a site the client can edit without destroying | "Please only edit text," training videos, prayer | Terribly. This is the #1 post-launch support cost. |
| Keep 40 client sites maintainable for years | Standardising on one builder | Fragile. One vendor decision away from disaster. |
| Prove the site is fast and accessible | Plugins, audits, manual fixes | Expensively, and after the fact. |
| Reuse my own patterns across clients | Copy-paste, template libraries, Frames/ACSS | Partially. Nothing is truly systemic. |
| Not look like every other Astra/Elementor site | Buying premium templates | Poorly — the templates are the problem. |

### The emotional job (don't skip this)
Every one of these people is quietly anxious about **being made irrelevant by AI**. They watch
Lovable demos and feel the floor move. Your product must be framed as *the thing that makes them
faster and more valuable*, never as *the thing that replaces the skill they sell*. Get this tone
wrong in one launch video and the WordPress community will turn on you in a weekend.

---

## 3. Personas

### 🎯 P1 — Ravi Menon · **The Solo WordPress Freelancer** *(PRIMARY / beachhead)*

| | |
|---|---|
| **Age / location** | 31 · Pune, India (archetype spans Manila, Lagos, Kraków, Austin) |
| **Role** | Independent. Designs *and* builds. |
| **Volume** | 3–8 sites/month, mostly 5–12 page brochure sites |
| **Rate** | $40–70/hr effective; $800–$3,500 per site |
| **Stack** | Elementor Pro + Astra/Hello + WPForms + Rank Math + a slider he regrets |
| **Skill** | Confident in CSS, can read PHP, won't write a plugin |

**A day in the life:** Kickoff Monday. Tuesday–Wednesday assembling containers in Elementor from
a template he bought and is now fighting. Thursday copy. Friday client review, three rounds of
"can the hero be bigger." Two weeks later the client has broken the header and it's a free fix.

**Pains (ranked by how much he'd pay to remove them):**
1. Days lost to layout assembly that produces nothing the client can perceive as value
2. Every site looks like the last site — he can't charge premium rates for template swaps
3. Client edits break layouts; he eats the support cost
4. Elementor Pro renewals × 40 client sites; Elementor AI credits feel like a rip-off
5. Terrified of what happens if he ever needs to move off Elementor

**Gains sought:** more sites at the same hours · portfolio pieces that look designed, not
assembled · a handoff that stops calling him back

**Quote (composite):** *"I don't need AI to write my copy. I need it to stop me spending Tuesday
dragging divs."*

**What wins him:** the timed prompt→site demo, then the uninstall demo. In that order.
**What loses him:** price above ~$30/mo without per-client billing, or output he can't hand to a
client. He is price-sensitive and trust-sensitive in equal measure.

---

### 🎯 P2 — Marta Kowalczyk · **The Boutique Agency Design Lead** *(PRIMARY)*

| | |
|---|---|
| **Age / location** | 38 · Warsaw / Lisbon / Toronto |
| **Team** | 6 people (2 designers, 2 devs, PM, founder). ~$700k/yr revenue, ~22% net |
| **Volume** | 2–4 projects/month, $8k–$45k each |
| **Stack** | Figma → hand-off → Bricks or custom block theme; ACSS/Frames; ClickUp |
| **Portfolio** | 60+ maintained client sites on retainer |

**Pains:**
1. The Figma→build handoff is where the design dies. Devs approximate; designers re-review; two
   days evaporate per project.
2. Pitch work is unpaid. Every proposal needs visuals she can't afford to fully design.
3. 60 sites on retainer = 60 sites whose stack she is responsible for in 2030.
4. Junior designers can't produce production-ready builds; she's the bottleneck.

**Gains sought:** design system enforced by the tool, not by code review · junior designers
shipping without her · a pitch artefact in an afternoon · a maintenance story she can defend

**Quote:** *"I'll pay real money for anything that means my designers stop handing my developers a
picture of a website."*

**What wins her:** design tokens as first-class citizens, a shared component/section library
across clients, multi-seat workspace, white-label handoff.
**What loses her:** anything that looks like a toy, or output her senior dev calls bloated. **Her
developer has veto power over your purchase.** Design for the buyer, but survive the gatekeeper.

---

### 🎯 P3 — Deepak Sharma · **The WordPress Developer / Bricks-Etch Believer** *(GATEKEEPER)*

| | |
|---|---|
| **Age** | 34 · Remote, works with 3 agencies |
| **Stack** | Bricks or a hand-rolled block theme, ACSS, GenerateBlocks, Git, WP-CLI, local-first |
| **Beliefs** | Page builders are technical debt. Elementor is a slur. Clean DOM is a moral position. |

**Pains:** clients arrive with Elementor sites he has to maintain · AI output he doesn't trust ·
being asked to "just quickly fix" someone else's builder mess

**Attitude to you:** **hostile by default.** He will install your beta, export a page, open
DevTools, count the wrappers, and post the screenshot. That screenshot decides your reputation.

**Gains sought:** output he'd have written himself · full CSS/HTML control · Git-friendly export ·
no runtime dependency · no `!important`, no wrapper soup, no inline style spam

**Quote:** *"Show me the markup. If there's a div with a generated class name wrapping a div with
a generated class name, we're done here."*

**Why he's in this document:** he is not your main buyer, but he is the **permission structure**
for P1 and P2. Win Deepak and the other two follow. Lose him publicly and you spend a year
recovering. **Give him a "view compiled output" panel from day one of the private beta and let
him tear it apart in private before he does it in public.**

---

### ○ P4 — Nadia Farouk · **The Framer/Webflow Refugee** *(SECONDARY, high-value)*

| | |
|---|---|
| **Age** | 29 · Product/brand designer, freelance |
| **Stack** | Figma, Framer, Webflow. Has never enjoyed a minute inside WordPress. |

**Situation:** her clients keep insisting on WordPress — for their marketing team, their SEO
agency, their existing plugins, their IT policy. She either turns down work or subcontracts the
build and loses margin and control.

**Pains:** WordPress builders feel a decade behind Framer · she can't produce the motion and
polish she's known for · handing off to a WP dev means losing the design

**Gains sought:** a canvas that respects her craft · real typography and spacing control ·
motion/interaction · and then, quietly, WordPress at the end of it

**Quote:** *"I don't want to learn WordPress. I want to not have to."*

**Why she matters:** she's the highest-fidelity demand signal for "design-grade," she has an
audience on design Twitter/Dribbble, and she'll pay 2–3× P1's price without blinking. But she's a
smaller pool and will churn if the canvas isn't genuinely good. **Serve her in v1.5, don't build
the v1 for her.**

---

### ○ P5 — Tom Bradley · **The White-Label / Reseller Partner** *(SECONDARY, channel)*

Runs a 200-site care plan business or a hosting reseller. Doesn't design. Wants volume,
standardisation, margin, and his own logo on it. **Value:** distribution and predictable revenue.
**Risk:** he'll ask for white-label, multi-site management, and an API before you're ready, and
if you build for him early you'll build the wrong product. **Say yes in v2, not v1.**

---

### ○ P6 — Sam Okafor · **The SMB Owner** *(TERTIARY / mostly an anti-persona)*

Runs a dental practice / gym / consultancy. Wants a website, has $500, will use whatever is
cheapest. **This is the segment Wix, Hostinger ($2.99), 10Web and Big Sky are already fighting a
land war over.** High CAC, 20–40% churn, high support cost, zero willingness to pay for design
quality. **Do not build for Sam.** But note: Sam *is* P1's client, so "Sam can safely edit the
site after handoff" is a P1 feature you should absolutely build.

---

### ⛔ Anti-personas — explicitly out of scope for 24 months

| Who | Why not |
|---|---|
| **Enterprise WordPress / VIP** | Procurement cycles, SSO/SOC2, custom workflows, headless. Wrong company shape. |
| **WooCommerce-first store builders** | Product templates, variations, checkout, tax, shipping — a swamp. v2 at the earliest, and only basic. |
| **Headless / Next.js WordPress teams** | They don't want a visual builder; they want an API. Different product. |
| **Non-WordPress AI app builders' users** | You will never out-Lovable Lovable at building apps. Don't try. |

---

## 4. Journey map — P1 (Ravi), current vs. target

### Current state
```
KICKOFF ──── DESIGN ──────── BUILD ─────────── CONTENT ── REVIEW ── LAUNCH ── SUPPORT
  2h          4h (or skip)    14–20h            6h         5h        3h       ∞ hours
                │                │                          │                    │
             😐 "I'll         😩 PEAK PAIN               😤 "can the         😫 "the client
             just find a      dragging containers,       hero be             broke the
             template"        fighting the template      bigger"             header"
```
**Time to first client-viewable draft: 3–5 days.** Emotional low point: build. Support tail:
permanent.

### Target state
```
KICKOFF ── PROMPT+TOKENS ── AI DRAFT ── CURATE ── CONTENT ── REVIEW ── EXPORT ── LAUNCH ── SUPPORT
  2h          30min           8 min      4–6h      4h         3h       15min      1h      reduced
                                 │          │                   │                    │
                              🤩 "there's  🙂 real design    😌 changes are      🙂 client edits
                              a whole      work, not         cheap because      content, can't
                              site here"   assembly          sections swap      break layout
```
**Time to first client-viewable draft: same day.** Value moves from assembly to curation.
Support tail shrinks because the handoff is content-only.

**The two moments that decide everything:**
1. **First draft reveal** (minute ~8). If it looks generic, Ravi closes the tab and never returns.
   This is why design-grade generation is the hard requirement, not a stretch goal.
2. **The export moment.** If it takes more than one step or produces anything he has to fix by
   hand, the whole promise collapses. **Instrument both obsessively.**

---

## 5. Consolidated pain inventory → feature mapping

| # | Pain | Persona | Severity | Feature that kills it | Beta? |
|---|---|---|---|---|---|
| 1 | Layout assembly eats days | P1, P2 | 🔴 | AI multi-page generation from prompt + brand tokens | ✅ |
| 2 | Everything looks templated | P1, P2, P4 | 🔴 | Design-grade generation, not template retrieval | ✅ |
| 3 | Builder lock-in / vendor risk | P1, P2, P3 | 🔴 | Native block + `theme.json` compiler, no runtime plugin | ✅ |
| 4 | Client breaks the site after handoff | P1, P2 | 🔴 | Content-only editing mode / locked layout on export | ✅ (basic) |
| 5 | Figma→build handoff loses the design | P2, P4 | 🟠 | Design is the build; tokens are the system | ✅ |
| 6 | Bloated output, poor CWV | P3, P2 | 🟠 | Compiler with a performance budget + output inspector | ✅ |
| 7 | Design change after content = rebuild | P1, P2 | 🟠 | **Round-trip sync** | ❌ v1.5 |
| 8 | Accessibility obligations (EAA) | P2, P5 | 🟠 | Accessible-by-default components + audit panel | ◐ partial |
| 9 | Unpaid pitch/spec work | P2 | 🟡 | Shareable concept links, 3-direction generation | ❌ v1.5 |
| 10 | No system reuse across clients | P2, P5 | 🟡 | Shared section/token libraries, workspace | ❌ v2 |
| 11 | AI cost unpredictability | P1, P3 | 🟡 | BYOK + transparent token metering | ✅ |
| 12 | Managing 40+ sites | P5, P2 | 🟡 | Multi-site dashboard, bulk updates | ❌ v2 |

**Rule:** everything 🔴 must be in Beta 1 or you don't have a product, you have a demo.
