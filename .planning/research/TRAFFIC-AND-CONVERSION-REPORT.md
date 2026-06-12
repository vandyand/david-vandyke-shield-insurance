# Traffic & Conversion Strategy Report
# David VanDyke Insurance — Facebook Ads + Niche Landing Pages

**Client:** David VanDyke, Shield Insurance Agency, West Michigan
**Site:** davidvandykeinsurance.com (static, Vercel)
**Goal conversion:** Calendly booking (15-minute call)
**Primary traffic source:** Meta/Facebook Ads
**Researched:** 2026-03-25

---

## The Short Version

Before spending a dollar on ads, instrument tracking. Then launch one campaign (general niche,
$25/day). Wait 2 weeks before touching it. Add niche campaigns once the general campaign is
proving viable. Start A/B testing the general page headline at week 4. Add retargeting at month 2.

The two biggest mistakes this setup would make: (1) running ads without Meta Pixel + Calendly
conversion tracking in place, and (2) selecting the wrong Meta campaign objective (use Leads,
not Traffic). Everything else is details.

---

## CRITICAL: The Special Ad Category Trap

Insurance is classified as a **Financial Products and Services** Special Ad Category on Meta.

This eliminates:
- Age targeting (cannot target 35-65, Medicare-age, etc.)
- ZIP code level geo targeting (minimum 15-mile radius only)
- Most interest-based targeting ("retirement planning," "small business owner," etc.)
- Meta's Advantage+ audience expansion tool

**Must-do before creating any campaign:** In Meta Ads Manager, when creating the campaign,
click "Special Ad Categories" and check "Financial Products and Services." If this is not
selected and Meta flags the account, the account can be suspended.

**The implication:** Niche targeting (landscaper, contractor, restaurant) cannot be done via
demographic filters. It must be done through **creative** — the ad image, copy, and hook speak
to the niche, and Meta's algorithm finds who responds to it. This is actually fine; it is how
Facebook's AI-based targeting is meant to work.

---

## PRONG 1: TRAFFIC

### Campaign Objective

Use the **Leads** objective (website destination), not the Traffic objective.

The Traffic objective optimizes for cheap clicks. Meta will find people who click on anything —
they will not book. The Leads objective tells Meta's algorithm to find people who complete
the specific conversion action (a Calendly booking). The algorithm only learns if it has a
conversion signal to optimize against — which is why tracking must be set up first.

Do not use Facebook Lead Ads (instant forms). They keep the user inside Facebook and prevent
the Calendly booking experience. The goal is bookings, not contact data captured in a form.

### Campaign Structure

**One campaign per niche.** Do not consolidate niches into one campaign. Meta optimizes at
the campaign level; mixing landscaper and contractor muddies the signal. Each niche gets:
- Its own campaign
- One ad set (to start — budget is too small to split)
- 2-3 ads (for creative testing within the campaign)

```
Campaign: general-leads ($25/day)
  └── Ad Set: cold-broad-michigan
        ├── Ad: video-hook-a (15-sec David intro video)
        ├── Ad: static-headshot-b (David photo + headline overlay)
        └── Ad: carousel-coverage-c (3-panel coverage types)

Campaign: contractor-leads ($20/day)
  └── Ad Set: cold-broad-michigan
        ├── Ad: video-hook-a ("Are you a contractor in Michigan?")
        └── Ad: static-jobsite-b (construction site image)
```

### Audience Targeting

**Given Special Ad Category restrictions, targeting is limited to:**

1. **Location:** Greater West Michigan area — Grand Rapids + 15-mile radius as a starting
   point. This covers most of David's natural service area and satisfies the minimum radius
   requirement. Can expand to all of Michigan if needed.

2. **Demographics:** All ages, all genders (Special Ad Category removes the ability to restrict).

3. **Interests:** Broad or none. Interest targeting for financial products is heavily restricted.
   Do not waste time building elaborate interest stacks — they will either be unavailable or
   too broad to matter. Let the creative do the filtering.

