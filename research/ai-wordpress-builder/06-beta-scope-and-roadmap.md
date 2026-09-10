# 06 — Beta Scope & Roadmap

---

## 1. Release train

| Release | Name | Audience | Gate to enter |
|---|---|---|---|
| **M0** | Compiler spike | Internal only | — |
| **M1** | Internal alpha | Team + 3 friendlies | 1 page compiles clean, installs on stock WP |
| **M2** | **Private Beta** | ~50 invited design partners | Full happy path works end to end |
| **M3** | **Public Beta (paid)** | Waitlist, open | 20 real client sites shipped by beta users |
| **M4** | **GA 1.0** | Open | Reliability + support load sustainable |
| **v1.5** | Round-trip release | Existing | Sync engine stable on 100 sites |
| **v2** | Agency release | Teams | — |

---

## 2. M0 — The Compiler Spike *(do this first, before anything else)*

**This is a go/no-go gate for the entire company.** Six weeks, one or two engineers, no UI.

**Deliverable:** a CLI that takes a hand-authored IR JSON for one realistic 6-section landing
page and emits an installable WordPress block theme (`theme.json`, `templates/`, `patterns/`).

**Pass criteria — all of them, no negotiating:**
- [ ] Installs on stock WordPress with **no plugins active**
- [ ] Renders pixel-accurate to the design at 3 breakpoints (≤2% visual diff)
- [ ] Every section is editable in the stock block editor and survives a save/reload round-trip
- [ ] `post_content` contains **zero** shortcodes and zero custom block namespaces
- [ ] ≤3 wrapper divs average per section; ≤60KB compiled CSS
- [ ] Lighthouse ≥95 perf, ≥95 a11y
- [ ] Slot UIDs present in block attributes and readable back via the REST API

**If you fail on fidelity:** narrow the design space the canvas allows (option 1 in
`05-technical-architecture.md` §3) and re-test. **If you fail on editability:** the entire
positioning changes and you need to know now.

**Also in M0:** the **eval harness skeleton**. 20 golden briefs, deterministic checks. It will
feel premature. Do it anyway — every week you delay it, generation quality becomes more
subjective and more argued-about.

---

## 3. M2 — Private Beta scope (MoSCoW)

### ✅ MUST — no product without these

| # | Feature | Notes |
|---|---|---|
| 1 | Prompt → brief → **sitemap** (editable) | Relume's flow. Users must be able to edit the sitemap before generation. |
| 2 | Brand token setup: upload logo *or* paste a URL → extract palette + type; manual override | Contrast auto-verified |
| 3 | **Multi-page generation** (up to ~8 pages) | Single-page generation is a demo, not a product |
| 4 | Section library: **~60 archetypes × 3–5 variants** | Hero, features, pricing, testimonial, logo cloud, FAQ, CTA, about, team, stats, contact, footer, nav, blog list, gallery, steps/process, comparison |
| 5 | **Altitude 1** — section editing: swap variant, regenerate, reorder, duplicate, delete, inline content edit, section-level style params | The 90% surface |
| 6 | **Altitude 2** — element inspector: layout, spacing, type, colour (token-bound), 3 breakpoints | |
| 7 | **Altitude 3** — code panel: view compiled HTML/CSS (read-only), add scoped custom CSS, custom HTML block | No PHP |
| 8 | Chat-driven revision on a selected section | "Make this 3 columns", "warmer tone", "swap the image side" |
| 9 | AI copy per section, brand-voice aware, incl. **alt text** | |
| 10 | Image handling: upload, stock API search, AI generation, auto-optimise (WebP/AVIF, sizes) | |
| 11 | Version history + rollback + named checkpoints per AI generation | Non-negotiable trust feature |
| 12 | **Export**: `.zip` block theme + WXR content import + a 3-step install guide | The moment of truth |
| 13 | **Output inspector**: side-by-side compiled markup + perf/a11y audit | Deepak's panel. Also your best marketing asset. |
| 14 | Managed AI credits, metered, with live cost display | |
| 15 | **BYOK** (Anthropic + OpenAI) | Pro toggle |
| 16 | Responsive editing at 3 breakpoints | |
| 17 | Basic SEO: title/meta/OG per page, semantic heading structure, sitemap-friendly output | |
| 18 | Onboarding that reaches first generated site in **under 10 minutes** | Instrument it. It's your activation metric. |

