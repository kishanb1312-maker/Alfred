# 08 — Pricing & Business Model

---

## 1. What the market currently pays

| Product | Price | Model |
|---|---|---|
| Elementor Pro | ~$59–$399/yr by site count | Annual licence per site tier |
| Elementor AI | $48/yr for 24k credits → $192/yr for 100k | **Metered credits.** 1 credit = text prompt, 33 = image, 40 = container. Widely criticised as expensive. |
| Elementor One | $168/yr, 1 site, 25k credits/mo + Ally + image optimisation | Bundle play |
| Divi | $89/yr or $249 lifetime | Unlimited sites |
| Divi Pro | $277/yr | **Unlimited AI** + Quick Sites — the aggressive anti-credit position |
| Divi AI standalone | $24/mo or $288/yr | Unlimited |
| Bricks | $79–$99/yr, ~$249–$299 lifetime | Unlimited sites |
| Breakdance / Oxygen | ~$129–$249 | Lifetime-flavoured |
| ZipWP | Free tier (sites expire in 24h) → paid | Freemium funnel to Astra ecosystem |
| 10Web | $10–$60/mo | **Hosting-bundled** |
| Hostinger AI | from $2.99/mo | Hosting-bundled |
| WordPress.com AI | 30 free prompts, then any paid plan | Hosting-bundled |
| Relume | $0–$40/mo ($26 Starter) | SaaS, seat-based |
| Webflow | $14–$39/site/mo + workspace seats | SaaS |
| Framer | $5–$30/site/mo + seats | SaaS |
| Lovable / Bolt / v0 | ~$20–$50/mo hobby, $100–$250 team | Credit-metered SaaS |

**Three things to read off this table:**

1. **The WordPress market is anchored to *annual licences*, often with a lifetime option.** SaaS
   monthly pricing is culturally unusual here and will meet resistance. You're going to charge
   monthly anyway (you have real COGS), so you must justify it with something obviously ongoing —
   AI inference and sync are that justification. **Say it explicitly on the pricing page.**
2. **Metered AI credits are the most disliked pricing model in this space.** Divi is winning
   arguments purely by saying "unlimited." Do not build your headline plan on credits.
3. **Hosting-bundled AI builders have set the floor at ~$3/mo.** You cannot and must not compete
   there. You are selling professional output, not a website.

---

## 2. Recommended pricing

```
┌──────────────┬──────────────┬──────────────────┬─────────────────┐
│  FREE        │  SOLO        │  PRO             │  AGENCY         │
│  $0          │  $19/mo      │  $39/mo          │  $99/mo         │
│              │  $180/yr     │  $372/yr         │  $948/yr        │
├──────────────┼──────────────┼──────────────────┼─────────────────┤
│ 1 project    │ 3 active     │ Unlimited        │ Unlimited       │
│ Full canvas  │ projects     │ projects         │ projects        │
│ Watermarked  │              │                  │ 3 seats incl.   │
│ preview only │ Full export  │ Full export      │ (+$25/seat)     │
│ NO EXPORT    │              │                  │                 │
│              │ Fair-use AI  │ Fair-use AI      │ Higher AI limit │
│ 30 AI gens   │ (soft cap)   │ (higher cap)     │                 │
│              │              │                  │                 │
│              │ Core section │ + Premium        │ + Shared team   │
│              │ library      │   sections       │   libraries     │
│              │              │ + Code panel     │ + White-label   │
│              │              │ + BYOK           │ + Client seats  │
│              │              │ + Round-trip     │ + Multi-site    │
│              │              │   sync (v1.5)    │   dashboard     │
│              │              │                  │ + Priority supp │
└──────────────┴──────────────┴──────────────────┴─────────────────┘
                    + BYOK DISCOUNT: −$8/mo on any paid tier
```

### The reasoning, decision by decision

**Free tier gates on *export*, not on features.** Let people build a whole site, fall in love,
and hit the wall at the one moment they're most motivated to pay. Gating features makes the
product feel bad; gating export makes the *decision* feel obvious. (This is exactly ZipWP's
24-hour-expiry trick, done less annoyingly.)

**Fair-use, not credits.** Say "unlimited, subject to fair use" and publish the actual soft caps
in the docs. Divi has proven this wins the argument against Elementor. Your real protection is
the cap plus the BYOK escape valve for heavy users — which conveniently converts your most
expensive users into your cheapest.

**$19 entry.** Below Relume's $26, comfortably above the hosting-bundle noise, and roughly one
tenth of one hour of P1 Ravi's billing rate. If the product saves him two hours on one site, the
ROI argument is over in a sentence.

**$39 Pro is the volume tier and the one you optimise.** Unlimited projects + code panel + BYOK +
sync. This is where P1 and P2 land.

