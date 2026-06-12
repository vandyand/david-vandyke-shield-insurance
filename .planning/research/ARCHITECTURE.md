# Architecture: Traffic + Conversion System

**Domain:** Facebook Ads → Niche Landing Pages → Calendly Booking
**Researched:** 2026-03-25

---

## System Overview

```
[Meta Ads Manager]
       |
       | UTM-tagged URL
       v
[Vercel Edge Middleware]
  - Reads active variants from Edge Config
  - Assigns a or b variant cookie
  - Rewrites URL to /[niche]/a.html or /[niche]/b.html
       |
       v
[Niche Landing Page]
  - Meta Pixel (PageView)
  - GA4 (page_view)
  - Microsoft Clarity (session recording)
  - UTM capture → sessionStorage
  - Calendly embed (inline widget)
       |
       | User books
       v
[Calendly postMessage: calendly.event_scheduled]
       |
       v
[JS Event Listener on Landing Page]
  ├── fbq('track', 'Schedule') → Meta Pixel
  └── gtag('event', 'calendly_booking') → GA4
             |
             v
[Meta Ads Manager: Schedule conversions]
[GA4: Conversion report w/ UTM + niche + variant]
```

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| Meta Ads Manager | Campaign creation, budget, creative delivery | Landing pages (via click) |
| Vercel Middleware | A/B variant assignment, URL rewriting | Edge Config (reads active variants), Landing pages |
| Edge Config | Stores active variants per niche | Admin dashboard (writes), Middleware (reads) |
| Landing Pages (static HTML) | Content delivery, tracking initialization | Meta Pixel, GA4, Clarity, Calendly embed |
| Calendly embed (iframe) | Booking flow | Parent page (via postMessage) |
| Meta Pixel | Conversion tracking, audience building | Meta Ads Manager (server sync) |
| GA4 | Full attribution analytics | No outbound; humans read it |
| Microsoft Clarity | Behavior analytics | No outbound; humans review sessions |
| Admin Dashboard (`/_admin`) | Variant control | Edge Config (writes) |

---

## Data Flow: The Attribution Chain

**Happy path:** A landscaper business owner in Grand Rapids sees David's Facebook ad,
clicks, lands on `/landscaper/`, the middleware assigns them variant `a`, they read the page,
click the Calendly embed, book a 15-minute call. Here is where each data piece goes:

1. **Facebook click** — Meta stamps an `fbclid` parameter on the URL. This is how Meta
   internally tracks the click even if the user is on iOS (partially — CAPI is needed for full
   iOS attribution).

2. **UTM parameters** — Arrive in the URL: `?utm_source=facebook&utm_medium=paid-social&
   utm_campaign=landscaper-leads&utm_content=cold-broad&utm_term=video-hook-a&fbclid=...`

3. **UTM capture** — JavaScript on the landing page reads the URLSearchParams and stores
   all UTM values plus the raw `fbclid` in `sessionStorage` on page load.

4. **Pixel PageView fires** — Meta records that this `fbclid` resulted in a landing page view.

5. **Variant assignment** — Middleware already assigned variant `a` via cookie before serving
   the page. The `<body>` tag has `data-variant="a" data-niche="landscaper"`.

6. **Booking** — User books through Calendly. Calendly fires `calendly.event_scheduled`
   via postMessage.

7. **Conversion events fire:**
   - `fbq('track', 'Schedule')` → Meta Pixel fires the Schedule standard event. Meta matches
     this to the original click using the browser's cookie store. Meta Ads Manager records
     a conversion for the campaign/ad set/ad that drove the click.
   - `gtag('event', 'calendly_booking', {niche: 'landscaper', variant: 'a', utm_source: 'facebook',
     utm_campaign: 'landscaper-leads'})` → GA4 records the full conversion with attribution.

8. **Reporting:** GA4 shows: "landscaper-leads campaign, cold-broad ad set, variant a → 3 bookings
   this week at $47 CPL." Meta Ads Manager shows: "landscaper-leads campaign → 3 Schedule events."

---

## A/B Testing Architecture (Existing System)

The middleware already handles this correctly. The pattern is:

```
Request to /landscaper/
  → Middleware reads Edge Config: {"landscaper": ["a", "b"]}
  → Randomly assigns variant (or reads existing cookie)
  → Rewrites to /landscaper/a.html or /landscaper/b.html
  → Sets variant cookie for session continuity
```

