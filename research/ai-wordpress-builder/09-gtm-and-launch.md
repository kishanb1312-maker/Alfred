# 09 — Go-To-Market, Launch & Naming

---

## 1. The one thing to understand about this market

**WordPress is a media-and-community market, not a performance-marketing market.**

Nobody buys a page builder from a Google ad. They buy it because Ferdy Korpershoek made a video,
or Kevin Geary said something spicy about it, or three people in a Facebook group said the output
was clean. Purchase decisions here are made by **social proof from named individuals with
audiences**, and those individuals are technical, opinionated, and allergic to marketing.

Which means: **your GTM starts 6 months before your product.** Not as a waitlist campaign — as a
credibility deposit.

---

## 2. Channel strategy

### Tier 1 — Where you actually win

| Channel | Play | Start |
|---|---|---|
| **YouTube creators** | WPCrafter, WPTuts, Ferdy Korpershoek, Kevin Geary/Geary's channel, Imran Siddiq, Web Squadron, Paul C, Dave Foy. Get the product in their hands *early, free, with no conditions*. Do not ask for a positive review — ask them to try to break it. The video where a sceptic fails to break your export is worth ten sponsored ones. | Month 4 (pre-beta) |
| **Facebook groups & Discords** | Bricks Builder, Etch, Automatic.css, WordPress Website Help, Advanced WordPress, Admin Bar. **Participate for months before you ever mention your product.** These groups can smell a launch account. | Month 1 |
| **WP Tavern / WP Mayor / WPBeginner / Post Status** | Earned coverage, not paid. Pitch the *story* ("someone built an AI builder that outputs no-lock-in native blocks"), not the product. | Month 7 |
| **Founder-led technical content** | Write the deep posts: "How we compile a visual design into native Gutenberg blocks," "We measured our output against Elementor, Bricks and ZipWP — here's the DOM." This community rewards technical honesty enormously. | Month 2, continuous |
| **The uninstall demo** | One 90-second video: build → export → deactivate every plugin → page still perfect → open in Gutenberg → edit. **This single asset does more work than your entire homepage.** | Month 5 |
| **WordCamps / WordPress meetups** | Sponsor small, speak often. Talk about block themes and AI, not about your product. | Month 8+ |

### Tier 2 — Supporting

- **Design communities** for P4 (Nadia): Dribbble, design Twitter/X, Read.cv-adjacent spaces,
  Framer/Webflow subreddits ("my client insists on WordPress" threads are a literal lead list)
- **Product Hunt** — one shot, use it for the public beta, expect a spike and little retention
- **Comparison SEO** — "Elementor alternative," "Webflow to WordPress," "ZipWP vs," "Bricks vs."
  Slow-building, compounding, and the highest-intent traffic in this market