4. **Advantage+ Audience:** Meta's AI targeting system. This is the correct choice for
   Special Ad Category campaigns. Turn it on and let Meta find who responds.

**Audience priority once pixel has data (Month 2+):**

1. **Website Visitor Retargeting** — Lowest CPL, highest intent. Anyone who visited a
   niche page but did not book. Set up as a separate campaign, $10/day.

2. **Lookalike from Bookers** — After 100+ Schedule events, create a 1% lookalike audience
   from Calendly bookings. This is your best cold prospecting audience.

3. **Customer Email List Lookalike** — If David has an existing client list (even 200-500
   emails), upload as a Custom Audience and create a 1% lookalike. This is available even
   before the pixel accumulates data.

### Creative Best Practices

**The formula:** Hook (1-3 sec) → Pain or Identity → Credibility → Single CTA

**Hooks that work for local insurance:**

For general niche:
- "Are you overpaying for insurance in West Michigan?"
- "I'm David VanDyke — I can shop 20+ insurance carriers so you don't have to."
- "Most people don't know they can get better coverage for less. Here's how."

For contractor niche:
- "Contractor in Michigan? You might be overpaying for your GL policy."
- "I help Michigan contractors get the right coverage without paying for what they don't need."
- "Your current insurance agent probably only has 3 options. I have 20+."

For landscaper niche:
- "Landscaping business in West Michigan? Let's make sure you're covered the right way."
- "Landscapers face specific risks. Most general policies don't cover them."

For restaurant niche:
- "Restaurant owners — liquor liability, slip and fall, food spoilage. Are you actually covered?"
- "Running a restaurant in Michigan? I specialize in business insurance for food service."

For home business niche:
- "Working from home doesn't mean your home policy covers your business."
- "Most home insurance policies explicitly exclude business liability. Here's what to do."

**David's biggest differentiators to feature in every ad:**
- Dave Ramsey ELP since 2006 (the Ramsey audience is large in Michigan, this is recognition
  they trust)
- Independent agent = shops 20+ carriers (this is the core value prop vs. captive agents)
- Licensed in 9 states (signals experience and legitimacy)
- 15-minute free call (low commitment, low friction)

**Format hierarchy:**
1. Short video (15-30 sec): David to camera, plain background, natural delivery. No production
   budget needed. Authenticity outperforms polish for a trust-based local service. Use captions
   (85% of Facebook video is watched with sound off).
2. Static image: David's existing headshot + headline overlay text + niche logo/imagery.
3. Carousel: For niches, 3-4 panels each showing a specific coverage type with brief explanation.

### Landing Page URL Strategy

Every campaign links to its niche page. The middleware handles A/B variant assignment.
Never link to the homepage.

| Campaign | Destination URL |
|----------|----------------|
| general-leads | davidvandykeinsurance.com/general/ |
| landscaper-leads | davidvandykeinsurance.com/landscaper/ |
| contractor-leads | davidvandykeinsurance.com/contractor/ |
| restaurant-leads | davidvandykeinsurance.com/restaurant/ |
| home-business-leads | davidvandykeinsurance.com/home-business/ |

### UTM Parameter Strategy

Add to every ad destination URL using Meta's dynamic macros:

```
?utm_source=facebook&utm_medium=paid-social&utm_campaign={{campaign.name}}&utm_content={{adset.name}}&utm_term={{ad.name}}
```

This auto-populates the actual campaign/adset/ad names into the UTM fields. No manual URL
building needed. Meta substitutes the values at click time.

**Naming conventions (use these exactly — lowercase, hyphens not spaces):**
- Campaigns: `general-leads`, `contractor-leads`, `landscaper-leads`, `restaurant-leads`,
  `home-business-leads`
- Ad Sets: `cold-broad`, `retarget-visitors`, `lookalike-bookers`, `lookalike-customers`
- Ads: `video-david-intro`, `static-headshot`, `carousel-coverage`, `video-testimonial`

### Budget Allocation

**Month 1-2 (learning phase):**
- Start with one campaign: general-leads at $25/day ($750/month)
- After 30 days, add one niche campaign: $20/day ($600/month)
- Total: ~$1,350/month