**What needs to be added to close the loop:**

The variant assignment needs to surface in GA4 conversion events. Currently, the `data-variant`
attribute exists on `<body>` but nothing reads it and sends it to analytics.

The fix: In the conversion event listener, read `document.body.dataset.variant` and include it
as a GA4 event parameter. This allows GA4 custom reports to show "variant a: 8% booking rate,
variant b: 6% booking rate."

---

## Calendly Embed Architecture

**Current state:** Unknown (research could not confirm if pages use iframe link or embedded widget).

**Recommended state:** Inline embed widget using Calendly's JavaScript embed library.

Why inline embed wins over a "Book Now" link:
- Eliminates one navigation step (user stays on page)
- User does not leave the niche-branded context
- postMessage events work on inline embed (they do not work if you open Calendly in a new tab
  and the user books there — no way to catch that event from the parent page)

```html
<!-- Calendly inline widget -->
<div class="calendly-inline-widget"
     data-url="https://calendly.com/davidvd/15min"
     style="min-width:320px;height:700px;">
</div>
<script type="text/javascript"
        src="https://assets.calendly.com/assets/external/widget.js"
        async>
</script>
```

---

## UTM Pass-Through to Calendly (Optional Enhancement)

Calendly supports prefilling UTM parameters into the scheduling URL via URL parameters.
This makes UTM data visible in Calendly's own analytics (separate from GA4/Pixel).

```javascript
// After reading UTMs from sessionStorage, build Calendly URL with them
const utmSource = sessionStorage.getItem('utm_source') || '';
const utmCampaign = sessionStorage.getItem('utm_campaign') || '';
const calendlyWidget = document.querySelector('.calendly-inline-widget');
if (calendlyWidget && utmSource) {
  const currentUrl = calendlyWidget.getAttribute('data-url');
  const url = new URL(currentUrl);
  url.searchParams.set('utm_source', utmSource);
  url.searchParams.set('utm_campaign', utmCampaign);
  calendlyWidget.setAttribute('data-url', url.toString());
}
```

This is a nice-to-have. The GA4 + Meta Pixel approach covers attribution without it.

---

## Retargeting Audience Architecture (Phase 2)

Once Meta Pixel has been running for 30+ days:

**Custom Audiences to create:**
1. "All website visitors — 30 days" (anyone who hit any niche page)
2. "All website visitors — 60 days" (broader, for slower consideration cycles)
3. "Niche page visitors — no booking" (visited `/contractor/` but no Schedule event)
   - This requires Custom Audience based on URL visited + conversion exclusion

**Lookalike Audiences to create (after 100+ Schedule events):**
1. "Bookers lookalike 1%" (people who look like people who booked)
2. "Website visitors lookalike 1%" (broader prospecting)

**Campaign for retargeting:**
- Separate campaign from prospecting (do not mix; budget and creative strategy differ)
- Daily budget: $10/day
- Creative: "You were looking at [niche] insurance — still have questions? Book a free call."
- Frequency cap: 3-5 per week (retargeting fatigue is real; don't become annoying)

---

## Secondary Channel: Google LSA

**Architecture if Google LSA is eligible for insurance in Michigan:**

Google LSA (Local Services Ads) is a separate platform entirely from Google Ads. It is:
- Pay per lead (not per click)
- Requires background check and license verification (advantageous for David — differentiates
  from unlicensed or out-of-state competitors)
- Appears at the very top of Google search results above standard ads
- Best for high-intent searches ("insurance agent near me", "contractor insurance Michigan")

**LSA vs. Facebook strategy:**
- Facebook: interruption marketing (user is not searching for insurance, David reaches them)
- Google LSA: intent marketing (user is searching for insurance, David appears first)
- These are complementary, not competing. Facebook builds brand; LSA captures searchers.

**Verification needed:** Not all insurance products/states qualify for LSA. Verify at
https://ads.google.com/local-services-ads before counting on this channel.

---

## Sources

- Calendly embed API: https://help.calendly.com/hc/en-us/articles/31618265722775-Advanced-Calendly-embed-for-developers
- Calendly UTM embed: https://help.calendly.com/hc/en-us/articles/4406950779799-How-to-source-track-your-Calendly-embed-with-UTM-parameters
- Meta retargeting strategy: https://goadfuel.com/facebook-ads-for-insurance-agents/
- Google LSA overview: https://www.oneupweb.com/blog/guide-to-google-local-service-ads/
