# Technology Stack: Analytics, Tracking & CRO Tooling

**Project:** David VanDyke Insurance — Traffic & Conversion
**Researched:** 2026-03-25

---

## Recommended Tooling Stack

### Analytics (Page Views, Traffic Sources)

| Tool | Cost | Purpose | Why |
|------|------|---------|-----|
| Vercel Web Analytics | Free (included) | Page views, referrers, top pages | Already on the platform, zero setup friction, privacy-compliant |
| Google Analytics 4 | Free | Deep funnel analysis, UTM attribution, goal tracking | Industry standard, best UTM reporting, needed for Calendly GA4 integration |

**Recommendation:** Use both. Vercel Analytics for the quick operational view. GA4 for UTM
attribution and conversion funnel reporting. GA4 is the source of truth for campaign performance.

Setup: Add the GA4 `gtag.js` snippet to the `<head>` of every landing page (all niche variants).

---

### Session Behavior (Heatmaps, Recordings)

| Tool | Cost | Purpose | Why |
|------|------|---------|-----|
| Microsoft Clarity | Free, unlimited | Click heatmaps, scroll maps, session recordings, rage clicks | No session/recording caps, completely free, lightweight script |

**Recommendation:** Clarity only. Hotjar's free tier is 35 sessions/day — useless for this use
case. Clarity has no meaningful limits and is owned by Microsoft, which means it won't
suddenly go paid or shut down. One script tag, done.

Setup: One-line script in `<head>`. Clarity auto-generates heatmaps per page URL.

---

### Conversion Tracking (Booking Attribution)

| Tool | Cost | Purpose | Why |
|------|------|---------|-----|
| Meta Pixel | Free | Track who visits pages, fire Schedule event on booking | Required for ad optimization and retargeting audience building |
| Calendly postMessage listener | Free (custom JS) | Bridge between Calendly iframe and Meta Pixel | Calendly fires `calendly.event_scheduled` via postMessage; catch it, fire the pixel |

**Recommendation:** Do not use Calendly's built-in Meta Pixel integration (requires paid Calendly
plan and has known attribution gaps per community reports). Instead, implement the postMessage
listener directly in JavaScript on each landing page. This is ~15 lines of code and is fully
reliable because Calendly documents this API.

---

### UTM Tracking Through to Calendly

| Approach | Reliability | Complexity |
|----------|------------|------------|
| Calendly prefill URL parameters (append UTMs to Calendly link) | MEDIUM — UTMs land in Calendly's reporting but not back to Meta | Low |
| Cookie-based UTM capture + pass to Calendly embed prefill | HIGH — preserves attribution even across page reloads | Medium |
| Server-side CAPI (Conversions API) | HIGHEST — bypasses iOS restrictions, sends to Meta server-to-server | High (requires backend) |

**Recommendation for this project:** Cookie-based UTM capture. Read UTMs from the landing page
URL on page load, store in sessionStorage, read them back when the Calendly booking event fires,
and include them in the GA4 event and Meta Pixel event. This requires ~30 lines of JavaScript and
no backend. CAPI is overkill for a small local business budget.

---

### A/B Testing Infrastructure (Already Built)

The existing infrastructure uses Vercel Edge Config + middleware to assign variants (a/b) per niche.
The admin dashboard at `/_admin` controls which variants are active.

**What's needed to close the loop:** The variant must be included in the GA4 and Meta Pixel
conversion events so winning variants can be identified. Read `data-variant` from the `<body>` tag
(already present: `data-variant="b"`) and include it as a custom dimension in events.

---

## Installation Snippets (Reference)

### Meta Pixel (base code — goes in `<head>`)
```html
<script>
  !function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?
  n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;
  n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
  t.src=v;s=b.getElementsByTagName(e)[0];s.src=v;s=b.getElementsByTagName(e)[0];
  s.parentNode.insertBefore(t,s)}(window,document,'script',
  'https://connect.facebook.net/en_US/fbevents.js');
  fbq('init', 'YOUR_PIXEL_ID');
  fbq('track', 'PageView');
</script>
```

### Calendly postMessage Conversion Listener
```javascript
window.addEventListener('message', function(e) {
  if (e.data && e.data.event && e.data.event === 'calendly.event_scheduled') {
    // Fire Meta Pixel Schedule event
    if (typeof fbq !== 'undefined') {
      fbq('track', 'Schedule');
    }
    // Fire GA4 event
    if (typeof gtag !== 'undefined') {
      const variant = document.body.getAttribute('data-variant') || 'unknown';
      const niche = document.body.getAttribute('data-niche') || 'unknown';
      gtag('event', 'calendly_booking', {
        'niche': niche,
        'variant': variant,
        'utm_source': sessionStorage.getItem('utm_source') || '',
        'utm_campaign': sessionStorage.getItem('utm_campaign') || '',
      });
    }
  }
});
```

### UTM Capture on Page Load
```javascript
(function() {
  const params = new URLSearchParams(window.location.search);
  ['utm_source','utm_medium','utm_campaign','utm_content','utm_term'].forEach(function(key) {
    const val = params.get(key);
    if (val) sessionStorage.setItem(key, val);
  });
})();
```

### Microsoft Clarity
```html
<script type="text/javascript">
  (function(c,l,a,r,i,t,y){
    c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
    t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
    y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
  })(window, document, "clarity", "script", "YOUR_CLARITY_ID");
</script>
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Heatmaps | Microsoft Clarity | Hotjar | 35 sessions/day free tier is inadequate; Clarity is genuinely unlimited free |
| Analytics | GA4 + Vercel Analytics | Plausible ($9/mo) | GA4 is free and has better UTM/conversion reporting; Plausible is cleaner but costs money for no benefit here |
| Booking attribution | Custom postMessage JS | Spectacle HQ (paid SaaS) | Spectacle is excellent but is a paid tool; postMessage approach is free and sufficient |
| Server-side tracking | Cookie + sessionStorage | Meta CAPI | CAPI requires a backend function; static Vercel site has Vercel Functions available but adds complexity not justified at this budget |

---

## Sources

- Calendly postMessage API: https://help.calendly.com/hc/en-us/articles/31618265722775-Advanced-Calendly-embed-for-developers
- Microsoft Clarity: https://clarity.microsoft.com (free, confirmed unlimited)
- Vercel Web Analytics: https://vercel.com/docs/analytics (free tier confirmed)
- Calendly attribution approach: https://www.spectaclehq.com/blog/calendly-attribution-conversion-tracking
- UTM strategy: https://admanage.ai/blog/utm-parameters-for-facebook-ads
