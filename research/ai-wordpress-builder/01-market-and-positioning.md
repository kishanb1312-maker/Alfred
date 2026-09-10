# 01 — Market, Trends & Positioning

---

## 1. Market sizing (top-down)

### 1.1 The WordPress base

| Metric | Value (2026) | Source note |
|---|---|---|
| Share of all websites running WordPress | **~40.7%** (Sept 2026, W3Techs) | Down from a ~43.2% peak |
| Share of the CMS market | **~58.9–59.3%** | Down from 65.2% in 2022 |
| Next-largest CMS | Shopify 5.3%, Wix 4.2% | WP still ~8× its nearest rival |
| WordPress sites using *some* page builder | **~60%** | The builder is the norm, not the exception |
| Elementor detected on | **32.67%** of WP sites | ~10M+ active installs |
| WP Block Editor / Gutenberg | **20.6%** as primary editor; **72%** block-editor adoption overall | FSE growing ~145% YoY |
| wpBakery | 8.52% | Legacy, actively churning out |
| Divi | 5.72% | Flat; Divi 5 moved to block architecture |
| Bricks | small base, **+71.2% YoY** | Fastest-growing commercial builder |

**Read:** WordPress is declining *as a share of new sites* but the absolute installed base is
still enormous and the *builder* layer inside it is where the money and the churn are. You are
not betting on WordPress growth. You are betting on **builder switching** inside a base of tens
of millions of sites — which is a much better bet, because switching is already happening
(wpBakery bleeding, Bricks +71%, Etch launching to a queue).

### 1.2 The money layer

| Metric | Value |
|---|---|
| Global web design services market | **$61.2B (2025) → ~$92B (2030)**, ~8.5% CAGR |
| Typical 2–10 person web agency revenue | $400k–$1.5M/yr, 15–30% net margin |
| WordPress freelance dev rates | $40–80/hr (higher for Woo/custom) |
| Elementor Pro entry | ~$59–$99/yr/site range; Elementor One $168/yr |
| Divi | $89/yr or $249 lifetime; Divi Pro $277/yr incl. unlimited AI |
| Bricks | $79–$99/yr, lifetime ~$249–$299 |
| 10Web AI Builder | $10–$60/mo (hosting-bundled) |
| Relume | $0–$40/mo |
| Webflow | $14–$39/site/mo + workspace seats |
| Framer | $5–$30/site/mo + seats |

### 1.3 Bottom-up TAM/SAM/SOM (be sceptical of top-down here)

Assume the addressable buyer is *a person who builds WordPress sites for money*.

- **TAM** — everyone who touches a WP builder commercially. If ~60% of ~500M+ WP-adjacent sites
  use builders and even 1% of those are professionally maintained by a paying builder-license
  holder, you're looking at a licence market in the **$800M–$1.5B/yr** range across all builders,
  themes, and AI add-ons. Treat this as a directional ceiling, not a plan.
- **SAM** — English-speaking solo freelancers + boutique agencies building 2+ WP sites/month who
  are *design-forward* (i.e. would consider Webflow/Framer if the client allowed it). Estimate
  **250k–450k individuals globally**. At an achievable $250/yr blended ARPU → **$60M–$110M SAM.**
- **SOM (3 years)** — realistic capture of 1.5–3% of SAM → **4,000–13,000 paying accounts**,
  **$1.2M–$3.5M ARR**. That is a good, fundable, real business. Anyone telling you a WordPress
  builder gets to $100M ARR in three years is selling you something.

---

## 2. The six trends that make this the right moment

**T1 — AI site generation has crossed from novelty to expectation.**
Lovable ~$400M ARR (Feb 2026), Replit ~$525M, v0 4M+ users, Bolt profitable at $40M ARR on a
$700M valuation. Users no longer need convincing that "type a prompt, get a site" is real. That
education cost — historically the most expensive part of launching a category — has been paid
for you by people with far more money.

**T2 — …and essentially none of it lands in WordPress.**
Lovable, Bolt, v0, Replit, Base44 all output React/Next apps. Figma Sites can't export code at
all. Framer can't export code at all. Webflow exports HTML/CSS *without CMS content*. The entire
AI-generation wave routes *away* from the CMS that runs 40% of the web. That is a structural
mismatch, and structural mismatches are where products get born.

