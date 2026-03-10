# A/B Testing & Niche Landing Pages Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a system where each niche audience gets its own landing page URL, and each URL can serve multiple variants (A/B/C/D) for testing — all with zero framework overhead.

**Architecture:** A simple Node build script reads JSON config files (one per niche) and stamps them into a shared HTML template to produce standalone HTML pages. Vercel Edge Middleware assigns visitors a variant via cookie and rewrites the request to the correct file. Facebook Ads point to niche URLs; the site handles variant rotation within each niche.

**Tech Stack:** Vanilla HTML/CSS/JS (Tailwind CDN, Lucide icons), Node.js build script, Vercel Edge Middleware, Cloudflare Web Analytics (already in place).

---

## Architecture Overview

```
Facebook Ad (targeting landscapers)
  → davidvandykeinsurance.com/landscaper
    → Vercel Middleware reads cookie
      → No cookie? Assign variant randomly, set cookie
      → Cookie says "B"? Rewrite to /landscaper/b.html
```

### File Structure (after build)

```
/
├── middleware.js                    # Vercel Edge Middleware
├── vercel.json                     # Rewrites + config
├── build.js                        # Assembles pages from template + niche configs
├── package.json                    # Scripts only (no deps)
├── templates/
│   ├── base.html                   # Full page template with {{placeholders}}
│   └── sections/                   # Reusable HTML section partials
│       ├── header.html
│       ├── hero.html
│       ├── why-choose.html
│       ├── services.html
│       ├── about.html
│       ├── testimonials.html
│       ├── carriers.html
│       ├── faq.html
│       ├── contact.html
│       └── footer.html
├── niches/
│   ├── general.json                # Config: variants A/B/C with copy overrides
│   ├── landscaper.json
│   ├── contractor.json
│   ├── restaurant.json
│   └── home-business.json
├── public/                         # Build output (gitignored, built by Vercel)
│   ├── images/
│   │   └── david-headshot.png
│   ├── index.html                  # General variant A
│   ├── landscaper/
│   │   ├── a.html
│   │   └── b.html
│   ├── contractor/
│   │   ├── a.html
│   │   └── b.html
│   └── ...
├── images/                         # Source images
│   └── david-headshot.png
└── CNAME
```

### Niche Config Format

Each niche JSON defines its variants. Every variant can override any section's copy. Unspecified fields fall back to defaults in the template.

```json
{
  "slug": "landscaper",
  "name": "Landscaping & Lawn Care Insurance",
  "variants": {
    "a": {
      "hero": {
        "headline": "Insurance Built for Landscapers",
        "subheadline": "General liability, commercial auto, equipment coverage — all from one agent who understands your business.",
        "cta_text": "Book a Free Consultation",
        "cta_url": "https://calendly.com/davidvd-shieldagency/15-minute-meeting"
      },
      "services": {
        "headline": "Coverage for Your Landscaping Business",
        "items": [
          {"icon": "shield", "title": "General Liability", "desc": "Protection when your crew damages a client's property or someone gets injured on a job site."},
          {"icon": "car", "title": "Commercial Auto", "desc": "Coverage for your trucks, trailers, and the equipment they carry."},
          {"icon": "wrench", "title": "Equipment & Tools", "desc": "Protect your mowers, blowers, and other expensive equipment from theft and damage."},
          {"icon": "users", "title": "Workers' Compensation", "desc": "Required coverage that protects your employees and your business."}
        ]
      },
      "faq": {
        "items": [
          {"q": "Do I need insurance for my landscaping business?", "a": "Yes. Most clients and municipalities require proof of general liability before you can work on their property."},
          {"q": "What does general liability cover?", "a": "It covers property damage you cause at a job site, injuries to non-employees, and legal defense costs if you're sued."},
          {"q": "How fast can I get a certificate of insurance?", "a": "Usually within 24 hours of binding your policy. I know you need COIs fast to land jobs."},
          {"q": "Can you cover my seasonal workers?", "a": "Yes. Workers' comp policies can be structured to account for seasonal fluctuations in your crew size."}
        ]
      },
      "why_choose": {
        "headline": "Why Landscapers Choose David",
        "items": [
          {"icon": "handshake", "title": "I Know Your Business", "desc": "I work with landscapers across Michigan and understand the specific risks you face every day."},
          {"icon": "search", "title": "Multiple Carriers", "desc": "I shop your coverage across 50+ carriers to find the best rate without cutting corners."},
          {"icon": "clock", "title": "Fast COIs", "desc": "Need a certificate of insurance for a new client? I get them out fast so you don't lose the job."},
          {"icon": "headphones", "title": "Real Person, Real Help", "desc": "When you have a claim or a question, you call me directly — not a 1-800 number."}
        ]
      },
      "contact": {
        "headline": "Get Your Landscaping Business Covered",
        "subheadline": "15-minute call — I'll walk you through exactly what coverage you need.",
        "cta_text": "Schedule Your Free 15-Min Call"
      }
    },
    "b": {
      "hero": {
        "headline": "Stop Worrying About Lawsuits. Start Growing Your Business.",
        "subheadline": "One call. Multiple quotes. Coverage that keeps your landscaping crew working.",
        "cta_text": "Get Protected Today"
      }
    }
  }
}
```