- **Affiliate program** — the WordPress ecosystem runs on affiliate revenue. 25–30% recurring.
  Launch it at GA, not before (you don't want affiliates promoting a beta).

### Tier 3 — Later / careful

- Paid search (expensive, Elementor outbids you, low-intent)
- Hosting partnerships (great distribution, but it drags you toward the Category-C hosting-funnel
  positioning you spent this whole strategy escaping — take these only at v2, and only white-label)
- LTD marketplaces — **no** (see `08-pricing-and-business-model.md` §4)

---

## 3. Launch sequence

```
M1–3  BUILD IN PUBLIC (quietly)
      · Founder posts technical notes weekly. No product, no CTA.
      · Join the communities. Answer questions about block themes. Be useful.
      · Publish an original piece of research: "We analysed the DOM output of
        8 WordPress builders." ← this is link bait, credibility, and your
        positioning argument, all at once. Costs a week. Pays for a year.

M4–5  DESIGN PARTNERS (private)
      · 12 paid partners. NDA-free. Encourage them to talk about it.
      · Waitlist opens with the uninstall demo as the only asset.
      · Target: 2,000 waitlist signups, entirely from community + earned.

M6    PRIVATE BETA (invite)
      · 50 users, hand-onboarded, recorded.
      · Weekly public changelog from day one.
      · Seed 3–5 creators with early access and an explicit "try to break it" brief.

M8    PUBLIC BETA (paid)
      · Product Hunt + WP Tavern + creator videos land the same week.
      · Founders Plan (250 seats, 3-year prepaid) opens — funds the run to GA.
      · Publish the benchmark: your output vs Elementor/ZipWP/Big Sky, with numbers.

M11   GA 1.0
      · Affiliate program opens.
      · Case studies from 10 agencies.
      · Pricing locked, annual plans, regional pricing live.

M14+  v1.5 ROUND-TRIP LAUNCH
      · This is your second launch moment, and arguably the bigger one:
        "your design tool now stays connected to the live site."
```

---

## 4. The content engine (what to actually publish)

Three streams, run continuously:

**Stream 1 — Proof** *(builds credibility with P3, converts P1/P2)*
- Output teardowns: your markup vs everyone else's, with DOM depth and CSS byte counts
- "How the compiler works" technical deep dives
- Live rebuild challenges: "we rebuilt [famous site] in 90 minutes"
- Public performance/accessibility benchmarks, re-run quarterly

**Stream 2 — Craft** *(builds audience with P2/P4)*
- Design system thinking for WordPress
- Section-archetype anatomy ("what makes a hero work")
- Accessibility and the EAA, practically explained for agencies
- Client handoff practices

**Stream 3 — Ecosystem** *(builds goodwill, earns links)*
- The quarterly "State of WordPress Building" survey — run it, publish it, cite it. Within two
  years, other people's articles cite *you*, which is the single most durable marketing asset in
  this space.
- Honest comparison pages, including where competitors beat you. **Say where Bricks is better.
  Say where Elementor is better.** In this community, admitted weakness buys more trust than any
  claimed strength.

---

## 5. Naming

You need a name that survives being said out loud by a YouTuber, doesn't sound like a plugin, and
doesn't box you into WordPress forever (in case v3 goes headless).

**Criteria:** 1–2 syllables · pronounceable globally · .com or a credible .dev/.design ·
trademark-clearable in software · not "WP-anything" (sounds like a $19 plugin) · not
"AI-anything" (dates instantly, and by 2027 it'll read like "e-Business")

**Directions worth exploring:**

| Direction | Examples | Feel |
|---|---|---|
| Craft/making | Loom*, Forge, Lathe, Anvil, Weave, Kiln | Substantial, tool-like, respects the craftsperson (*Loom is taken) |
| Structure | Frame, Scaffold, Lattice, Truss, Strata, Grain | Architectural, appeals to P3 |
| Speed/light | Swift, Flint, Ember, Spark, Prism | Energetic, more consumer |
| Abstract/short | Nomo, Volt, Kite, Verso, Hale | Modern SaaS, needs the tagline to carry meaning |

**My instinct:** something from the craft/structure column. Your entire positioning is
*"professional output, real materials, no fakery"* — a craft name reinforces it every time
someone says it. An abstract name makes you sound like one more AI tool, which is exactly the
category you're trying not to be filed under.

**Whatever you pick, the tagline does the heavy lifting:**
> *"Design like it's Framer. Ship like it's WordPress core."*

---

## 6. The homepage (above the fold)

```
┌──────────────────────────────────────────────────────────────────────┐
│  Design like it's Framer. Ship like it's WordPress core.             │
│                                                                       │
│  Describe your site. Edit it in a real design canvas. Export a clean, │
│  native WordPress block theme — no page-builder plugin, no shortcode  │
│  lock-in, nothing that breaks when you stop paying us.                │
│                                                                       │
│  [ Start free — no card ]   [ Watch: we uninstall everything (0:90) ] │
│                                                                       │
│  ─────────────────────────────────────────────────────────────────    │
│  [ AUTOPLAYING: prompt → site appearing → export → plugins            │
│    deactivated → page still perfect → edited in Gutenberg ]           │
└──────────────────────────────────────────────────────────────────────┘
```

The second CTA is the important one. In a market this sceptical, **the demo that proves the
scary claim outperforms the demo that shows the exciting one.**

---

## 7. Objection handling (write these answers before you need them)

| Objection | Answer |
|---|---|
| *"Another AI builder that makes generic sites."* | "Try it and compare. Here's our output next to ZipWP, 10Web and Big Sky, same brief." Then show it. Never argue — demonstrate. |
| *"What happens when you shut down?"* (**the Cwicly question**) | "Your sites keep working, because they don't depend on us. That's architectural, not a promise. Here's the uninstall video." This is the objection you're *most* prepared for — treat it as a gift. |
| *"The output will be bloated."* | Open the inspector. Show the DOM. Publish the benchmark. |
| *"I can just use Elementor + AI."* | "You can. You'll also still have Elementor on 40 client sites in 2030." |
| *"Why monthly? Everything in WordPress is annual."* | "Because inference and sync cost us money every month. Annual is available at 2 months free, and regional pricing is live." |
| *"Can I edit the code?"* | Yes — scoped CSS, custom HTML, and full visibility into the compiled output. PHP snippets in v2. Be honest about the current limit rather than vague. |
| *"Does it work with my plugins?"* | "Better than a page builder does — the output is native blocks, so every block plugin, ACF, form plugin and SEO plugin works normally." **This is a genuinely strong answer; use it more than you think.** |
