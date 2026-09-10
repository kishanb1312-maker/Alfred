# 04 — Product Strategy & Differentiation

---

## 1. The three-altitude editing model

Your "sections, not widgets" instinct is right but needs sharpening. Every visual builder makes a
single, fatal choice: pick one granularity and serve one audience. Elementor picked widgets and
lost developers. Etch picked elements/code and excluded designers. Relume picked sections and
can't finish a site.

**Don't pick. Layer.**

```
┌────────────────────────────────────────────────────────────────────────────┐
│  ALTITUDE 1 — SECTION           "Make this hero taller and swap the image" │
│  ───────────────────────────────────────────────────────────────────────── │
│  Unit: a whole meaningful chunk (Hero, Features, Pricing, FAQ, Footer)     │
│  Actions: swap variant · regenerate · reorder · duplicate · delete ·       │
│           edit content inline · adjust section-level tokens (density,      │
│           alignment, media, background)                                   │
│  Audience: P1 Ravi, P2 Marta, and 90% of all editing time                 │
│  UX: click a section → a focused panel, not a 40-field kitchen sink       │
└────────────────────────────────────────────────────────────────────────────┘
                                    ↓  "I need more control"
┌────────────────────────────────────────────────────────────────────────────┐
│  ALTITUDE 2 — ELEMENT                        Box model, type scale, layout │
│  ───────────────────────────────────────────────────────────────────────── │
│  Unit: any node in the tree (grid, stack, text, image, button)            │
│  Actions: full layout control (flex/grid), spacing, typography, states,    │
│           breakpoints, motion — all bound to TOKENS, not raw values       │
│  Audience: P2, P4, and P1 when he's fussy                                 │
│  UX: reveal on demand — never the default surface                         │
└────────────────────────────────────────────────────────────────────────────┘
                                    ↓  "just let me write it"
┌────────────────────────────────────────────────────────────────────────────┐
│  ALTITUDE 3 — CODE                                      The escape hatch   │
│  ───────────────────────────────────────────────────────────────────────── │
│  Unit: the compiled artefact                                              │
│  Actions: view/edit generated CSS · custom CSS scoped to section/site ·   │
│           custom HTML block · view compiled block markup (read-only in v1)│
│  Audience: P3 Deepak, P2's senior dev                                     │
│  UX: a real editor (Monaco), diffed against generated output              │
└────────────────────────────────────────────────────────────────────────────┘
```

**The design principle that makes this work:**
> **Every altitude edits the same model. There is no "you left the visual editor" penalty and no
> one-way door.** Changes at altitude 3 must remain visible and non-destructive at altitude 1.

This is the hardest UX problem in the product and the one most likely to be fudged. Webflow
solves it (custom code is additive and scoped). Elementor fudges it (custom CSS is a black box).
**Get this right and P3 becomes an advocate instead of a critic.**

### The specific rule for the code escape hatch
- Custom CSS is **additive and scoped**, stored as an override layer, never merged destructively
  into generated styles.
- Custom HTML lives in a **contained node** the AI will not rewrite (flagged `ai:frozen`).
- Arbitrary **PHP execution is not in v1**. It's a remote-code-execution surface, it breaks the
  portability promise, and it turns your compiler into a runtime. Ship *snippet insertion into the
  exported theme's `functions.php`* in v2 instead — same user value, no execution in your sandbox.

---

## 2. The five differentiation pillars

### Pillar 1 — **Portable by construction** *(the moat)*
Output is native WordPress block markup + `theme.json` + template files. No runtime plugin
required to render. The site works if you cancel, if you get acquired, if you shut down.

This is not marketing. It's an architectural property with three consequences:
- It answers the Cwicly ghost, which is the #1 objection in this market
- It makes every existing block plugin instantly compatible with your output
- It removes the biggest reason agencies refuse new builders

**And yes — it means users can leave.** Good. Products that must trap users to retain them are
products with a value problem. Retain on velocity and workflow, not on hostage-taking.

### Pillar 2 — **Design-grade generation, not template retrieval**
Every AI WordPress tool on the market today does one of two things: swaps a pre-built template,
or fills a fixed skeleton with AI copy. That's why ZipWP/10Web/Extendify sites are recognisable
at a glance.