**Variant inheritance:** Variant "b" only specifies overrides. Everything else (services, faq, why_choose, contact) inherits from variant "a". This keeps configs DRY — you only specify what's different.

### Middleware Logic

```javascript
// middleware.js — Vercel Edge Middleware
import { NextResponse } from 'next/server';

const NICHES = ['landscaper', 'contractor', 'restaurant', 'home-business'];
const VARIANT_COUNTS = { '': 2, landscaper: 2, contractor: 2, restaurant: 2, 'home-business': 2 };
const VARIANTS = 'abcdefghij';

export function middleware(request) {
  const { pathname } = request.nextUrl;

  // Determine which niche (empty string = general/homepage)
  const niche = NICHES.find(n => pathname === `/${n}` || pathname === `/${n}/`);
  const isHome = pathname === '/' || pathname === '/index.html';

  if (!niche && !isHome) return NextResponse.next();

  const slug = niche || '';
  const cookieName = `variant_${slug || 'general'}`;
  const existingVariant = request.cookies.get(cookieName)?.value;
  const count = VARIANT_COUNTS[slug] || 2;

  // Assign variant if none exists
  let variant = existingVariant;
  if (!variant || !VARIANTS.includes(variant)) {
    variant = VARIANTS[Math.floor(Math.random() * count)];
  }

  // Rewrite to the correct HTML file
  const target = slug
    ? `/${slug}/${variant}.html`
    : (variant === 'a' ? '/index.html' : `/general/${variant}.html`);

  const response = NextResponse.rewrite(new URL(target, request.url));
  response.cookies.set(cookieName, variant, { maxAge: 60 * 60 * 24 * 30, path: '/' });
  return response;
}

export const config = {
  matcher: ['/', '/landscaper', '/contractor', '/restaurant', '/home-business'],
};
```

### Tracking

UTM params from Facebook Ads flow through to Calendly automatically (Calendly preserves query params from the referring page). The variant ID is injected as a `data-variant` attribute on the `<body>` tag, which Cloudflare Web Analytics can capture. For deeper analytics later, PostHog can be added with one script tag.

### Removing Datastar

Datastar is currently used for:
1. **Header scroll shadow** — replace with 3 lines of vanilla JS
2. **Mobile hamburger menu** — replace with vanilla JS toggle
3. **Services expand/collapse on mobile** — replace with vanilla JS
4. **CTA A/B toggle** (?ab=true param) — no longer needed (middleware handles variants)
5. **Geo-based headline** (?geo=west-michigan) — bake into variant configs instead

All Datastar `data-signals`, `data-show`, `data-on:click`, `data-class`, `data-text`, `data-init` attributes get replaced with plain JS event listeners and classList toggles.

---

## Task 1: Set Up Build Infrastructure

**Files:**
- Create: `package.json`
- Create: `vercel.json`
- Create: `build.js`
- Modify: `.gitignore` (add `public/`)

**Step 1: Create package.json**

```json
{
  "name": "david-vandyke-insurance",
  "private": true,
  "scripts": {
    "build": "node build.js"
  }
}
```

**Step 2: Create vercel.json**

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "public"
}
```

**Step 3: Create build.js scaffold**

Start with a minimal build script that just copies `index.html` to `public/index.html` to verify the Vercel pipeline works.

```javascript
const fs = require('fs');
const path = require('path');

