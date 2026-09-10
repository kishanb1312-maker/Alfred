# AI Website Builder for WordPress — Strategy & Research Dossier

**Working codename:** *Loom* (placeholder — see `09-gtm-and-launch.md` for naming)
**Date:** September 2026
**Status:** Pre-product research. Nothing built yet.
**Author:** Research compiled for Kishan B.

---

## 0. Read this first

You described a product roughly like this:

> A Webflow/Framer-class visual editor, driven by prompts like Lovable/Bolt/Replit, where users
> compose by **section** rather than by widget, can drop into code when they want, and then
> **export the finished site into WordPress**. Optionally using their own Claude/OpenAI key.

That's a good instinct sitting on top of one genuinely unsolved problem and three landmines.
This dossier lays out the market, the competitors (including the ones you didn't name — and
there are a *lot*), the users, the personas, a differentiated position, the architecture that
position implies, a beta scope, a timeline, pricing, GTM, and the risks that kill products
like this.

I'm not going to be polite about the weak spots. That's the point of the exercise.

---

## 1. The one-paragraph thesis

The WordPress page-builder market is huge, mature, and **structurally unhappy**. Elementor is on
32.67% of WordPress sites and page builders in general are on ~60% of them, but the entire
category is defined by a trade-off users hate: *the visual freedom you get is paid for in bloat
and lock-in.* Deactivate the builder and your content turns to shortcode soup. Meanwhile the AI
site-generation wave (Lovable at ~$400M ARR, Replit at ~$525M, Bolt, v0 at 4M+ users) has
proven people will describe a site and accept a generated first draft — but essentially **none
of that wave outputs clean, native WordPress**. The gap is not "AI that makes a website." That's
a commodity now. The gap is:

> **A design-grade visual editor whose output is a real, native, plugin-free WordPress block
> theme — with round-trip sync so design changes don't nuke client content.**

Nobody owns that. That is the wedge.

---

## 2. What I'd change about your framing (the honest bit)

**a) "Export to WordPress" should not be a feature. It should be the product thesis.**
The moment you frame it as "build here, export there," you're a converter — and converters are
low-trust, one-shot, high-churn businesses. Udesly has been converting Webflow→WordPress for
years and remains a niche utility precisely because every design change means a re-export.
Frame it instead as *"WordPress is the runtime, we're the authoring environment."* That changes
the architecture, the pricing, and the retention math. See §4 of `04-product-strategy.md`.

**b) "No blocks or widgets, just sections" is under-specified — and half wrong.**
Webflow and Framer aren't *less* granular than Elementor; they're *more* granular (every div is
addressable). What you actually mean, I think, is: **no widget drawer, no assembling a hero out
of 14 primitives.** You pick a *Hero*, a *Pricing*, a *Testimonial* section and edit inside it.
That's Relume's model, and it's correct — but only if you also give power users element-level
control underneath, or you'll lose the developer segment on day one. The position to hold is
**"section-level composition, element-level control on demand, code-level control when needed."**
Three altitudes, one canvas.

**c) BYOK is a great *feature* and a terrible *default*.**
BYOK protects your gross margin and wins the developer/agency segment (people pay $1–5/mo in raw
API cost instead of $20–249/mo with 300–500% markup). But it hands you: unpredictable quality,
no cost lever, support tickets about *other people's* rate limits, and a straightforward path
for your system prompts to leak. Ship managed credits as the default, BYOK as a Pro/Agency
toggle. Details in `08-pricing-and-business-model.md`.

**d) The real churn risk isn't acquisition. It's "export once, never return."**
If the product's job ends at export, your LTV is one transaction. Every serious decision in this
dossier — round-trip sync, the WP companion plugin, the client-handoff mode, the agency
workspace — exists to solve that. Solve it in the architecture, not in a retention email.

**e) You're entering a market with a fresh graveyard.**
Cwicly — a genuinely well-loved, technically excellent WordPress builder — shut down and left
its users stranded. That memory is live in this community. Your single biggest GTM obstacle is
not "is it good," it's **"will you still be here in three years, and what happens to my client
sites if you're not?"** The answer must be structural (native block output = your product can
die and the sites still work), and you must say it out loud on the homepage. It's also, by a
happy accident, your strongest differentiator.

---

## 3. The position, in one line

> **Design like it's Framer. Ship like it's WordPress core.**

Or the longer version for the site:

> *An AI-native design canvas that outputs clean, native WordPress block themes — no page-builder
> plugin, no shortcode lock-in, no rebuild when you leave.*