**Month 3+ (scaling):**
- Add retargeting campaign: $10/day ($300/month)
- Add second niche campaign: $20/day ($600/month)
- Total: ~$2,000-2,500/month

**When to scale a campaign:** If CPL is under $50 and consistent for 2+ weeks, double the
daily budget. Do not increase budget by more than 20% per week — larger jumps reset the
learning phase.

**Target CPL benchmarks for 15-minute insurance booking:**
- Under $30: Excellent — scale aggressively
- $30-60: Good — optimize creative, continue
- $60-100: Acceptable — requires improvement before scaling
- Over $100: Stop and reassess creative and page

### Secondary Channels (Beyond Facebook)

**Google Local Services Ads (LSA) — evaluate, do not skip**

LSA is intent-based (user is actively searching for insurance) vs. Facebook's interrupt-based
model (David reaches users who are not searching). These are complementary, not competing.

LSA for insurance in Michigan requires verification. Visit https://ads.google.com/local-services-ads
to check eligibility. If eligible: apply, get Google Screened badge, launch. Pay per lead,
not per click. Expected CPL: $20-50 for insurance. This channel has no learning phase and
delivers leads immediately once live.

**Organic (Facebook page + content) — low priority but free**

Posting niche-specific tips to David's Facebook business page costs nothing and can build
the retargeting audience over time. Not a replacement for paid ads but reinforces them.
One post per week: "Contractor tip: here's the one coverage most contractors forget."

**Email to existing clients — immediate warm channel**

If David has client email addresses: send one email per niche introducing the niche-specific
page. This can seed a Calendly booking from existing relationships (referrals, cross-sells)
and builds the pixel audience faster.

---

## PRONG 2: CONVERSION

### What Matters Most on the Landing Pages

In order of conversion impact (research-backed):

1. **Headline + subheadline** — Decides in 3 seconds whether the visitor stays. Must answer:
   who is this for, what do they get, why David. Must match the ad that brought them.
   Example: "West Michigan Contractor Insurance" (H1) + "I shop 20+ carriers to find you the
   right coverage. Book a free 15-minute call." (H2)

2. **CTA button — copy, placement, visibility** — Must be above the fold on mobile without
   scrolling. Copy: "Book Your Free 15-Min Call" is better than "Schedule Now" which is better
   than "Get Started" which is better than "Contact Us." The more specific and lower-friction,
   the better.

3. **Calendly embed (inline widget, not a link)** — If the Calendly calendar is embedded
   directly on the page, users book without navigating away. This reduces abandonment by
   eliminating the click → new tab → find availability → book → return sequence. If the
   current pages link to Calendly instead of embedding it, fixing this is a high priority.

4. **Social proof near the CTA** — A testimonial from a business owner in the same niche as
   the page, placed immediately above or below the CTA button, directly improves conversion.
   "David saved my landscaping company $1,200/year. Took 15 minutes." — Mike, Jenison MI.
   The Dave Ramsey ELP badge is also high-value credibility that should be near the CTA.

5. **Mobile optimization** — Facebook traffic is predominantly mobile. Test every page on
   a real iPhone at a real cellular connection. The Calendly embed particularly needs
   verification on mobile — it must be visible and scrollable.

### A/B Testing Methodology

**Reality of small traffic volumes:**

At $25/day with a $1.50-3.00 CPC, expect 8-16 clicks per day. With a 5-8% booking rate,
that is 0-1 bookings per day. To detect a meaningful improvement (say, variant B converting
at 8% vs. variant A at 5%), you need approximately 600-800 visitors per variant. At 8-16
clicks/day, that takes 40-100 days per variant.

**What this means practically:**

- Run tests on the general page only (highest traffic of all five niches)
- Run one test at a time, minimum 4 weeks per test
- Accept 80% statistical confidence as the threshold (not 95%)
- For borderline results (70-80% confidence), extend the test another 2 weeks before calling it
- Never A/B test niche pages that get under 5 clicks/day — the test will not conclude in
  any reasonable timeframe