const PUBLIC = path.join(__dirname, 'public');

// Clean and create output dir
if (fs.existsSync(PUBLIC)) fs.rmSync(PUBLIC, { recursive: true });
fs.mkdirSync(PUBLIC, { recursive: true });

// Copy images
const imgSrc = path.join(__dirname, 'images');
const imgDest = path.join(PUBLIC, 'images');
fs.mkdirSync(imgDest, { recursive: true });
for (const file of fs.readdirSync(imgSrc)) {
  fs.copyFileSync(path.join(imgSrc, file), path.join(imgDest, file));
}

// Copy CNAME
fs.copyFileSync(path.join(__dirname, 'CNAME'), path.join(PUBLIC, 'CNAME'));

// For now, just copy index.html
fs.copyFileSync(path.join(__dirname, 'index.html'), path.join(PUBLIC, 'index.html'));

console.log('Build complete: public/index.html');
```

**Step 4: Add `public/` to .gitignore**

Append `public/` to `.gitignore`.

**Step 5: Test locally**

Run: `node build.js`
Expected: `public/index.html` exists and matches source `index.html`.

**Step 6: Commit**

```bash
git add package.json vercel.json build.js .gitignore
git commit -m "feat: add build infrastructure for landing page system"
```

---

## Task 2: Extract Template Sections from index.html

**Files:**
- Create: `templates/base.html`
- Create: `templates/sections/header.html`
- Create: `templates/sections/hero.html`
- Create: `templates/sections/why-choose.html`
- Create: `templates/sections/services.html`
- Create: `templates/sections/about.html`
- Create: `templates/sections/testimonials.html`
- Create: `templates/sections/carriers.html`
- Create: `templates/sections/faq.html`
- Create: `templates/sections/contact.html`
- Create: `templates/sections/footer.html`

**Step 1: Create templates/base.html**

This is the page skeleton with `{{section}}` placeholders and `{{variable}}` placeholders for per-variant copy. Extract the `<head>` content, and slot in section includes:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{page_title}}</title>
  <!-- ... same head content minus Datastar script ... -->
</head>
<body class="font-sans text-gray-600 leading-relaxed" data-variant="{{variant_id}}" data-niche="{{niche_slug}}">
  {{section:header}}
  <main>
    {{section:hero}}
    {{section:why-choose}}
    {{section:services}}
    {{section:about}}
    {{section:testimonials}}
    {{section:carriers}}
    {{section:faq}}
    {{section:contact}}
  </main>
  {{section:footer}}
  <script>lucide.createIcons();</script>
  {{vanilla_js}}
  <!-- Cloudflare Web Analytics -->
  <script defer src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{"token": "1eb649f75ee44207bde8d74bd95b2396"}'></script>
</body>
</html>
```

**Step 2: Extract each section from current index.html into its own file**

Each section file contains the HTML for that section with `{{placeholder}}` variables where copy differs between variants. For example, `templates/sections/hero.html`:

```html
<section id="home" class="border-b border-gray-200 bg-gradient-to-b from-blue-50 to-white">
  <div class="py-12 md:py-20 px-4 md:px-6 max-w-4xl mx-auto">
    <div class="flex flex-col md:flex-row items-center gap-8 md:gap-12 mb-8 md:mb-12">
      <div class="flex-shrink-0">
        <img src="{{image_base}}/david-headshot.png"
          alt="David VanDyke, your local Michigan insurance agent"
          class="w-36 h-36 md:w-56 md:h-56 lg:w-64 lg:h-64 object-cover rounded-full border-4 border-gold shadow-xl ring-4 ring-gold/20">
      </div>
      <div class="text-center md:text-left flex-1">
        <h1 class="text-3xl md:text-5xl font-bold text-navy mb-4 leading-tight tracking-tight">
          {{hero_headline}}
        </h1>
        <p class="text-lg md:text-xl text-gray-600 font-medium max-w-lg">
          {{hero_subheadline}}
        </p>
      </div>
    </div>
    <div class="flex flex-col items-center gap-4 text-center">
      <div class="flex flex-col md:flex-row items-center gap-4">
        <a href="{{hero_cta_url}}" target="_blank" rel="noopener noreferrer"
          class="inline-flex items-center justify-center bg-gold hover:bg-gold-dark text-navy font-bold text-lg md:text-xl px-8 py-4 rounded-lg min-h-[60px] min-w-[220px] shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all">
          {{hero_cta_text}}
        </a>
        <a href="tel:6166164884"
          class="inline-flex items-center justify-center gap-3 bg-navy hover:bg-navy-light text-white font-bold text-lg md:text-xl px-8 py-4 rounded-lg min-h-[60px] min-w-[220px] shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all">
          <i data-lucide="phone" class="w-6 h-6" aria-hidden="true"></i>
          <span>616-616-4884</span>
        </a>
      </div>
      <p class="text-gray-600">
        or email <a href="mailto:davidvd@shieldagency.com" class="text-navy font-medium hover:text-gold-dark transition-colors">davidvd@shieldagency.com</a>
      </p>
    </div>
  </div>
</section>
```