---

## 4. Beachhead

**Not** SMB DIY owners. That's the volume segment, it's where Wix/Hostinger/10Web/Big Sky are
already dogfighting on price, the CAC is brutal and churn is 20–40%.

**Beachhead = the solo WordPress freelancer and the 2–10 person boutique agency.** ~210-respondent
industry survey data says the typical WordPress agency in 2026 *is* a solo operator or small team
running anywhere from a handful to 100+ sites. They bill $40–80/hr, they build 2–10 sites a
month, they already pay for Elementor Pro + a theme + a form plugin + a slider, and their #1 pain
is that every client project starts from a blank Elementor canvas and ends with a handoff the
client immediately breaks.

They also have something SMB owners don't: **they buy tools, they have budget, they evangelise
in public, and one of them brings you 30 sites.**

---

## 5. What Beta 1 is (and isn't)

**Is:** Prompt → sitemap → multi-page design in a real canvas → edit sections and elements →
inspect/edit generated CSS → one-click export as an installable native block theme + content →
open it in WordPress and everything is editable in Gutenberg.

**Isn't:** WooCommerce, memberships, multilingual, team collaboration, custom PHP execution,
round-trip sync, marketplace, white-label, mobile app, importing existing Elementor sites.

Full MoSCoW breakdown in `06-beta-scope-and-roadmap.md`.

---

## 6. Timeline at a glance

| Milestone | Lean (3–4 people) | Standard (6–8) | Funded (12–15) |
|---|---|---|---|
| Design partner interviews done | Wk 4 | Wk 3 | Wk 3 |
| Architecture spike: IR → block markup proven | Wk 10 | Wk 7 | Wk 6 |
| Internal alpha (1 page, 1 template) | Wk 20 | Wk 14 | Wk 11 |
| **Private beta (invite, ~50 users)** | **Wk 32 (~7.5 mo)** | **Wk 24 (~5.5 mo)** | **Wk 18 (~4 mo)** |
| Public beta (paid, waitlist open) | Wk 46 (~11 mo) | Wk 34 (~8 mo) | Wk 26 (~6 mo) |
| GA 1.0 | Wk 62 (~14 mo) | Wk 48 (~11 mo) | Wk 36 (~8 mo) |

Full breakdown, staffing, and the honest risk-adjusted version in `07-timeline-and-team.md`.

---

## 7. Document map

| File | What's in it |
|---|---|
| `01-market-and-positioning.md` | Market size, trends, the structural opening, positioning statement, messaging house |
| `02-competitive-landscape.md` | 60+ competitors across 7 categories, deep dives, positioning map, gap analysis |
| `03-user-research-and-personas.md` | Research plan, JTBD, 6 personas + 3 anti-personas, journey maps, pain inventory |
| `04-product-strategy.md` | The three-altitude editing model, differentiation pillars, moat analysis, feature architecture |
| `05-technical-architecture.md` | The IR, generation pipeline, export compiler, round-trip sync, code editing, cost control |
| `06-beta-scope-and-roadmap.md` | Beta 1 MoSCoW, release train through v2, definition of done |
| `07-timeline-and-team.md` | Phase-by-phase timeline, team shapes, budget, critical path, risk-adjusted schedule |
| `08-pricing-and-business-model.md` | Tiers, BYOK economics, unit economics, competitor price table, the LTD question |
| `09-gtm-and-launch.md` | Channel strategy, WordPress community playbook, launch sequence, naming, content engine |
| `10-risks-legal-and-metrics.md` | Risk register, GPL/licensing, accessibility law, security, North Star + metric tree |
| `SOURCES.md` | Every source cited, with dates |

---

## 8. If you only do three things

1. **Prove the compiler before you build the canvas.** Take a hand-designed page, compile it into
   native block markup + `theme.json`, install it on stock WordPress, and confirm it's fully
   editable in Gutenberg with no plugin. If that's not possible at the fidelity you want, the
   entire thesis changes and you need to know that in week 8, not week 30.
2. **Recruit 12 design partners before you write product code.** Solo WP freelancers, from the
   Facebook groups and the Bricks/Etch YouTube comment sections. Pay them. They are your beta,
   your case studies, and your early distribution.
3. **Decide the retention model on day one.** Export-and-leave is a death sentence. Pick one:
   round-trip sync, managed hosting, or a client-editing layer. My vote: round-trip sync first,
   client-editing layer second, hosting never.
