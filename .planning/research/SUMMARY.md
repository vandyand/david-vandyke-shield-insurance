# Research Summary: Traffic & Conversion Strategy
# David VanDyke Insurance — Facebook Ads + Niche Landing Pages

**Domain:** Local independent insurance agent, two-pronged paid traffic + CRO
**Researched:** 2026-03-25
**Overall confidence:** MEDIUM-HIGH (Meta restrictions evolve quickly; fundamentals are solid)

---

## Executive Summary

David VanDyke's setup — static niche landing pages on Vercel with A/B infrastructure already built —
is well-positioned for a disciplined paid traffic + conversion optimization loop. The infrastructure
risk is low; the execution risk is in Meta's Special Ad Category restrictions (insurance is classified
as a financial product) and in the reality that low-traffic A/B testing requires patience and
methodological honesty.

The two-pronged approach is correct. Neither prong works without the other: traffic without
optimized pages burns budget, and optimized pages without traffic produce nothing to test. The
recommended sequence is: instrument tracking first, then launch traffic, then iterate on pages.

The biggest non-obvious finding is that Meta's Special Ad Category eliminates age targeting,
ZIP-level geo targeting, and most interest-based targeting for insurance. This means the
niche-differentiation strategy (landscaper, contractor, restaurant, home-business) must come
primarily from creative message match and custom/lookalike audiences — not from Facebook's
interest targeting. This is actually workable, but it changes how campaigns are structured.

The Calendly tracking integration is the most critical technical dependency. Without it, you
cannot close the loop between ad spend and actual bookings. The good news: Calendly's
`calendly.event_scheduled` postMessage event fires on booking confirmation and can be caught
with a simple JavaScript listener to fire the Meta Pixel `Schedule` event without GTM.

---

## Key Findings

**Traffic:** Use Meta Leads objective (not Traffic) with website destination. Structure one campaign
per niche, each pointing to its dedicated landing page. Creative is the primary targeting lever
because Special Ad Category restricts demographics.

**Conversion:** The highest-leverage A/B test for low traffic is the headline + subheadline block.
Test one thing at a time with a 4-6 week minimum window. Accept Bayesian probability (80%
confidence) rather than waiting for classical 95% significance — you will never get there at
local traffic volumes.

**Tracking:** Install Meta Pixel on all landing pages. Use Calendly's postMessage event to fire
`fbq('track', 'Schedule')` when booking completes. Pass UTM parameters to Calendly via the
prefill/embed API so attribution flows through. This is the single most important implementation task.

**Analytics:** Vercel Web Analytics is already available (free with the Vercel plan) and is the
fastest win. Add Microsoft Clarity (free, unlimited) for heatmaps and session recordings. These
two together cost nothing and cover the full picture.

**Critical pitfall:** Meta will auto-apply Special Ad Category restrictions to insurance ads.
Running without selecting the category first can result in ad account suspension. Always select
"Credit, Employment and Housing" — wait, for insurance it is "Financial Products and Services"
— before launching.

---

## Implications for Roadmap

Suggested implementation sequence:

1. **Tracking foundation** — Install Meta Pixel, Vercel Analytics, Microsoft Clarity, wire up
   Calendly postMessage conversion event. Nothing else matters until this is done.
   - Avoids: launching paid traffic blind with no attribution

2. **Campaign launch — general niche first** — One campaign, Leads objective, $20-30/day,
   broad Michigan geo (minimum 15-mile radius per Special Ad Category), creative testing.
   - Start here because it has the most data, lowest creative production cost.

3. **Niche campaign expansion** — Launch contractor, landscaper, restaurant, home-business
   campaigns once general niche is dialed in. Each gets its own ad set pointing to its niche page.
   - Depends on: tracking working, creative assets per niche being produced

4. **Conversion testing on general page** — Start A/B testing headline variants on the general
   page while niche pages are launching. This is the highest-traffic page.
   - Avoids: testing on niche pages first (too low traffic, tests will never conclude)

5. **Retargeting layer** — After 30-60 days of pixel data, add a retargeting campaign for
   website visitors who did not book. Separate campaign, warm creative, lower CPL.

6. **Secondary channel evaluation** — Evaluate Google LSA eligibility for insurance in Michigan.
   If eligible, add as a complementary channel (intent-based vs. interrupt-based).

**Phase ordering rationale:**
- Tracking must precede all traffic spend
- General niche page generates the most test data; optimize it first
- Niche campaigns depend on creative assets (photography, copy per niche)
- Retargeting requires pixel to accumulate audience (minimum ~100 website visitors)
- LSA is a separate evaluation, not a blocker

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Meta campaign structure | MEDIUM | Special Ad Category rules confirmed; objective rec is HIGH confidence |
| Special Ad Category restrictions | HIGH | Multiple official and practitioner sources agree |
| Calendly tracking mechanics | HIGH | postMessage API is documented by Calendly |
| A/B testing methodology | HIGH | Statistical reality is well-established |
| Analytics tooling | HIGH | Vercel Analytics + Clarity are confirmed free |
| Google LSA eligibility | LOW | Insurance eligibility varies; requires verification |
| Budget benchmarks | MEDIUM | CPL estimates from industry sources, not David's actual data |

---

## Gaps to Address

- Verify Google LSA eligibility for insurance agents in Michigan specifically
- Confirm David's current Calendly plan (postMessage event tracking is available on all plans
  but the native Meta Pixel integration in Calendly's dashboard requires a paid plan)
- Determine whether David has an existing email list that can seed a Custom Audience
- Validate that the existing niche pages have the data-niche attribute wired up for the
  A/B testing infrastructure (code shows `data-niche="general"` — confirm all niches)