**Step 3: Remove Datastar** — do NOT include the Datastar `<script>` tag in base.html. Replace all `data-signals`, `data-show`, `data-on:click`, `data-class`, `data-text`, `data-init` attributes with equivalent vanilla JS (added as a `<script>` block in base.html).

Vanilla JS replacements needed:
- **Scroll shadow on header:** `window.addEventListener('scroll', ...)` + `classList.toggle`
- **Hamburger menu toggle:** button `onclick` toggles a `hidden` class on mobile nav
- **Services expand/collapse:** button `onclick` toggles `expanded` class on `.secondary-service` elements

**Step 4: Verify template extraction is complete**

Manually confirm every section from the original `index.html` (lines 81-782) is captured in a section file, and that `base.html` assembles them all.

**Step 5: Commit**

```bash
git add templates/
git commit -m "feat: extract HTML template with section partials"
```

---

## Task 3: Build Script — Template Assembly

**Files:**
- Modify: `build.js`

**Step 1: Add template loading and placeholder replacement**

Update `build.js` to:
1. Read `templates/base.html`
2. For each `{{section:name}}`, read and inline `templates/sections/name.html`
3. Read each `niches/*.json` config
4. For each variant in the config, replace `{{placeholder}}` variables with the variant's values (falling back to variant "a" values, then to hardcoded defaults)
5. Write the assembled HTML to `public/`

```javascript
const fs = require('fs');
const path = require('path');

const PUBLIC = path.join(__dirname, 'public');
const TEMPLATES = path.join(__dirname, 'templates');
const NICHES = path.join(__dirname, 'niches');

// Defaults for all placeholders
const DEFAULTS = {
  page_title: 'David VanDyke Insurance',
  image_base: '/images',
  variant_id: 'a',
  niche_slug: 'general',
  hero_headline: 'Insurance Made Personal',
  hero_subheadline: 'Honest advice. Better coverage. Your Michigan agent who puts you first.',
  hero_cta_text: 'Book a Free Consultation',
  hero_cta_url: 'https://calendly.com/davidvd-shieldagency/15-minute-meeting',
  contact_headline: 'Book a free consultation',
  contact_subheadline: "Pick a time that works for you and I'll walk you through your options.",
  contact_cta_text: 'Schedule Your Free 15-Min Call',
  why_choose_headline: 'Why Choose David?',
  // ... etc
};

function loadTemplate() {
  let base = fs.readFileSync(path.join(TEMPLATES, 'base.html'), 'utf8');
  // Inline section partials
  base = base.replace(/\{\{section:([\w-]+)\}\}/g, (_, name) => {
    const sectionPath = path.join(TEMPLATES, 'sections', `${name}.html`);
    return fs.readFileSync(sectionPath, 'utf8');
  });
  return base;
}

function fillTemplate(template, vars) {
  return template.replace(/\{\{(\w+)\}\}/g, (match, key) => {
    return vars[key] !== undefined ? vars[key] : match;
  });
}

function flattenVariantConfig(nicheConfig, variantId) {
  const variantA = nicheConfig.variants?.a || {};
  const variant = nicheConfig.variants?.[variantId] || {};
  // Merge: defaults < variant a < specific variant
  const flat = { ...DEFAULTS };
  // Flatten nested objects from variant a
  for (const [section, values] of Object.entries(variantA)) {
    if (typeof values === 'object' && !Array.isArray(values)) {
      for (const [k, v] of Object.entries(values)) {
        if (typeof v === 'string') flat[`${section}_${k}`] = v;
      }
    }
  }
  // Override with specific variant
  for (const [section, values] of Object.entries(variant)) {
    if (typeof values === 'object' && !Array.isArray(values)) {
      for (const [k, v] of Object.entries(values)) {
        if (typeof v === 'string') flat[`${section}_${k}`] = v;
      }
    }
  }
  flat.variant_id = variantId;
  flat.niche_slug = nicheConfig.slug || 'general';
  flat.page_title = nicheConfig.name || DEFAULTS.page_title;
  return flat;
}

// Clean output
if (fs.existsSync(PUBLIC)) fs.rmSync(PUBLIC, { recursive: true });
fs.mkdirSync(PUBLIC, { recursive: true });

// Copy static assets
const imgSrc = path.join(__dirname, 'images');
const imgDest = path.join(PUBLIC, 'images');
fs.mkdirSync(imgDest, { recursive: true });
for (const f of fs.readdirSync(imgSrc)) {
  fs.copyFileSync(path.join(imgSrc, f), path.join(imgDest, f));
}
fs.copyFileSync(path.join(__dirname, 'CNAME'), path.join(PUBLIC, 'CNAME'));

// Load template
const template = loadTemplate();

// Build each niche
for (const file of fs.readdirSync(NICHES)) {
  if (!file.endsWith('.json')) continue;
  const config = JSON.parse(fs.readFileSync(path.join(NICHES, file), 'utf8'));
  const slug = config.slug || path.basename(file, '.json');
  const variants = Object.keys(config.variants || { a: {} });

  for (const v of variants) {
    const vars = flattenVariantConfig(config, v);
    const html = fillTemplate(template, vars);
    if (slug === 'general' && v === 'a') {
      fs.writeFileSync(path.join(PUBLIC, 'index.html'), html);
    } else {
      const dir = path.join(PUBLIC, slug === 'general' ? 'general' : slug);
      fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(path.join(dir, `${v}.html`), html);
    }
  }
}

console.log('Build complete.');
```