**The existing A/B infrastructure is correctly built.** The middleware assigns variants and the
`data-variant` attribute is on the body. The only missing piece is surfacing the variant in
conversion analytics (see Tracking section below).

### What to Test and In What Order

| Priority | Element | Variants to Test | Why |
|----------|---------|-----------------|-----|
| 1 | Headline copy | Pain-point hook vs. benefit statement | Highest leverage, decided in first 3 seconds |
| 2 | CTA button copy | "Book Free 15-Min Call" vs. "See David's Availability" | Words matter more than button color |
| 3 | CTA position | Sticky mobile button vs. in-page | Mobile-first impact |
| 4 | Social proof placement | Testimonial above CTA vs. below hero | Trust at the moment of decision |
| 5 | Calendly embed vs. link | Embedded widget vs. "Book Now" link | Eliminates a step in the funnel |
| 6 | Hero image | David headshot vs. niche-relevant image | Identity vs. trust signal test |
| 7 | Dave Ramsey ELP prominence | Large badge in hero vs. small in trust section | Ramsey audience recognition |

Start at #1. Do not start #2 until #1 has a declared winner or is abandoned (8 weeks, no result).

### Measuring Conversions

**The technical chain:**

1. Meta Pixel fires `PageView` when the landing page loads
2. JavaScript captures UTM parameters from the URL and stores them in `sessionStorage`
3. User completes booking in Calendly embed
4. Calendly fires `window.postMessage({ event: 'calendly.event_scheduled' })` to the parent page
5. JavaScript event listener on the landing page catches this and fires:
   - `fbq('track', 'Schedule')` — Meta Pixel records the conversion
   - `gtag('event', 'calendly_booking', { niche, variant, utm_source, utm_campaign })` — GA4

**To include variant data in conversions:**
```javascript
// Read from the <body> tag that already has this attribute
const variant = document.body.getAttribute('data-variant');
const niche = document.body.getAttribute('data-niche');
// Include in the GA4 event
gtag('event', 'calendly_booking', { variant, niche, utm_campaign: sessionStorage.getItem('utm_campaign') });
```

**In GA4:** Mark `calendly_booking` as a conversion event. Build a custom report showing:
- Conversions by campaign (utm_campaign)
- Conversions by niche
- Conversions by variant (custom dimension)

**In Meta Ads Manager:** The `Schedule` standard event appears in the Conversions column.
Use this to evaluate CPL per campaign, ad set, and individual creative.

**Known limitation:** iOS 14.5+ users with App Tracking Transparency opted out will not
transmit the fbclid cookie. For a local business at this budget, this is acceptable without
implementing Meta's Conversions API (CAPI). CAPI is worth adding if the campaign scales
above $3,000/month, but is overkill now.

### Heatmaps and Session Recording

Install **Microsoft Clarity** — free, unlimited sessions, lightweight script.

Clarity tells you:
- Which sections users scroll to (scroll maps)
- Where they click (click heatmaps)
- Full session recordings (watch real users navigate and book or fail to book)
- Rage click detection (users clicking something repeatedly — signals confusion)
- Dead click detection (users clicking non-clickable elements — signals they expect a link)

The most valuable use of Clarity: watch session recordings of users who landed on the page
from a Facebook ad and left without booking. What did they look at? Where did they stop?
Did they try to click the Calendly embed and fail? This is irreplaceable qualitative data.

**Clarity setup:** One script tag in `<head>` of all niche pages. Free, no account limit.

### Recommended Testing Cadence