### 🟨 SHOULD — in if the schedule allows, cut without drama if not

- Multi-direction generation (3 concepts side by side) — *strong sales feature, real cost*
- Shareable read-only preview link for client review
- Blog post archetype + archive template
- Import brand from an existing site URL (screenshot + DOM analysis)
- Basic motion presets (entrance, hover, scroll reveal) — *compiles to CSS only, no JS runtime*
- Dark mode variant generation
- Form section mapped to a chosen WP form plugin's native blocks

### 🟦 COULD — nice, not now

- Figma import
- Comments/annotations on the canvas
- Template starting points ("start from a template, not a prompt")
- Keyboard-first command palette
- Content generation from an uploaded brand/brief document

### ⛔ WON'T — explicitly out of Private Beta (say this to users up front)

| Excluded | Lands in |
|---|---|
| Round-trip sync | v1.5 |
| Direct publish to a live site (export-only for now) | v1.5 |
| Custom post types / dynamic collections | v1.5 |
| WooCommerce | v2 |
| Multilingual | v2 |
| Team seats / shared libraries / white-label | v2 |
| PHP snippets or custom blocks | v2 |
| Membership/LMS/booking integrations | ✗ |
| Hosting | ✗ ever |
| Importing an existing Elementor/Divi site | evaluate in v2 |
| Mobile/tablet authoring app | ✗ |

**Publish this WON'T table to beta users on day one.** Half of beta support load is expectation
management, and a public non-roadmap is the cheapest fix available.

---

## 4. Definition of Done — Private Beta

The beta is ready when a design partner who has never seen the product can, unassisted:

1. Sign up, describe a real client's business, and get a generated 5-page site in **< 10 minutes**
2. Adjust brand tokens and see the whole site update coherently
3. Regenerate 3 sections and swap 2 variants without breaking anything
4. Add one piece of custom CSS and have it survive a regeneration
5. Export, install on a fresh WordPress, and see it render identically
6. Open the exported page in Gutenberg and edit the headline
7. Deactivate every plugin and confirm the page still renders

…and do all of it **without the founders in the room.** If step 5, 6 or 7 needs hand-holding, you
don't have a beta; you have a services business.

---

## 5. Public Beta gate (M2 → M3)

Do **not** open the doors until:

- [ ] ≥20 real client sites built and **launched** by beta users (not demos — live, paid work)
- [ ] Median time-to-first-export < 45 minutes
- [ ] Export success rate > 95% (no manual fixes needed)
- [ ] ≥8 of 10 sampled beta users say they'd be "very disappointed" if the product vanished
      (Sean Ellis PMF test — under 40% "very disappointed" means you're not ready, full stop)
- [ ] Security audit of the companion plugin complete, findings closed
- [ ] Support load < 1.5 tickets per active user per month
- [ ] At least 2 respected WordPress developers have publicly inspected the output and not hated it

That last one is soft, unquantifiable, and probably the most important item on the list.

---

## 6. Post-GA roadmap

### v1.5 — "It's alive" (≈ GA + 3–4 months)
**Theme: stop being a one-way export tool.**
- Round-trip sync + companion plugin publish
- Custom post types / content collections
- Client review links with comments
- Multi-direction generation
- Motion editor
- Blog/archive/single templates

### v2 — "For agencies" (≈ GA + 9–12 months)
**Theme: seats, systems, scale.**
- Team workspaces, roles, shared section & token libraries
- White-label export and client-facing content-only editor
- Multi-site dashboard
- WooCommerce basics (product, archive, cart/checkout templates)
- Multilingual-aware output
- PHP snippets → exported theme
- Public API + MCP server (let people drive you from Claude Code — you of all people should ship this)
- Reseller / partner program

### v3+ — optional bets, pick at most one
- Static/headless export (Next.js) — opens a new market, dilutes the WordPress story
- Import & convert existing Elementor/Divi sites — enormous growth lever, enormous engineering cost
- Marketplace for third-party sections — ecosystem flywheel, moderation burden
- Agentic maintenance ("keep this site's design system in sync across 40 client sites")

**My pick, if you're asking:** the Elementor import converter. It's the single biggest wedge into
an installed base of 10M sites, it's the most defensible thing you could build second, and it
turns your competitor's market share into your funnel.
