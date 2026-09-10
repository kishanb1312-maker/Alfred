# 02 — Competitive Landscape

You named Elementor, Gutenberg, Webflow, Framer, Replit, Lovable and Bolt. That's about a tenth
of who you're actually up against. Here's the full board, in seven categories, plus the ones that
matter most and why.

---

## Category A — Established WordPress page builders (the incumbents)

| Product | Model | Strength | Weakness / your angle |
|---|---|---|---|
| **Elementor** (+ Elementor AI, Site Planner, Ally, One) | $59–$399/yr, credits for AI | 32.67% of WP sites, ~10M installs, enormous 3rd-party add-on ecosystem, brand = "WordPress builder" | Runtime plugin dependency = permanent lock-in; heavy DOM/CSS output; **metered AI credits widely criticised as expensive** (1 credit/text, 33/image, 40/container); market share sliding from ~56% (2023) |
| **Divi 5** (+ Divi AI, Quick Sites) | $89/yr, $249 lifetime; Divi Pro $277/yr **unlimited AI** | Lifetime pricing, huge loyal base, Divi 5 moved to block-ish architecture, **unlimited AI is a real advantage over Elementor's credits** | Legacy shortcode debt on older sites; design ceiling; still a runtime dependency |
| **WPBakery** | Bundled with themes | 8.52% share by sheer theme-bundling inertia | Pure shortcode lock-in; actively churning; **this is your migration source pool** |
| **Beaver Builder** | $99–$399/yr | Beloved by agencies for stability + clean-ish output, white-label | Small share, minimal AI, dated UI |
| **Brizy** | $/yr + white-label cloud | Good UX, agency white-label | Small, split focus between WP and Cloud |
| **Oxygen 6** | ~$129–$249 | Developer-grade, no theme needed | Niche; Oxygen 6 rewrite came late; audience partly poached by Bricks/Etch |
| **Bricks** | $79–$99/yr, ~$249 lifetime | **Fastest-growing commercial builder, +71.2% YoY.** Clean output, small pages, developer trust, strong community | Requires web fundamentals; limited AI; *this crowd is your best early adopter pool and your most credible critic* |
| **Breakdance** | $/yr | Fast, clean, from the Oxygen team, good element set | Middle-positioned between Bricks and Elementor |
| **Droip** (Themeum, now merged into **Kirki**) | $/yr | Genuinely Webflow-like freeform canvas inside WP, animations, form/popup builders, native-ish output | The Kirki merge caused community controversy; advanced features unintuitive; thin templates; **closest existing product to your canvas UX — study it hard** |
| **Zion Builder, Live Canvas, Greenshift, Stackable, Otter, Kadence Blocks, Spectra, GenerateBlocks, Blocksy** | mixed | Block-native or lightweight; GenerateBlocks + Kadence are the "clean blocks" cohort | Low design ceiling, no AI generation, developer-flavoured |
| **⚰️ Cwicly** | dead | *Was* the most technically admired block-native builder | **Shut down and stranded its users.** This is the single most important cautionary tale in your market. Your trust story must answer it. |

**Category takeaway:** Incumbents win on ecosystem, lose on lock-in and output quality. The
growth is 100% in the "clean output" cohort (Bricks +71%, Etch, GenerateBlocks). None of them has
a credible AI generation story yet. That's a narrow, closing window.

---

## Category B — The new WordPress "clean output" school (your real rivals)

### **Etch** — Digital Gravy (Kevin Geary) — *the most dangerous competitor on this board*
- Hit **v1.0 on 30 Jan 2026**. Positioned as a "Unified Visual Development Environment," explicitly
  *not* a page builder and *not* for people unwilling to learn web development.
- Visually manipulates **real HTML, CSS, PHP and JS**, and **authors everything to native
  WordPress blocks**. That is *literally your output thesis*, shipped, by a team (Automatic.css,
  Frames) already trusted by thousands of agencies.
- **Why you can still win:** Etch deliberately excludes non-developers, has no AI-first multi-page
  generation, and its canvas is a dev environment rather than a design environment. Your play is
  *design-grade + AI + accessible to a designer who doesn't write CSS from scratch* — the segment
  Etch has explicitly declined to serve.
- **Why you should be nervous:** if Etch bolts on strong AI generation, they arrive at your
  position with an existing audience, a charismatic founder with a big megaphone, and years of
  community credibility. **Assume 12–18 months.**

### **Frames / Automatic.css** (same team)
Design-system-first component library + utility CSS framework. Proof that WP agencies will pay
for *systems* rather than widgets. Also proof that the "token-first" model you should adopt sells.

### **Bricks + BricksExtras/BricksForge ecosystem**
The community you must win over. If Bricks power users publicly say your output is clean, you're
credible. If they say it's bloated, you're dead. Budget for this audit publicly.

---

## Category C — AI WordPress site generators (closest to your stated idea)