```
Week 1-2:    Install Meta Pixel + GA4 + Clarity + Calendly postMessage listener
             QA all tracking: verify events fire correctly
             Do not launch ads yet

Week 3:      Launch general-leads campaign ($25/day)
             Monitor: Pixel firing correctly? GA4 receiving UTM data?

Week 4-8:    Hands off the campaign (learning phase)
             Monitor daily: impressions, spend, any policy issues
             Do not touch campaign settings

Week 6:      Launch A/B test #1: general page headline (variant a vs. b)
             Document: what is the hypothesis, what are the variants, start date

Week 8:      First campaign review:
             - What is CPL?
             - Which creative has lowest CPL? Pause the highest CPL ad.
             - Create one new ad to replace it.
             - Watch 5-10 Clarity session recordings.

Week 10:     Launch second niche campaign (contractor or landscaper — whichever is
             David's highest-priority niche) at $20/day

Week 14:     Read A/B test #1 (8 weeks minimum has elapsed)
             Use Bayesian calculator. Declare winner or call inconclusive.
             If winner: update the "a" variant to the winning copy for all niche pages
             Start A/B test #2 (CTA button copy)

Week 20:     Add retargeting campaign ($10/day) using website visitor audience

Month 4+:    Two-week iteration cycles: watch Clarity → form hypothesis → test
```

---

## TOOLING SUMMARY

| Tool | Cost | What It Does | Setup |
|------|------|-------------|-------|
| Meta Pixel | Free | Conversion tracking, retargeting audiences | Script in `<head>` |
| GA4 | Free | Full attribution + UTM reporting | Script in `<head>` |
| Microsoft Clarity | Free | Heatmaps + session recordings | Script in `<head>` |
| Vercel Web Analytics | Free (included) | Page views, referrers, quick stats | Already available |
| Calendly postMessage listener | Free (custom JS ~15 lines) | Bridge Calendly → Pixel + GA4 | Inline JS on each page |

No paid tools are needed until this system is generating 50+ bookings/month. At that point,
consider Meta's Conversions API for better iOS attribution.

---

## IMPLEMENTATION PRIORITY ORDER

1. **Meta Pixel installation on all five niche pages** — No tracking, no optimization.
2. **GA4 installation on all five niche pages** — UTM attribution lives here.
3. **Calendly postMessage listener** — Closes the tracking loop. Test thoroughly.
4. **UTM capture JavaScript** — sessionStorage persistence of UTMs.
5. **Microsoft Clarity installation** — Free behavior data.
6. **Verify Calendly is embedded (not linked)** — postMessage requires inline embed.
7. **General niche campaign launch** — First live campaign.
8. **First A/B test (general page headline)** — Start at week 4-6 after traffic is flowing.
9. **Niche campaigns** — After general campaign validates the model.
10. **Retargeting campaign** — After 30 days of pixel data.

---

## Sources

- Meta Special Ad Category for insurance: https://www.data-axle.com/resources/blog/meta-special-ad-categories-rules/
- Meta campaign objectives: https://www.wordstream.com/blog/facebook-ad-objectives
- Facebook ads for insurance agents: https://goadfuel.com/facebook-ads-for-insurance-agents/
- Meta targeting updates 2025: https://leadenforce.com/blog/facebook-ads-targeting-updates-how-to-adapt-in-2025
- Calendly Meta Pixel integration: https://calendly.com/integration/facebook-pixel
- Calendly UTM tracking: https://help.calendly.com/hc/en-us/articles/1500005575121-How-to-track-conversions-with-UTM-parameters
- Calendly postMessage events: https://www.analyticsmania.com/post/how-to-track-calendly-with-google-tag-manager-and-google-analytics-4/
- Calendly attribution without GTM: https://www.spectaclehq.com/blog/calendly-attribution-conversion-tracking
- A/B testing low traffic: https://vwo.com/blog/ab-split-testing-low-traffic-sites/
- Insurance landing page CRO: https://www.apexure.com/insurance-landing-page/
- Microsoft Clarity vs Hotjar: https://www.heatmap.com/blog/microsoft-clarity-vs-hotjar
- Vercel Web Analytics: https://vercel.com/docs/analytics
- Facebook retargeting for insurance: https://www.invoca.com/blog/drive-insurance-leads-facebook
- Google LSA overview: https://www.oneupweb.com/blog/guide-to-google-local-service-ads/
- Meta ads benchmarks 2026: https://www.enrichlabs.ai/blog/meta-ads-benchmarks-2025