**T3 — WordPress's own AI answer is real but boxed in.**
Automattic's Big Sky / WordPress.com AI Site Builder is genuinely good, built on Gutenberg,
conversational + direct editing. But: it's **WordPress.com**, and it **only works with block
themes** — which locks out roughly half of all WordPress sites still on classic themes. It is a
hosting funnel, not a professional design tool. That leaves the self-hosted, agency, design-led
segment wide open.

**T4 — The lock-in backlash has gone mainstream.**
"Deactivate the builder and your content becomes bracketed gibberish" is now a stock complaint in
every 2026 comparison article. Businesses openly report losing months to builder migrations.
Bricks (+71% YoY) and Etch both sell primarily on *clean output*. Kevin Geary's Etch reached 1.0
in Jan 2026 explicitly positioned as "authors everything to native WordPress blocks." The market
has told you what it wants; nobody has combined it with AI generation and a design-grade canvas.

**T5 — Performance and accessibility became compliance issues, not preferences.**
Core Web Vitals are a ranking input. The European Accessibility Act has applied since June 2025,
pulling a large class of commercial sites into WCAG-shaped obligations. Elementor sells "Ally" as
a paid add-on. If your generator produces semantically correct, accessible, fast markup **by
default**, that is a sales weapon with a legal deadline attached — not a nice-to-have.

**T6 — BYOK went from fringe to expected in dev tools.**
The 2026 norm is a predictable platform fee plus either metered usage or a customer-owned key.
Buyers now explicitly ask "who controls the key, who pays the model bill, can I switch
providers." Your instinct here is correct and current.

---

## 3. The structural opening (the actual gap)

Map the space on two axes:

```
                    DESIGN FIDELITY / CREATIVE CONTROL
                              (high)
                                │
      Webflow ●                 │              ● Framer
      Figma Sites ●             │        ● Figma Make
                                │
      Bricks ●   ● Etch         │
      Droip ●                   │            ┌─────────────┐
                                │            │   << YOU >> │
  ──────────────────────────────┼────────────│  Design-grade│──────────
   NOT WORDPRESS-NATIVE         │            │  + WP-native │   WORDPRESS-NATIVE
   OUTPUT                       │            │  + AI-first  │   OUTPUT (clean)
                                │            └─────────────┘
      Lovable ●  ● Bolt         │
      v0 ●  ● Replit            │   Gutenberg/FSE ●
                                │   ZipWP ●    ● Big Sky
      Wix ● ● Squarespace       │   10Web ●    ● Hostinger AI
                              (low)
                    DESIGN FIDELITY / CREATIVE CONTROL
```

Every quadrant is crowded **except the top-right**: high design fidelity *and* clean
WordPress-native output *and* AI-first authoring.

- Tools with design fidelity (Webflow, Framer, Figma Sites) don't reach WordPress at all.
- Tools that reach WordPress cleanly (Gutenberg, Etch, GenerateBlocks) have low AI and demand
  developer skill.
- Tools that reach WordPress with AI (ZipWP, 10Web, Big Sky, Hostinger) produce
  template-swap-grade output, not design-grade output, and are usually hosting funnels.
- Tools with the best AI (Lovable, Bolt, v0) produce React apps a WordPress client cannot edit.

**The opening: design-grade + WP-native + AI-first.** One box. Currently empty.

---

## 4. Positioning

### 4.1 Positioning statement (internal)

> For **solo WordPress freelancers and boutique agencies** who **build client sites on WordPress
> but wish they could design in Webflow or Framer**, *[Product]* is an **AI-native visual design
> environment** that **generates and edits complete multi-page sites from a prompt and compiles
> them into clean, native WordPress block themes**. Unlike **Elementor, Divi, and other page
> builders**, our output **has no plugin dependency and no shortcode lock-in — if you stop paying
> us, your client's site keeps working.** And unlike **Webflow, Framer, or Lovable**, the thing
> you ship **is real WordPress**, editable by your client in Gutenberg on day one.