| Product | What it does | Real limitation |
|---|---|---|
| **ZipWP** (Brainstorm Force / Astra) | Full WP site in <60s; host-agnostic; free tier (sites expire in 24h unless upgraded/exported) | It's **template assembly with AI copy**, not design generation. Output is Astra/Spectra-flavoured. Everything looks like everything. |
| **10Web AI Builder** | Q&A or **recreate a site from a URL**; unlimited AI pages | **Tied to 10Web hosting** ($10–$60/mo). It's a hosting funnel. Output is Elementor-based → back to lock-in. |
| **Hostinger AI** (+ Horizons) | $2.99 entry, AI site + WP | Hosting funnel, budget segment, shallow design control |
| **WordPress.com AI Site Builder / "Big Sky"** (Automattic) | Conversational + direct block editing, generates logo, typography, palette, content; 30 free prompts then paid plan | **WordPress.com only**, **block themes only** (locks out ~half of WP sites on classic themes), no agency workflow, no self-hosted story yet |
| **Divi Quick Sites** | Full AI site inside Divi | Divi-locked |
| **Elementor AI + Site Planner** | AI copy/image/CSS/containers, AI wireframes | Credit-metered, Elementor-locked |
| **Extendify Launch** | Onboarding site-generation flow bundled by hosts | Host-distributed, template-grade |
| **Kadence AI**, **Bluehost AI**, **CodeWP** | Block-theme generation / WP-specific code gen (CodeWP trained on Woo hooks + PHP core) | CodeWP is code assistance, not a builder — but a plausible acquirer/partner/competitor in the "AI for WP" adjacency |

**Category takeaway:** every one of these is either (a) a hosting funnel or (b) template
assembly. **None produces original, design-grade layout.** That's the quality bar you must clear
to differentiate — and it's a genuinely hard AI problem, not a prompt-engineering problem. See
`05-technical-architecture.md` §4.

---

## Category D — AI app/site builders outside WordPress (the ones you named)

| Product | Scale (2026) | Why it doesn't reach your user |
|---|---|---|
| **Lovable** | **~$400M ARR** (Feb 2026, from $100M 8 months earlier); $13.3B valuation Aug 2026; 60M+ projects | Outputs React/Supabase apps. A client cannot edit content. No WordPress path. |
| **Replit** | ~**$525M ARR**, $400M raise at $9B (Mar 2026) | Full dev environment. Wrong audience entirely. |
| **Bolt.new** | $40M ARR in 5 months, $700M valuation, profitable; WebContainers = genuinely fast | Same: app output, no CMS handoff |
| **v0** (Vercel) | 4M+ users; Vercel at $9.3B | Component/page generation for React devs |
| **Base44 / Create.xyz / Softgen / Databutton / Tempo** | Varied | Same app-output category |

**What to steal from them:** the *interaction model*. Chat panel beside a live preview,
diff-style revisions, version history you can roll back, "select an element and describe the
change." Lovable's growth is 80% UX, 20% model.

**What not to steal:** their retention problem. Industry reporting puts **churn at 20–40%** in
AI coding services, **63% of developers say they spend more time debugging AI code** than writing
it themselves would have taken, and trust in AI-generated code fell from 77% → 60%. The
generation game is won; the *quality and maintainability* game is wide open. Position there.

---

## Category E — Visual web platforms (the design bar you're judged against)

| Product | Note |
|---|---|
| **Webflow** | The design/CMS gold standard. Code export exists but **excludes CMS content and e-commerce** — dynamic pages come out structurally empty. This is exactly why Webflow→WP conversion is unsatisfying. |
| **Framer** | Best-in-class motion + AI Workshop. **No code export at all.** Total vendor lock-in. Framer refugees who need WordPress are a real, identifiable, frustrated audience — go recruit them. |
| **Figma Sites / Figma Make** | Sites in open beta since Config 2025; **Code Layers** (React-rendered layers) Aug 2025; **CMS public beta Nov 2025** (multi-collection, 200 items/collection limit). **No code export, no self-hosting.** Figma is now a direct competitor to Webflow/Framer — and to your canvas UX expectations. Designers will compare your canvas to Figma's. Plan for that. |
| **Wix (ADI/Astro)** | Volume leader in SMB DIY, **+32.6% YoY**, actively taking WordPress share. Reports 34% higher 30-day site retention for AI-onboarded users. |
| **Squarespace (Blueprint AI)**, **Dorik**, **Typedream**, **Universe**, **Plasmic**, **Builder.io (Visual Copilot / Fusion)** | Builder.io matters most: visual editing over real code, headless-CMS-shaped. Watch them. |

---

## Category F — Design-to-code / handoff tools (your closest UX analogues)