Your bar: **a designer looks at the first draft and says "huh, that's not bad" rather than "oh,
it's one of those."** Achieving this means generating *design decisions* (rhythm, contrast,
hierarchy, tension, whitespace) from a token system, not retrieving layouts. See
`05-technical-architecture.md` §4 for how.

**This is the highest-risk, highest-value part of the product.** If you can't clear the bar,
you're a nicer ZipWP.

### Pillar 3 — **Three-altitude control** (§1 above)

### Pillar 4 — **Round-trip, not one-way export** *(the retention engine)*
Ship in v1.5, but architect for it from commit #1.

```
     YOUR CANVAS                            WORDPRESS SITE
   ┌──────────────┐    export/publish     ┌────────────────┐
   │  Design IR   │ ───────────────────▶  │ Block theme +  │
   │  (structure, │                       │ templates +    │
   │   tokens,    │  ◀─────────────────── │ posts/pages    │
   │   content    │    content pull-back  │                │
   │   slots)     │                       │ Companion      │
   └──────────────┘   ▲                   │ plugin (sync   │
                      │                   │ agent only)    │
              design changes republish    └────────────────┘
              WITHOUT clobbering the
              client's content edits
```

**Why this is the whole ballgame:** Udesly has done Webflow→WP for years and stayed niche
*precisely because* every design change means re-export and re-do. One-way export means your
product's job ends at export, which means your LTV is one transaction. **Round-trip is the
difference between a utility and a platform.**

**Design constraint this imposes on v1:** content must be *slot-addressed*, never
position-addressed, from the very first data model. If your IR says "the third paragraph in the
second section," round-trip is impossible forever. If it says
`hero.headline` → `wp:post_id 12 / block uid a7f3`, it works. **This decision is unreversible.
Get it right in week 6.**

### Pillar 5 — **Fast and accessible by default** *(the compliance wedge)*
- Hard performance budget enforced by the compiler: page weight, DOM depth, CSS bytes, LCP
  estimate. Show the score *in the editor, live*, next to a comparison figure for a typical
  Elementor page.
- Semantic HTML, correct landmark/heading structure, focus states, contrast checks against your
  own token system, real alt-text prompting in the AI flow.
- With the European Accessibility Act in force since June 2025, "accessible by default" is a
  procurement checkbox for a growing share of P2's clients. Elementor sells this as a paid add-on
  (Ally). **Making it free and structural is both a moral and a commercial win.**

---

## 3. Moat analysis — what actually defends this

| Candidate moat | Strength | Honest assessment |
|---|---|---|
| **The compiler (IR → native blocks, high fidelity)** | 🟢 Strong | 12–18 months of accumulated edge cases. Hard to replicate, invisible to copy, gets better with every user site. **This is the real moat. Invest here disproportionately.** |
| **Round-trip sync engine** | 🟢 Strong | Genuinely hard distributed-state problem. Compounds with the compiler. |
| **Section/pattern library quality** | 🟡 Medium | Copyable over time, but quality + breadth is a real 12-month lead |
| **Generation quality / prompt+model pipeline** | 🟡 Medium | Model improvements lift everyone. Your *evaluation harness* and design-judgement dataset are the durable part, not the prompts. |
| **Brand/community trust in WordPress** | 🟡 Medium | Slow to build, slow to lose. Kevin Geary proves how valuable this is. Start building now, before you have a product. |
| **Design tokens / systems layer** | 🟡 Medium | Frames/ACSS proved the demand; not defensible alone |
| **The canvas UX itself** | 🔴 Weak | Copyable in 6 months by a funded competitor |
| **BYOK** | 🔴 Weak | A checkbox. Nice, not defensible. |
| **AI models** | 🔴 None | You're renting these. Never position on model quality. |

**Strategic implication:** spend your engineering capital on the compiler and the sync engine.
Spend your marketing capital on community trust. Everything else is table stakes.

---

## 4. Feature architecture (v1 → v2)