**Step 2: Handle dynamic sections (services, FAQ, why-choose)**

For sections that render arrays of items (services grid, FAQ accordion, why-choose cards), the build script needs to generate the HTML from the config arrays. Add helper functions:

```javascript
function renderServices(items) {
  return items.map(item => `
    <div class="bg-white p-6 rounded-xl border border-gray-200 shadow text-center hover:shadow-lg hover:-translate-y-1 hover:border-gold transition-all">
      <i data-lucide="${item.icon}" class="w-10 h-10 text-navy mx-auto mb-3" aria-hidden="true"></i>
      <h3 class="text-navy font-semibold text-lg mb-2">${item.title}</h3>
      <p class="text-gray-600 text-sm">${item.desc}</p>
    </div>
  `).join('\n');
}

function renderFaq(items) {
  return items.map(item => `
    <details class="bg-white border border-gray-200 rounded-xl overflow-hidden hover:border-gold transition-all group">
      <summary class="flex justify-between items-center p-4 md:p-6 cursor-pointer font-semibold text-navy text-lg hover:bg-gray-50 transition-colors">
        <span>${item.q}</span>
        <span class="ml-4 w-3 h-3 border-r-2 border-b-2 border-navy transform rotate-45 group-open:-rotate-135 transition-transform"></span>
      </summary>
      <div class="px-4 md:px-6 pb-4 md:pb-6 bg-white">
        <p class="text-gray-600">${item.a}</p>
      </div>
    </details>
  `).join('\n');
}

function renderWhyChoose(items) {
  return items.map(item => `
    <div class="bg-white p-6 rounded-xl border border-gray-200 shadow hover:shadow-lg hover:-translate-y-1 hover:border-gold transition-all">
      <i data-lucide="${item.icon}" class="w-10 h-10 text-gold mb-4" aria-hidden="true"></i>
      <h3 class="text-navy font-semibold text-lg mb-2">${item.title}</h3>
      <p class="text-gray-600">${item.desc}</p>
    </div>
  `).join('\n');
}
```

These renderers are called during `flattenVariantConfig` — if a variant has `services.items`, render the HTML and store it as `services_items_html`. The section template uses `{{services_items_html}}`.

**Step 3: Test build locally**