| Product | Relevance |
|---|---|
| **Relume** | **Study this one hardest.** Prompt → **sitemap** → one-click **wireframes** from 1,000+ human-designed components → export to Webflow or Figma. $0–$40/mo. Users report 2–4 hours saved per project. **Your section-first model is essentially Relume's, and their sitemap-first flow is the right IA. But Relume stops at wireframes and never reaches WordPress.** That's your extension. |
| **Anima, Locofy, TeleportHQ, Uizard, UX Pilot, Visily** | Design→code converters. Consistently mediocre output quality — proof that "convert pixels to code" is the wrong abstraction. Generate from a *structured model*, never from a rendered image. |
| **Pinegrow Web Editor** | **The most underrated competitor on this list.** A desktop visual editor that genuinely exports **WordPress themes and Gutenberg blocks** from HTML/CSS. Small, developer-flavoured, no AI, dated UX — but it *proves the compiler is technically possible*. Buy a licence, dissect the output, learn from their block-attribute mapping. |

---

## Category G — Bridge / export tools (the incumbent solution to your problem)

| Tool | What it does | Why it's not good enough |
|---|---|---|
| **Udesly Adapter** | Converts Webflow exports → WP themes, maps Webflow collections → custom post types | **Re-export and re-convert on every design change.** No round-trip. Output is a static-ish theme, not natively editable in Gutenberg. Niche adoption after years. |
| **Webflow→WP plugins, "Framer to WordPress" services** | Mostly manual rebuild or iframe/proxy hacks | Framer has no export, so these are rebuilds sold as conversions |
| **Static site → WP theme services** | Freelancer labour | Doesn't scale, no AI |

**Category takeaway:** the existing solution to *exactly the problem you're solving* is a slow,
one-way, non-round-tripping utility. That's the strongest single validation in this document —
and the clearest instruction: **round-trip is the feature that makes you not-Udesly.**

---

## Positioning map — feature matrix

| | AI multi-page gen | Design-grade canvas | Code editing | WP-native output | No plugin dependency | Round-trip sync | BYOK |
|---|---|---|---|---|---|---|---|
| Elementor + AI | ◐ | ◐ | ◐ CSS only | ✗ | ✗ | n/a | ✗ |
| Divi 5 + AI | ● | ◐ | ◐ | ◐ | ✗ | n/a | ✗ |
| Bricks | ✗ | ● | ● | ◐ | ✗ | n/a | ✗ |
| **Etch** | ✗ | ● | ● | **●** | **●** | n/a | ✗ |
| Droip / Kirki | ✗ | ● | ◐ | ◐ | ✗ | n/a | ✗ |
| Gutenberg / FSE | ✗ | ✗ | ◐ | ● | ● | n/a | ✗ |
| ZipWP | ● | ✗ | ✗ | ◐ | ◐ | ✗ | ✗ |
| 10Web | ● | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Big Sky (WP.com) | ● | ◐ | ✗ | ● | ● | n/a | ✗ |
| Webflow (+Udesly) | ◐ | ● | ◐ | ✗ | ◐ | ✗ | ✗ |
| Framer | ● | ● | ✗ | ✗ | ✗ | ✗ | ✗ |
| Figma Sites | ● | ● | ◐ | ✗ | ✗ | ✗ | ✗ |
| Relume | ● | ◐ | ✗ | ✗ | n/a | ✗ | ✗ |
| Lovable / Bolt / v0 | ● | ◐ | ● | ✗ | n/a | ✗ | ◐ |
| Pinegrow | ✗ | ◐ | ● | ● | ● | ✗ | ✗ |
| **[YOU]** | **●** | **●** | **●** | **●** | **●** | **●** | **●** |

● full · ◐ partial · ✗ none

**No existing row has more than four filled cells. Your thesis needs all seven — which is
simultaneously the opportunity and the reason this takes 12+ months, not 3.**

---

## The four gaps you can actually own

1. **Design-grade AI output for WordPress.** Everyone in Category C generates templates. Nobody
   generates *design*. Highest value, hardest to build.
2. **Round-trip between an external canvas and a live WordPress site.** Category G's fatal flaw.
   High value, high difficulty, and the single best retention mechanism available to you.
3. **Three-altitude editing (section / element / code) in one canvas.** Etch has element+code but
   not section-speed or AI; Relume has section but no depth; Elementor has widgets but no code.
4. **Portable-by-construction output.** Not a promise — an architectural property. "Cancel your
   subscription, the site still works." Answers the Cwicly ghost directly.

## The three things you should *not* try to own

1. **A widget/add-on ecosystem.** Elementor has a decade of head start and thousands of
   third-party developers. Don't compete. Interoperate: your output is native blocks, so *every*
   block plugin already works alongside you. Say that loudly — it's a real advantage.
2. **WooCommerce depth.** A swamp. Support basic product templates in v2 at the earliest.
3. **Hosting.** It's a different business with different margins, it invites the Category C
   comparison you spent this whole document escaping, and it makes "portable output" a lie.