**$99 Agency with seats.** For a 6-person shop billing $700k/yr, $948/yr is a rounding error and
your seat expansion is the growth engine. Land at Pro, expand into Agency.

**The BYOK discount is deliberate and counterintuitive.** Give money back for BYOK. It costs you
nothing (you lose the inference COGS and the margin on it simultaneously), it makes the
transparency story real rather than performative, and it converts the exact segment — developers,
P3 — most likely to distrust you into people who feel respected. **Discounting for BYOK is the
cheapest trust purchase available to you.**

---

## 3. Unit economics

### Managed-inference user (Pro, $39/mo)

| Line | Estimate |
|---|---|
| Revenue | $39.00 |
| AI inference (typical: ~2 full site gens + ~40 section regens/mo) | $4.50 – $12.00 |
| Image generation + stock API | $1.00 – $3.00 |
| Infra (storage, assets, compute) | $1.50 |
| Payment processing | $1.40 |
| Support (amortised) | $3.00 |
| **Gross margin** | **$18 – $27 (46–70%)** |

That's thin for SaaS and it's the *whole reason* BYOK matters.

### BYOK user (Pro, $31/mo after discount)

| Line | Estimate |
|---|---|
| Revenue | $31.00 |
| AI inference | **$0** |
| Everything else | $6.90 |
| **Gross margin** | **$24 (78%)** |

**BYOK users are more profitable than managed users despite paying less.** Push power users
toward it enthusiastically. This is one of the rare cases where the honest option and the
profitable option are the same option.

### The heavy-user risk
A single agency running 40 site generations a month on managed inference can cost you $80–200 in
tokens against $99 of revenue. Mitigations, in order:
1. Soft caps with a friendly "you're in the top 1%, want to switch to your own key?" prompt
2. Aggressive caching (stages 1–3 of the pipeline are cheap and reusable)
3. Cheap/fast models for stages 1, 5 and parts of 6; frontier model only for stages 2–4
4. Hard cap + overage at cost, clearly disclosed

### Blended targets to aim for by GA+12mo
| Metric | Target |
|---|---|
| Blended ARPU | $28–$35/mo |
| Gross margin | 70%+ |
| Monthly logo churn | < 4% (< 3% on annual) |
| Annual plan mix | > 45% (WordPress buyers *like* annual — lean into it) |
| CAC payback | < 5 months (community-led GTM should make this achievable) |
| LTV:CAC | > 3.5:1 |

---

## 4. The lifetime deal question — my answer is no

You will be asked. AppSumo will email you. A WordPress lifetime-deal site will offer to feature
you. Half your competitors did it (Bricks, Oxygen, Divi, Etch).

**Don't. Here's why, specifically for *this* product:**

- Your COGS are **ongoing and per-use**. Bricks has near-zero marginal cost per site; you have an
  inference bill for the life of the account. A lifetime deal on an AI product is selling an
  uncapped liability for a one-time fee.
- LTD buyers are the **highest-support, lowest-fit** cohort. They buy on impulse and price, not on
  fit, and they arrive during the exact months when your support capacity is thinnest.
- It **destroys your MRR narrative** for 24 months and makes fundraising or acquisition harder.
- It **anchors the price** permanently. You never fully recover.

**If you must do something LTD-shaped**, do a **Founders Plan**: a limited run (250 seats) of a
*3-year* prepaid Pro at ~$399, with an explicit AI fair-use cap and a written policy on what
happens after year 3. Time-boxed, capped, honest. It funds the beta without mortgaging the
company.

---

## 5. Business model risks

| Risk | Severity | Mitigation |
|---|---|---|
| **"Export once and cancel"** — user builds a site, exports, cancels | 🔴 Critical | The entire v1.5 round-trip roadmap exists for this. Also: annual plans, per-project value (they build 3–8 sites/mo, so they need you continuously), agency workspaces. **Track "sites exported per active account per month" as a leading retention indicator from day one.** |
| Model price/quality shifts under you | 🟠 High | Provider abstraction from day one; BYOK as a hedge; never position on a specific model |
| A hosting company bundles an equivalent for free | 🟠 High | Don't sell to the segment that buys on price. Sell to people whose deliverable quality *is* their income. |
| Elementor/Automattic ships something close | 🟠 High | Speed + the portability position they structurally cannot copy |
| Support load exceeds margin | 🟡 Medium | Docs, video, community forum, the published WON'T list, and a support hire *before* public beta |
| Inference cost spike | 🟡 Medium | Caching, model tiering, soft caps, BYOK migration path |
| Currency/geography price sensitivity (large freelancer pools in India, SE Asia, LatAm, Eastern Europe) | 🟡 Medium | **Regional pricing from launch.** Your beachhead persona is disproportionately in these markets. A flat $39 excludes a huge chunk of your best-fit users. Purchasing-power pricing here is not charity, it's TAM. |