```
┌─────────────────────────── AUTHORING ────────────────────────────┐
│ Prompt & brief intake ─▶ Sitemap generation ─▶ Page generation   │  v1
│ Brand token extraction (logo/URL/upload → palette, type, radius) │  v1
│ Section library + variants                                       │  v1
│ 3-altitude editor (section/element/code)                         │  v1
│ Chat-driven revision ("make the pricing 3 columns")              │  v1
│ Version history + rollback                                       │  v1
│ Multi-direction generation (3 concepts side by side)             │  v1.5
│ Motion/interaction editor                                        │  v1.5
│ Shareable client review link + comments                          │  v1.5
│ Team seats, shared libraries, white-label                        │  v2
└──────────────────────────────────────────────────────────────────┘
┌─────────────────────────── CONTENT ──────────────────────────────┐
│ Page content editing in-canvas                                   │  v1
│ AI copywriting (per-section, brand-voice aware)                  │  v1
│ Image sourcing (stock API) + AI image gen                        │  v1
│ Blog/post archetype + archive templates                          │  v1.5
│ Custom post types / content collections → CPT mapping            │  v1.5
│ Forms (mapped to a chosen WP form plugin's blocks)               │  v1.5
│ WooCommerce basic product/archive templates                      │  v2
│ Multilingual (WPML/Polylang aware output)                        │  v2 |
└──────────────────────────────────────────────────────────────────┘
┌──────────────────────────── OUTPUT ──────────────────────────────┐
│ Compile to native block markup + theme.json + templates          │  v1
│ Export as installable .zip block theme + content import          │  v1
│ Output inspector (see the compiled HTML/CSS)                     │  v1
│ Performance + a11y audit panel                                   │  v1
│ Direct publish to a WP site via companion plugin                 │  v1.5
│ Round-trip sync (design ⇄ content)                               │  v1.5
│ Static/headless export (HTML, or Next.js)                        │  v2 (optional) |
│ Git-friendly theme export / CLI                                  │  v2 |
└──────────────────────────────────────────────────────────────────┘
┌────────────────────────── PLATFORM ──────────────────────────────┐
│ Managed AI credits (default)                                     │  v1
│ BYOK — Anthropic / OpenAI / (Gemini)                             │  v1
│ Usage metering + transparent cost display                        │  v1
│ Multi-site dashboard / client workspaces                         │  v2
│ Agency white-label + reseller                                    │  v2
│ Public API + MCP server                                          │  v2 |
└──────────────────────────────────────────────────────────────────┘
```

---

## 5. The design principles (write these on the wall)

1. **The first draft is the product.** Everything else is recovery from a bad first draft. Spend
   disproportionately on generation quality.
2. **Never a one-way door.** Any edit at any altitude must be reversible and non-destructive to
   the others.
3. **Tokens over values.** Nothing in the canvas sets a raw hex or a raw pixel unless the user
   deliberately escapes. This is what makes generated design coherent *and* what makes
   `theme.json` output clean. Two birds.
4. **The compiled output is a first-class UI surface.** Show it. Let people inspect it, be proud
   of it, screenshot it. Your competitors hide theirs for a reason.
5. **Optimise for time-to-first-export, not time-in-app.** Engagement metrics will lie to you
   here. A user who exports in 20 minutes and comes back next week is worth ten who fiddle for
   three hours and churn.
6. **Assume the user is being watched by a sceptical developer.** Because they are (P3).

---

## 6. Things I'd cut from your original concept

| Idea | Verdict | Why |
|---|---|---|
| "Edit code and all things" — full PHP/JS execution in the editor | ✂️ **Cut from v1** | RCE surface, breaks portability, turns you into a runtime. Ship scoped CSS + custom HTML block + (v2) snippets injected into the exported theme. |
| BYOK as the primary/default model | ✂️ **Demote** | Great Pro feature, terrible default. Kills your quality control and your support margin. |
| Serving SMB DIY and pros with one product | ✂️ **Cut** | Opposite needs. Pick pros; serve SMBs *through* pros via a content-only client mode. |
| "Export to WordPress" as the framing | ✂️ **Reframe** | "WordPress is the runtime, we're the authoring environment." Same tech, completely different business. |
| Competing on breadth of widgets/elements | ✂️ **Cut** | Unwinnable vs Elementor's ecosystem. Native blocks means you inherit that ecosystem for free — lean on it. |
| Hosting | ✂️ **Cut, permanently** | Different business, contradicts the portability promise, drags you into the $2.99 knife fight. |