### 4.2 The three claims (and the proof each needs)

| Claim | Proof required before you may say it |
|---|---|
| "Design-grade" | Side-by-side rebuild of 5 award-winning sites, done in your editor, in under 2h each |
| "WordPress-native" | Uninstall your plugin. Page still renders and still edits in Gutenberg. Video it. |
| "AI-first" | Median time from prompt to publishable 5-page site under 15 minutes, measured, published |

Do not ship marketing ahead of proof in this community. WordPress Twitter/YouTube will test it
publicly within 48 hours and the takedown video will outrank your homepage.

### 4.3 Messaging house

```
                  "Design like it's Framer. Ship like it's WordPress core."
   ┌──────────────────────┬──────────────────────┬──────────────────────┐
   │  NO LOCK-IN          │  REAL DESIGN CONTROL │  AI THAT DOES THE    │
   │                      │                      │  BORING 80%          │
   │ Native blocks +      │ Section-level speed, │ Prompt → sitemap →   │
   │ theme.json. Cancel   │ element-level        │ multi-page draft in  │
   │ us and nothing       │ precision, code-     │ minutes, on your     │
   │ breaks.              │ level escape hatch.  │ brand tokens.        │
   ├──────────────────────┼──────────────────────┼──────────────────────┤
   │ Proof: uninstall demo│ Proof: rebuild videos│ Proof: timed builds  │
   │ Proof: 0 shortcodes  │ Proof: CSS inspector │ Proof: BYOK option   │
   │ Proof: theme export  │ Proof: 3-altitude UI │ Proof: token control │
   └──────────────────────┴──────────────────────┴──────────────────────┘
   Foundations: fast by default (CWV budget) · accessible by default (EAA/WCAG) ·
                your key or ours · GPL-clean · client-safe handoff
```

### 4.4 Positioning traps to avoid

- ❌ **"The Elementor killer."** Cliché, invites a feature-parity war you cannot win against
  10M installs and a decade of add-on ecosystem. You are not replacing Elementor's widget
  library. You are replacing the *reason people tolerate it*.
- ❌ **"AI website builder."** Commoditised, indistinguishable from Hostinger's $2.99 offer,
  attracts the exact low-value high-churn segment you don't want.
- ❌ **"For everyone."** SMB DIY and pro agencies want opposite things (one wants fewer choices,
  the other wants all of them). Pick pros. Add a simplified client mode later — which is a
  *feature for pros*, not a second product.
- ❌ **"Webflow for WordPress."** Tempting, and I'd use it in a pitch deck, but it sets the
  expectation of Webflow's CMS depth and interaction engine on day one. You will disappoint.

---

## 5. Competitive response — what happens when you're noticed

Assume 6–12 months of quiet, then reaction. Plan for it:

| Who | Likely response | Your counter |
|---|---|---|
| **Elementor** | Ships an AI wireframe→page flow (already has Site Planner + AI Copilot); will *not* abandon its own rendering layer | Their runtime dependency is architectural and permanent. Keep hammering the uninstall demo. |
| **Automattic / Big Sky** | Extends AI builder to self-hosted via Jetpack/plugin | Real threat. Counter on design fidelity, agency workflow, multi-client workspace, BYOK, and not being a hosting funnel. |
| **Bricks / Etch** | Adds AI generation on top of clean output | The most dangerous competitor set, because they already own the "clean output" position. Counter on AI quality, non-developer accessibility, and multi-page generation. Move fast here. |
| **ZipWP / Brainstorm Force** | Improves generation fidelity, bundles with Astra/Spectra | They're template-assembly, not design. Counter on originality of output. |
| **Hosts (Hostinger, Bluehost, WP Engine)** | Bundle a free AI builder to sell hosting | Can't beat free-with-hosting on price. Don't try. Sell to people whose *deliverable quality* is their livelihood. |
| **Lovable / Bolt** | Adds a "publish to WordPress" checkbox | Would be a static/headless bridge, not native blocks. Watch it. If any of them ship a *real* block compiler, your moat halves overnight — which is exactly why the compiler must be your deepest investment. |
