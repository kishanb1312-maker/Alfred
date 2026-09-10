# 05 — Technical Architecture

> This is a strategy document, not an engineering spec — but the architecture *is* the strategy
> here, so the important decisions are made explicit. Every one of these has a business
> consequence noted.

---

## 1. System overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT (browser)                                │
│  ┌────────────┐  ┌──────────────────────────┐  ┌─────────────────────────┐  │
│  │ Chat /     │  │   CANVAS                 │  │ Inspector               │  │
│  │ prompt     │  │   iframe-isolated live   │  │ · Section panel (alt 1) │  │
│  │ panel      │  │   render of the IR       │  │ · Element panel (alt 2) │  │
│  │            │  │                          │  │ · Code panel (alt 3)    │  │
│  └────────────┘  └──────────────────────────┘  └─────────────────────────┘  │
│         └───────────────── local IR store (CRDT/Yjs) ──────────────────┘    │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │ WebSocket + REST
┌───────────────────────────────────▼──────────────────────────────────────────┐
│                                 BACKEND                                       │
│  ┌───────────────┐ ┌──────────────┐ ┌─────────────┐ ┌────────────────────┐  │
│  │ Generation    │ │ IR service   │ │ Compiler    │ │ Asset service      │  │
│  │ orchestrator  │ │ (versioning, │ │ IR → blocks │ │ (images, optimise, │  │
│  │ (LLM calls,   │ │  history,    │ │ + theme.json│ │  CDN, AI images)   │  │
│  │  BYOK router, │ │  CRDT merge) │ │ + templates │ │                    │  │
│  │  eval gates)  │ │              │ │             │ │                    │  │
│  └───────┬───────┘ └──────────────┘ └──────┬──────┘ └────────────────────┘  │
│          │                                 │                                 │
│  ┌───────▼──────────────┐        ┌─────────▼──────────┐  ┌───────────────┐  │
│  │ Model providers      │        │ Export packager    │  │ Sync engine   │  │
│  │ Anthropic / OpenAI / │        │ (.zip theme +      │  │ (v1.5)        │  │
│  │ user's own key       │        │  WXR content)      │  │               │  │
│  └──────────────────────┘        └─────────┬──────────┘  └───────┬───────┘  │
└─────────────────────────────────────────────┼──────────────────────┼─────────┘
                                              │ download / push      │
┌─────────────────────────────────────────────▼──────────────────────▼─────────┐
│                          USER'S WORDPRESS SITE                                │
│   Native block theme (no runtime dependency)  +  Companion plugin (optional,  │
│   sync agent + content-lock mode only — NOT required for rendering)           │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. The Design IR — the single most important decision in the product

Everything hangs off this. Get it wrong and you can't round-trip, can't compile cleanly, and
can't ship a code escape hatch that survives regeneration.

### Requirements
1. **Serialisable, diffable, versionable** — it's the unit of history, collaboration and sync
2. **Stable identity per node** — every node has a UID that survives regeneration and reordering
3. **Slot-addressed content** — content is referenced by semantic slot, never by DOM position
4. **Token-referential styling** — styles reference tokens, not raw values
5. **Losslessly compilable to native block markup** — if it can't compile, the canvas mustn't
   allow it
6. **Annotatable** — nodes carry provenance (`ai:generated` / `user:edited` / `ai:frozen`)

### Sketch

```jsonc
{
  "version": "1",
  "site": {
    "tokens": {
      "color":   { "brand-600": "#1F4FD8", "surface": "#FFFFFF", "ink": "#0B1020" },
      "space":   { "scale": "1.25", "base": "1rem" },
      "type":    { "family-display": "Instrument Sans", "scale": "major-third" },
      "radius":  { "md": "0.5rem" },
      "density": "comfortable"
    },
    "breakpoints": ["sm","md","lg"]
  },
  "pages": [{
    "uid": "pg_home", "slug": "/", "title": "Home",
    "sections": [{
      "uid": "sec_a7f3",
      "archetype": "hero.split-media",
      "variant": "v3",
      "provenance": "ai:generated",
      "slots": {
        "headline":  { "uid": "sl_h1", "type": "richtext", "value": "..." },
        "sub":       { "uid": "sl_p1", "type": "richtext", "value": "..." },
        "cta":       { "uid": "sl_c1", "type": "link",     "value": {...} },
        "media":     { "uid": "sl_m1", "type": "image",    "asset": "ast_991" }
      },
      "layout": { "columns": [7,5], "align": "center", "padY": "space.10" },
      "style":  { "bg": "color.surface", "textColor": "color.ink" },
      "overrides": { "css": null },
      "compiles_to": "core/group > core/columns"
    }]
  }]
}
```

**The critical property:** `sec_a7f3` and `sl_h1` are stable. When the AI regenerates the hero,
slot UIDs are *preserved by matching archetype+role*, so the client's edited headline survives.
When you round-trip, you look up `sl_h1` and know exactly which block attribute on which post to
read back. **Without stable slot identity, round-trip is mathematically impossible.**

---

## 3. The compiler — IR → native WordPress

### What "native output" must mean (non-negotiable)

| Requirement | Test |
|---|---|
| Renders with your plugin uninstalled | Deactivate everything, load the page. Pixel-identical. |
| Editable in the stock block editor | Open in Gutenberg. Every section is a recognisable, editable block structure. |
| No shortcodes | `grep '\[' post_content` returns nothing builder-shaped |
| Styles primarily via `theme.json` + a single compiled stylesheet | Not 400 inline `style=` attributes |
| Semantic, shallow DOM | Compare wrapper depth against a hand-built Bricks page. Publish the comparison. |

### Compilation targets

```
IR section  ──▶  strategy chosen per archetype:
                 ├── (a) core blocks only  → core/group, core/columns, core/heading,
                 │                            core/paragraph, core/image, core/buttons
                 ├── (b) core blocks + block-level styles from theme.json variations
                 └── (c) a registered *block pattern* (patterns are just serialised core
                          blocks — zero runtime dependency, fully editable)
```

**Recommended primary strategy: (c) patterns composed of (a) core blocks.** Block patterns are
the perfect vehicle: they're native, they're just markup, they're editable, they carry no
dependency, and they're already how WordPress thinks about "sections." *Your entire product is,
architecturally, a very good pattern generator with a design canvas on top.* Say that to a
WordPress developer and watch them relax.

### The escape valve you'll need
Some designs won't map cleanly to core blocks (complex overlaps, unusual grid, motion). Options,
in order of preference:
1. **Constrain the canvas** so it can only express what compiles. Boring, correct, ships.
2. **A single tiny "layout primitive" block** shipped inside the exported theme (not a separate
   plugin) — a themed block, so uninstalling *your* SaaS changes nothing.
3. ❌ A runtime plugin. **This is how you become Elementor. Refuse it.**

**Take option 1 for v1 and option 2 only when you have evidence from real user designs.** If you
reach for option 2 in month 3, you've lost the plot.

### Fidelity budget (set these targets now, measure from the first spike)
- ≥95% of generated sections compile with zero visual delta at 3 breakpoints
- ≤3 wrapper elements average per section
- ≤60KB compiled CSS for a typical 6-section page
- 0 inline `!important`
- Lighthouse ≥95 performance / ≥95 a11y on the generated starter site

---

## 4. The generation pipeline (why yours can be better than ZipWP's)

The reason every AI WordPress builder produces samey output is that they generate at the wrong
level: they pick a template and fill it. Generate **design decisions**, then **compose**.

```
USER INPUT: prompt · industry · optional logo/URL · optional reference sites · tone
                              │
          ┌───────────────────▼─────────────────────┐
   STAGE 1│ BRIEF EXTRACTION                        │  small/fast model, structured output
          │ → audience, goals, tone, CTA hierarchy, │  cheap, cacheable
          │   content inventory, competitor context │
          └───────────────────┬─────────────────────┘
          ┌───────────────────▼─────────────────────┐
   STAGE 2│ DESIGN DIRECTION                        │  frontier model
          │ → token set (palette w/ verified contrast│ THIS is where "not templated"
          │   ratios, type pairing + scale, spacing  │ is won or lost. Generate a
          │   rhythm, radius, density, motion feel)  │ SYSTEM, not a look.
          └───────────────────┬─────────────────────┘
          ┌───────────────────▼─────────────────────┐
   STAGE 3│ SITEMAP + PAGE NARRATIVE                │  Relume's insight, done properly
          │ → pages, and per page an ordered list of │ Output: archetypes + intent,
          │   SECTION ARCHETYPES with intent         │ NOT layouts yet
          └───────────────────┬─────────────────────┘
          ┌───────────────────▼─────────────────────┐
   STAGE 4│ SECTION COMPOSITION (per section)       │  parallel, per-section
          │ → choose archetype variant, set layout   │ constrained decoding against
          │   params, allocate emphasis, pick media  │ the IR schema — the model
          │                                          │ CANNOT emit invalid IR
          └───────────────────┬─────────────────────┘
          ┌───────────────────▼─────────────────────┐
   STAGE 5│ CONTENT                                 │  brand-voice-aware copy,
          │ → headlines, body, CTAs, alt text, meta  │ real alt text (a11y!)
          └───────────────────┬─────────────────────┘
          ┌───────────────────▼─────────────────────┐
   STAGE 6│ CRITIQUE & REPAIR                       │  ← the differentiator nobody does
          │ → automated checks: contrast, hierarchy, │ Programmatic checks + a
          │   repetition, rhythm consistency, CTA    │ vision-model design critique
          │   density, a11y, perf budget             │ pass. Repair, then re-check.
          └───────────────────┬─────────────────────┘
                        VALID IR → canvas
```

**Four things to internalise:**

1. **Constrained decoding against the IR schema.** The model emits structured IR, never HTML.
   This eliminates an entire class of failure (invalid markup, uncompilable output) and is why
   your compiler can guarantee clean results. Tools that generate raw HTML are gambling.
2. **Stage 6 is your quality moat.** Everyone runs stages 1–5. Almost nobody runs an automated
   design critique and repair loop. It's also cheap — the checks are mostly deterministic.
3. **Build the eval harness before the generator.** A golden set of 50 briefs, scored on: does it
   compile, contrast pass rate, layout variety across runs (measure it — this is the anti-sameness
   metric), perf budget, and a blind human design-quality rating vs ZipWP/Big Sky/Elementor AI
   output. **You cannot improve generation quality you cannot measure**, and "it looks good to me"
   is not a measurement.
4. **Cache aggressively.** Stages 1–3 are cheap and cacheable. Stage 4 parallelises per section.
   Regeneration of one section must never re-run the whole pipeline.

---

## 5. BYOK — how to do it without regretting it

```
      request ──▶ ┌─────────────────────────┐
                  │ Provider Router          │
                  │  ├ managed pool (default)│──▶ your Anthropic/OpenAI accounts
                  │  └ user key (Pro/Agency) │──▶ user's key, server-side only
                  └───────────┬──────────────┘
                              ▼
                  ┌──────────────────────────┐
                  │ Metering + cost display   │  every call logged w/ token counts
                  │ Rate limit + retry/fallback│  fallback to managed pool on user
                  └──────────────────────────┘  quota errors (with consent)
```

**Rules:**
- Keys are **encrypted at rest (envelope encryption, per-tenant DEK), never sent to the browser,
  never logged**, and revocable. Publish this in a security page — P2/P3 will ask.
- **BYOK does not expose your prompts.** Route through your backend so the user's key can't be
  used to dump your system prompts via a proxy. (They can still infer them from outputs. Accept
  that; your moat is the compiler and evals, not the prompt text.)
- **Show live cost.** "This regeneration cost you ~$0.04." Transparency here is a *feature* — it's
  exactly what makes Elementor's credit model feel extractive by comparison.
- **Cap and warn.** A runaway agent on a user's key is a support incident and a trust incident.
- Support **Anthropic + OpenAI at launch**, Gemini in v1.5, OpenRouter/local in v2 if asked.

**Business consequence:** BYOK users have near-zero COGS but also lower switching cost. Price
BYOK plans on *seats and features*, not usage, and make the managed tier genuinely more
convenient (better models, no setup, higher rate limits).

---

## 6. The canvas

| Decision | Recommendation | Why |
|---|---|---|
| Render approach | **Real DOM in a sandboxed iframe**, rendering the same CSS the compiler emits | WYSIWYG fidelity is non-negotiable; if the canvas and the export differ, you have two products. Canvas-based (Figma-style) rendering would give you nicer manipulation and a fidelity nightmare. |
| Framework | React + a thin custom renderer over the IR | Standard, hireable |
| State | **CRDT (Yjs)** even in v1 single-player | Retrofitting collaboration later is agony. Costs you ~2 weeks now, saves ~2 months in v2. |
| Style system | Compile IR → CSS custom properties from tokens; same output in canvas and export | One pipeline, one truth |
| Code editing | Monaco, with generated CSS read-only + an additive override layer | Keeps regeneration non-destructive |
| Undo/history | IR-level snapshots + CRDT history, named checkpoints per AI generation | Users must be able to say "go back to before the AI touched it" |

---

## 7. Round-trip sync (v1.5, architected in v1)

The problem: after export, the client edits content in WordPress. The designer changes the design
in your canvas. Neither should destroy the other.

**Model: content lives in WordPress, design lives in the IR, and they meet at slot IDs.**

- Export writes block markup with a stable slot UID in block attributes (e.g. a `metadata.name`
  or a custom attribute the block editor preserves).
- The companion plugin exposes a read/write endpoint over the REST API, authenticated with an
  application password or a scoped token.
- **Pull:** read all slot values from the live site → update IR content.
- **Push:** recompile design → write back **only** structure and styles, preserving slot content
  unless explicitly overridden.
- **Conflicts:** three-way merge on slot content, with a UI. Design conflicts don't exist — design
  is authored in exactly one place, on purpose.
- **Deletions/reorders:** slot UID is the anchor. A slot that disappears from the design flags a
  "content orphaned" warning rather than silently dropping the client's copy.

**Constraint on v1 that this creates:** the export must already emit slot UIDs, even though
nothing reads them yet. Cheap now, impossible to retrofit onto sites already exported.

---

## 8. Security (don't skip — you're generating code and touching people's sites)

| Surface | Mitigation |
|---|---|
| Custom HTML/CSS from users | Sanitise on compile; CSP in the canvas iframe; no `<script>` in v1 |
| Arbitrary PHP | **Not supported in v1.** In v2, snippets are written to the exported theme and executed only on the user's own server, never yours. |
| Companion plugin REST endpoints | Scoped capability checks, nonce/token auth, rate limiting, signed payloads. **A vulnerable companion plugin on 5,000 client sites is a company-ending event.** Budget a third-party audit before public beta. |
| BYOK keys | Envelope encryption, per-tenant DEK, never client-side, audit log, one-click revoke |
| Prompt injection via user content/URLs | Treat scraped reference sites and imported content as untrusted; never let them steer tool calls |
| Generated content liability | Image licensing (stock API terms), AI image provenance, copy plagiarism checks |
| Multi-tenancy | Hard isolation of IR data and assets; per-tenant asset URLs |

**Do a real pen test before public beta.** In the WordPress ecosystem, a security incident isn't
a bug — it's a WP Tavern headline and a permanent Google result.

---

## 9. Suggested stack (opinionated, adjust to your team)

| Layer | Pick | Note |
|---|---|---|
| Frontend | React + TypeScript, Vite, Yjs, Monaco, Radix/Tailwind for chrome | |
| Canvas | Sandboxed iframe + postMessage bridge | |
| Backend | TypeScript (Node/Bun) or Go; Postgres + Redis; S3-compatible object store | Boring is correct here |
| Compiler | Isolated service, pure function IR→artifacts, heavily unit-tested with golden files | **Golden-file testing is how you keep fidelity from regressing.** |
| LLM orchestration | Direct provider SDKs + your own router. Avoid heavy frameworks; you need control over structured output and cost accounting. | |
| Eval harness | Own it. Golden briefs, deterministic checks, human rating UI, run in CI. | |
| WP companion plugin | PHP 8.1+, block-editor-aware, PHPCS + WPCS, tested on WP 6.5→latest | |
| Infra | Containers on a boring PaaS. Don't build a platform team for a beta. | |