Run: `node build.js`
Expected: `public/index.html` and `public/landscaper/a.html`, `public/landscaper/b.html` etc. exist. Open in browser to verify they look correct.

**Step 4: Commit**

```bash
git add build.js
git commit -m "feat: build script assembles pages from template + niche configs"
```

---

## Task 4: Create Niche Configs

**Files:**
- Create: `niches/general.json`
- Create: `niches/landscaper.json`
- Create: `niches/contractor.json`
- Create: `niches/restaurant.json`
- Create: `niches/home-business.json`

**Step 1: Create general.json**

Extract the current site's copy into the general config with 2 variants:
- A: Current copy ("Insurance Made Personal" / "Book a Free Consultation")
- B: Alternative ("Protect What Matters Most" / "Schedule a Call")

**Step 2: Create landscaper.json**

See the example config above in Architecture Overview. Two variants:
- A: Business-focused ("Insurance Built for Landscapers")
- B: Fear/urgency ("Stop Worrying About Lawsuits. Start Growing Your Business.")

**Step 3: Create contractor.json**

Two variants targeting electricians, HVAC, plumbers, painters:
- A: Professional ("Insurance for Skilled Tradespeople")
- B: Pain-point ("One Accident Could Shut Down Your Business")

**Step 4: Create restaurant.json**

Two variants:
- A: Comprehensive ("Complete Coverage for Your Restaurant")
- B: Specific risk ("Liquor Liability. Slip-and-Falls. Kitchen Fires. Are You Covered?")

**Step 5: Create home-business.json**

Two variants:
- A: Awareness gap ("Your Homeowners Policy Doesn't Cover Your Side Hustle")
- B: Empowering ("Protect Your Business Without the Big-Business Price Tag")

**Step 6: Test build**

Run: `node build.js`
Expected: All niche directories created with variant HTML files.

**Step 7: Commit**

```bash
git add niches/
git commit -m "feat: add niche configs for 5 audience segments"
```

---

## Task 5: Vercel Edge Middleware

**Files:**
- Create: `middleware.js`
- Modify: `vercel.json`

**Step 1: Create middleware.js**

Use the middleware logic from Architecture Overview above. Key behaviors:
- Read `variant_<niche>` cookie
- If missing, assign random variant and set cookie (30-day expiry)
- Rewrite request to the correct HTML file
- Preserve UTM query params through the rewrite

**Step 2: Update vercel.json**

Add middleware matcher config if needed (Vercel auto-detects `middleware.js` at root).

Ensure `vercel.json` looks like:
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "public"
}
```

**Step 3: Test locally with `npx vercel dev`**

Run: `npx vercel dev`
- Visit `http://localhost:3000/` — should serve a variant and set a cookie
- Visit `http://localhost:3000/landscaper` — should serve landscaper variant
- Check cookies in browser DevTools to confirm variant assignment
- Refresh — should get the same variant (sticky cookie)

**Step 4: Commit**

```bash
git add middleware.js vercel.json
git commit -m "feat: add Vercel Edge Middleware for A/B variant routing"
```

---

## Task 6: Remove Datastar, Add Vanilla JS

**Files:**
- Modify: `templates/base.html` (remove Datastar script tag)
- Modify: `templates/sections/header.html` (replace Datastar attributes)
- Modify: `templates/sections/services.html` (replace Datastar attributes)

**Step 1: Remove Datastar script from base.html head**

Delete the line:
```html
<script src="https://cdn.jsdelivr.net/gh/starfederation/datastar@1.0.0-RC.7/bundles/datastar.js" type="module"></script>
```

**Step 2: Replace header Datastar with vanilla JS**

Remove all `data-signals`, `data-init`, `data-class-*`, `data-show`, `data-on:click` attributes from header. Add vanilla JS at the bottom of `base.html`:

```html
<script>
// Scroll shadow on header
const header = document.querySelector('header');
window.addEventListener('scroll', () => {
  header.classList.toggle('shadow-lg', window.scrollY > 10);
});

// Mobile menu toggle
const menuBtn = document.getElementById('menu-toggle');
const mobileNav = document.getElementById('mobile-nav');
const menuIconOpen = document.getElementById('menu-icon-open');
const menuIconClose = document.getElementById('menu-icon-close');
menuBtn.addEventListener('click', () => {
  const open = mobileNav.classList.toggle('hidden');
  menuIconOpen.classList.toggle('hidden');
  menuIconClose.classList.toggle('hidden');
});
// Close mobile menu on nav link click
mobileNav.querySelectorAll('a').forEach(a => {
  a.addEventListener('click', () => {
    mobileNav.classList.add('hidden');
    menuIconOpen.classList.remove('hidden');
    menuIconClose.classList.add('hidden');
  });
});

// Services expand/collapse (mobile)
const servicesBtn = document.getElementById('services-toggle');
if (servicesBtn) {
  const secondaryServices = document.querySelectorAll('.secondary-service');
  const toggleText = servicesBtn.querySelector('span');
  const toggleIcon = servicesBtn.querySelector('i');
  let expanded = false;
  servicesBtn.addEventListener('click', () => {
    expanded = !expanded;
    secondaryServices.forEach(el => el.classList.toggle('expanded', expanded));
    toggleText.textContent = expanded ? 'Show Less' : 'View All Services';
    toggleIcon.classList.toggle('rotate-180', expanded);
  });
}
</script>
```

**Step 3: Update header.html to use IDs instead of Datastar attributes**

Add `id="menu-toggle"`, `id="mobile-nav"`, `id="menu-icon-open"`, `id="menu-icon-close"` to the relevant elements. Remove all `data-*` attributes from Datastar.

**Step 4: Update services section template**

Add `id="services-toggle"` to the expand button. Remove `data-on:click`, `data-class`, `data-text` attributes.

**Step 5: Rebuild and verify**

Run: `node build.js`
Open pages in browser, verify:
- Header gets shadow on scroll
- Hamburger menu works on mobile
- Services expand/collapse works on mobile

**Step 6: Commit**

```bash
git add templates/
git commit -m "refactor: replace Datastar with vanilla JS"
```

---

## Task 7: Clean Up Old Files & Deploy

**Files:**
- Delete: `index.html` (now generated by build)
- Modify: `.gitignore`

**Step 1: Remove old index.html from git**

The source of truth is now `templates/` + `niches/`. The old `index.html` is no longer needed.

```bash
git rm index.html
```

**Step 2: Verify .gitignore includes `public/`**

Already done in Task 1, but double-check.

**Step 3: Full build + local test**

Run: `node build.js`
Verify all pages render correctly.

**Step 4: Commit and push**

```bash
git add -A
git commit -m "feat: complete landing page system with A/B testing and niche pages"
git push origin main
```

**Step 5: Verify Vercel deployment**

- Visit `davidvandykeinsurance.com` — should serve general variant
- Visit `davidvandykeinsurance.com/landscaper` — should serve landscaper variant
- Check cookies in DevTools
- Verify Cloudflare analytics still fires

---

## Task 8: Update FAQ Copy for Calendly

**Files:**
- Modify: `niches/general.json`

**Step 1: Update the "How do I get a quote?" FAQ answer**

Change from "Send me a quick note through the contact form" to "Book a free 15-minute call using the scheduling link, or call/email me directly."

**Step 2: Rebuild and verify**

Run: `node build.js`

**Step 3: Commit**

```bash
git add niches/general.json
git commit -m "fix: update FAQ copy to reference Calendly instead of contact form"
```

---

## Adding New Niches Later

To add a new niche (e.g., "salon"):

1. Create `niches/salon.json` with variant configs
2. Add `'salon'` to the `NICHES` array in `middleware.js`
3. Update `VARIANT_COUNTS` in `middleware.js`
4. Run `node build.js` to generate pages
5. Commit and push

To add a new variant to an existing niche:

1. Add the variant key (e.g., `"c": { ... }`) to the niche's JSON config
2. Update `VARIANT_COUNTS` in `middleware.js`
3. Rebuild and push

---

## Summary of Niches & Variants

| Niche | URL Path | Initial Variants | Target Audience |
|-------|----------|-----------------|----------------|
| General | `/` | A, B | Personal lines (auto, home, umbrella) |
| Landscaper | `/landscaper` | A, B | Landscaping & lawn care businesses |
| Contractor | `/contractor` | A, B | Electricians, HVAC, plumbers, painters |
| Restaurant | `/restaurant` | A, B | Restaurants, bars, food service |
| Home Business | `/home-business` | A, B | Etsy sellers, Amazon FBA, home bakeries, consultants |
