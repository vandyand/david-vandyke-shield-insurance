# Admin Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a password-protected admin dashboard at `/_admin` that shows all A/B test variants with preview links and live on/off toggles powered by Vercel Edge Config.

**Architecture:** A static admin HTML page makes API calls to a Vercel Serverless Function (`/api/config`). The serverless function reads/writes Vercel Edge Config via the REST API. The existing Edge Middleware reads Edge Config to determine which variants are active when assigning visitors. Three environment variables are needed: `EDGE_CONFIG` (connection string), `EDGE_CONFIG_ID` (for writes), `VERCEL_API_TOKEN` (for writes), and `ADMIN_PASSWORD` (for dashboard auth).

**Tech Stack:** Vanilla HTML/CSS/JS (Tailwind CDN) for the dashboard page, Vercel Serverless Functions (Node.js) for the API, `@vercel/edge-config` SDK for middleware reads, Vercel REST API for writes.

---

## Task 1: Install `@vercel/edge-config` and update package.json

**Files:**
- Modify: `package.json`

**Step 1: Install the dependency**

Run: `npm install @vercel/edge-config`

This adds the SDK that the middleware will use to read Edge Config at the edge.

**Step 2: Verify package.json**

Run: `cat package.json`
Expected: `@vercel/edge-config` appears in `dependencies`.

**Step 3: Commit**

```bash
git add package.json package-lock.json
git commit -m "feat: add @vercel/edge-config dependency"
```

---

## Task 2: Create the API serverless function

**Files:**
- Create: `api/config.js`

**Step 1: Create the serverless function**

Vercel automatically deploys files in `api/` as serverless functions. This function handles:
- `GET /api/config` — reads current Edge Config and returns it (password required)
- `POST /api/config` — updates Edge Config with new variant settings (password required)

```javascript
// api/config.js
export default async function handler(req, res) {
  // CORS headers for the admin page
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  // Check password from Authorization header
  const password = req.headers.authorization?.replace('Bearer ', '');
  if (password !== process.env.ADMIN_PASSWORD) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  const edgeConfigId = process.env.EDGE_CONFIG_ID;
  const vercelToken = process.env.VERCEL_API_TOKEN;

  if (req.method === 'GET') {
    // Read current config from Edge Config REST API
    try {
      const response = await fetch(
        `https://api.vercel.com/v1/edge-config/${edgeConfigId}/items`,
        {
          headers: { Authorization: `Bearer ${vercelToken}` },
        }
      );
      const items = await response.json();
      // items is an array of { key, value } objects
      const abConfig = items.find(item => item.key === 'ab_config');
      return res.status(200).json({
        ab_config: abConfig?.value || null,
      });
    } catch (error) {
      return res.status(500).json({ error: 'Failed to read config' });
    }
  }

  if (req.method === 'POST') {
    // Write updated config to Edge Config
    const { ab_config } = req.body;

    if (!ab_config || typeof ab_config !== 'object') {
      return res.status(400).json({ error: 'Invalid ab_config' });
    }

    try {
      const response = await fetch(
        `https://api.vercel.com/v1/edge-config/${edgeConfigId}/items`,
        {
          method: 'PATCH',
          headers: {
            Authorization: `Bearer ${vercelToken}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            items: [
              {
                operation: 'upsert',
                key: 'ab_config',
                value: ab_config,
              },
            ],
          }),
        }
      );

      if (!response.ok) {
        const err = await response.json();
        return res.status(response.status).json({ error: err.error?.message || 'Update failed' });
      }

      return res.status(200).json({ success: true });
    } catch (error) {
      return res.status(500).json({ error: 'Failed to update config' });
    }
  }

  return res.status(405).json({ error: 'Method not allowed' });
}
```

**Step 2: Commit**

```bash
git add api/config.js
git commit -m "feat: add serverless function for Edge Config read/write"
```

---

## Task 3: Update middleware to read Edge Config

**Files:**
- Modify: `middleware.js`

**Step 1: Rewrite middleware to use Edge Config SDK**

The middleware should read the `ab_config` key from Edge Config to know which variants are active. If Edge Config is unavailable or the key doesn't exist, fall back to all variants active (graceful degradation).

```javascript
import { NextResponse } from 'next/server';
import { get } from '@vercel/edge-config';

const ALL_NICHES = ['landscaper', 'contractor', 'restaurant', 'home-business'];
const VARIANTS = 'abcdefghij';

// Default: all niches have both variants active
const DEFAULT_CONFIG = {
  'general': ['a', 'b'],
  'landscaper': ['a', 'b'],
  'contractor': ['a', 'b'],
  'restaurant': ['a', 'b'],
  'home-business': ['a', 'b'],
};

export async function middleware(request) {
  const { pathname } = request.nextUrl;

  // Determine niche from path
  const nicheSlug = ALL_NICHES.find(n => pathname === `/${n}` || pathname === `/${n}/`);
  const isHome = pathname === '/' || pathname === '/index.html';

  if (!nicheSlug && !isHome) return NextResponse.next();

  const slug = nicheSlug || 'general';

  // Read active variants from Edge Config (with fallback)
  let activeVariants;
  try {
    const abConfig = await get('ab_config');
    activeVariants = abConfig?.[slug] || DEFAULT_CONFIG[slug] || ['a'];
  } catch {
    activeVariants = DEFAULT_CONFIG[slug] || ['a'];
  }

  // If no variants are active, serve variant 'a' as fallback
  if (!activeVariants.length) activeVariants = ['a'];

  const cookieName = `variant_${slug}`;
  const existingVariant = request.cookies.get(cookieName)?.value;

  // Assign variant: use existing if still active, otherwise reassign
  let variant = existingVariant;
  if (!variant || !activeVariants.includes(variant)) {
    variant = activeVariants[Math.floor(Math.random() * activeVariants.length)];
  }

  // Rewrite to correct HTML file
  let target;
  if (slug === 'general') {
    target = variant === 'a' ? '/index.html' : `/general/${variant}.html`;
  } else {
    target = `/${slug}/${variant}.html`;
  }

  const url = request.nextUrl.clone();
  url.pathname = target;
  const response = NextResponse.rewrite(url);

  // Set sticky cookie (30 days)
  response.cookies.set(cookieName, variant, {
    maxAge: 60 * 60 * 24 * 30,
    path: '/',
    sameSite: 'lax',
  });

  return response;
}

export const config = {
  matcher: ['/', '/index.html', '/landscaper', '/landscaper/', '/contractor', '/contractor/', '/restaurant', '/restaurant/', '/home-business', '/home-business/'],
};
```

Key changes from the old middleware:
- Imports `get` from `@vercel/edge-config`
- Reads `ab_config` key to get active variant list per niche
- Falls back to `DEFAULT_CONFIG` if Edge Config is unavailable
- Validates existing cookie against active variants (if a variant was deactivated, reassign the user)
- Function is now `async` (required for Edge Config reads)

**Step 2: Verify the file has no syntax errors**

Run: `node -e "import('./middleware.js')" 2>&1 || echo "Note: import errors expected locally since this runs on Vercel Edge Runtime"`

This will fail locally (no Edge Runtime), but we can check for basic syntax issues.

**Step 3: Commit**

```bash
git add middleware.js
git commit -m "feat: middleware reads active variants from Edge Config"
```

---

## Task 4: Build the admin dashboard HTML page

**Files:**
- Create: `admin/index.html`

**Step 1: Create the admin dashboard page**

This is a standalone HTML page (not generated by the build script). It uses the same Tailwind CDN for styling. The build script should copy it to `public/_admin/index.html`.

The dashboard shows:
- A table of all niches, each with their variants
- Preview links for each variant (direct links that bypass middleware)
- Toggle switches to enable/disable each variant
- A save button that writes changes to Edge Config via `/api/config`
- Status indicator showing if changes are saved/pending

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Admin Dashboard | David VanDyke Insurance</title>
  <meta name="robots" content="noindex, nofollow">
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          colors: {
            navy: { DEFAULT: '#1a365d', light: '#2c5282', dark: '#1a202c' },
            gold: { DEFAULT: '#d69e2e', light: '#ecc94b', dark: '#b7791f' }
          }
        }
      }
    }
  </script>
</head>
<body class="bg-gray-100 min-h-screen font-sans">
  <div id="login-screen" class="min-h-screen flex items-center justify-center">
    <div class="bg-white p-8 rounded-xl shadow-lg max-w-sm w-full">
      <h1 class="text-2xl font-bold text-navy mb-6 text-center">Admin Dashboard</h1>
      <form id="login-form" class="flex flex-col gap-4">
        <input id="password-input" type="password" placeholder="Enter password"
          class="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:outline-none focus:border-gold">
        <button type="submit"
          class="bg-gold text-navy font-bold py-3 rounded-lg hover:bg-gold-dark transition-colors">
          Log In
        </button>
        <p id="login-error" class="text-red-600 text-sm text-center hidden">Incorrect password</p>
      </form>
    </div>
  </div>

  <div id="dashboard" class="hidden">
    <header class="bg-navy text-white px-6 py-4 flex justify-between items-center">
      <h1 class="text-xl font-bold">A/B Test Dashboard</h1>
      <div class="flex items-center gap-4">
        <span id="status" class="text-sm text-green-400">Loaded</span>
        <button id="logout-btn" class="text-white/70 hover:text-white text-sm">Logout</button>
      </div>
    </header>

    <main class="max-w-4xl mx-auto px-4 py-8">
      <div id="niches-container" class="flex flex-col gap-6"></div>

      <div class="mt-8 flex justify-end">
        <button id="save-btn"
          class="bg-gold text-navy font-bold px-8 py-3 rounded-lg shadow hover:bg-gold-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          disabled>
          Save Changes
        </button>
      </div>
    </main>
  </div>

  <script>
    // ── State ─────────────────────────────────────────────────────────────
    let password = '';
    let config = null;    // current saved state
    let pending = null;   // pending changes

    // All known niches and their possible variants (from build system)
    const NICHES = {
      'general':       { name: 'General (Homepage)', variants: ['a', 'b'], path: '/' },
      'landscaper':    { name: 'Landscaper', variants: ['a', 'b'], path: '/landscaper' },
      'contractor':    { name: 'Contractor', variants: ['a', 'b'], path: '/contractor' },
      'restaurant':    { name: 'Restaurant', variants: ['a', 'b'], path: '/restaurant' },
      'home-business': { name: 'Home Business', variants: ['a', 'b'], path: '/home-business' },
    };

    // ── API helpers ───────────────────────────────────────────────────────
    async function apiGet() {
      const res = await fetch('/api/config', {
        headers: { 'Authorization': `Bearer ${password}` },
      });
      if (res.status === 401) throw new Error('Unauthorized');
      return res.json();
    }

    async function apiPost(abConfig) {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${password}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ab_config: abConfig }),
      });
      if (!res.ok) throw new Error('Save failed');
      return res.json();
    }

    // ── Render ─────────────────────────────────────────────────────────────
    function previewUrl(slug, variant) {
      if (slug === 'general') {
        return variant === 'a' ? '/index.html' : `/general/${variant}.html`;
      }
      return `/${slug}/${variant}.html`;
    }

    function render() {
      const container = document.getElementById('niches-container');
      container.innerHTML = '';

      for (const [slug, info] of Object.entries(NICHES)) {
        const active = pending[slug] || [];
        const card = document.createElement('div');
        card.className = 'bg-white rounded-xl shadow border border-gray-200 p-6';
        card.innerHTML = `
          <div class="flex justify-between items-center mb-4">
            <h2 class="text-lg font-bold text-navy">${info.name}</h2>
            <a href="${info.path}" target="_blank" class="text-sm text-gold-dark hover:underline">View live page &rarr;</a>
          </div>
          <div class="flex flex-col gap-3">
            ${info.variants.map(v => {
              const isActive = active.includes(v);
              return `
                <div class="flex items-center justify-between p-3 rounded-lg border ${isActive ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-gray-50'}">
                  <div class="flex items-center gap-3">
                    <span class="text-navy font-semibold text-sm uppercase w-8">V${v.toUpperCase()}</span>
                    <a href="${previewUrl(slug, v)}" target="_blank" class="text-sm text-navy hover:text-gold-dark underline">Preview</a>
                  </div>
                  <label class="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" class="sr-only peer" ${isActive ? 'checked' : ''}
                      data-slug="${slug}" data-variant="${v}"
                      onchange="toggleVariant('${slug}', '${v}', this.checked)">
                    <div class="w-11 h-6 bg-gray-300 peer-checked:bg-green-500 rounded-full
                      after:content-[''] after:absolute after:top-[2px] after:left-[2px]
                      after:bg-white after:rounded-full after:h-5 after:w-5
                      after:transition-all peer-checked:after:translate-x-full"></div>
                  </label>
                </div>`;
            }).join('')}
          </div>
        `;
        container.appendChild(card);
      }

      // Update save button state
      const hasChanges = JSON.stringify(pending) !== JSON.stringify(config);
      document.getElementById('save-btn').disabled = !hasChanges;
      document.getElementById('status').textContent = hasChanges ? 'Unsaved changes' : 'Saved';
      document.getElementById('status').className = hasChanges ? 'text-sm text-yellow-400' : 'text-sm text-green-400';
    }

    // ── Actions ────────────────────────────────────────────────────────────
    function toggleVariant(slug, variant, checked) {
      let active = [...(pending[slug] || [])];
      if (checked && !active.includes(variant)) {
        active.push(variant);
        active.sort();
      } else if (!checked) {
        active = active.filter(v => v !== variant);
      }
      // Don't allow disabling all variants
      if (active.length === 0) {
        alert('At least one variant must be active.');
        render();
        return;
      }
      pending[slug] = active;
      render();
    }

    // ── Login ──────────────────────────────────────────────────────────────
    document.getElementById('login-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      password = document.getElementById('password-input').value;
      try {
        const data = await apiGet();
        // If ab_config is null (first time), initialize with all variants active
        config = data.ab_config || Object.fromEntries(
          Object.entries(NICHES).map(([slug, info]) => [slug, [...info.variants]])
        );
        pending = JSON.parse(JSON.stringify(config));
        document.getElementById('login-screen').classList.add('hidden');
        document.getElementById('dashboard').classList.remove('hidden');
        render();
      } catch {
        document.getElementById('login-error').classList.remove('hidden');
      }
    });

    // ── Save ───────────────────────────────────────────────────────────────
    document.getElementById('save-btn').addEventListener('click', async () => {
      const btn = document.getElementById('save-btn');
      btn.disabled = true;
      btn.textContent = 'Saving...';
      document.getElementById('status').textContent = 'Saving...';
      document.getElementById('status').className = 'text-sm text-yellow-400';
      try {
        await apiPost(pending);
        config = JSON.parse(JSON.stringify(pending));
        document.getElementById('status').textContent = 'Saved — changes go live within 10 seconds';
        document.getElementById('status').className = 'text-sm text-green-400';
      } catch {
        document.getElementById('status').textContent = 'Save failed!';
        document.getElementById('status').className = 'text-sm text-red-400';
      }
      btn.textContent = 'Save Changes';
      render();
    });

    // ── Logout ─────────────────────────────────────────────────────────────
    document.getElementById('logout-btn').addEventListener('click', () => {
      password = '';
      config = null;
      pending = null;
      document.getElementById('dashboard').classList.add('hidden');
      document.getElementById('login-screen').classList.remove('hidden');
      document.getElementById('password-input').value = '';
      document.getElementById('login-error').classList.add('hidden');
    });
  </script>
</body>
</html>
```

**Step 2: Commit**

```bash
git add admin/index.html
git commit -m "feat: add admin dashboard HTML page"
```

---

## Task 5: Update build script to copy admin page

**Files:**
- Modify: `build.js`

**Step 1: Add admin page copy step**

After the existing static asset copy section (images and CNAME), add:

```javascript
// Copy admin dashboard
const adminSrc = path.join(ROOT, 'admin');
const adminDest = path.join(PUBLIC, '_admin');
if (fs.existsSync(adminSrc)) {
  fs.mkdirSync(adminDest, { recursive: true });
  for (const file of fs.readdirSync(adminSrc)) {
    fs.copyFileSync(path.join(adminSrc, file), path.join(adminDest, file));
  }
}
```

This copies `admin/index.html` to `public/_admin/index.html`, making it available at `davidvandykeinsurance.com/_admin`.

**Step 2: Test the build**

Run: `node build.js`
Expected: `public/_admin/index.html` exists alongside the other generated pages.

Run: `ls public/_admin/`
Expected: `index.html`

**Step 3: Commit**

```bash
git add build.js
git commit -m "feat: build script copies admin dashboard to public/_admin"
```

---

## Task 6: Update vercel.json for serverless functions

**Files:**
- Modify: `vercel.json`

**Step 1: Update vercel.json**

Vercel needs to know the API function exists alongside the static output. The `api/` directory is auto-detected by Vercel, but we should ensure the framework isn't interfering. The config should be:

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "public",
  "functions": {
    "api/config.js": {
      "memory": 128,
      "maxDuration": 10
    }
  }
}
```

**Step 2: Commit**

```bash
git add vercel.json
git commit -m "feat: configure serverless function in vercel.json"
```

---

## Task 7: Set up Vercel environment variables and Edge Config store

This task requires manual steps in the Vercel dashboard. The implementer should output clear instructions for the user.

**Step 1: Document the required setup steps**

The user needs to do the following in the Vercel dashboard before deploying:

1. **Create an Edge Config store:**
   - Go to Vercel Dashboard → Project → Storage → Create Database
   - Select "Edge Config" → name it `ab-config` → Create
   - This auto-creates the `EDGE_CONFIG` environment variable

2. **Get the Edge Config ID:**
   - In the Edge Config store page, find the ID (starts with `ecfg_`)
   - Add it as environment variable: `EDGE_CONFIG_ID` = `ecfg_xxxx`

3. **Create a Vercel API Token:**
   - Go to vercel.com/account/tokens
   - Create a new token (scope it to the project if desired)
   - Add it as environment variable: `VERCEL_API_TOKEN` = `the_token`

4. **Set the admin password:**
   - Add environment variable: `ADMIN_PASSWORD` = (a strong password of their choosing)

5. **Initialize Edge Config data:**
   - In the Edge Config store page, click "Add Item"
   - Key: `ab_config`
   - Value: `{"general":["a","b"],"landscaper":["a","b"],"contractor":["a","b"],"restaurant":["a","b"],"home-business":["a","b"]}`

**Step 2: Create a setup instructions file**

Create `docs/ADMIN-SETUP.md` with the above instructions formatted clearly.

**Step 3: Commit**

```bash
git add docs/ADMIN-SETUP.md
git commit -m "docs: add admin dashboard setup instructions"
```

---

## Task 8: Final integration test and deploy

**Files:**
- No new files

**Step 1: Verify the full build**

Run: `node build.js`
Expected: All 10 landing pages + admin dashboard generated.

Run: `ls public/_admin/ && ls api/`
Expected: `index.html` in admin, `config.js` in api.

**Step 2: Verify no leftover issues**

Run: `grep -r 'formspree' . --include='*.html' --include='*.js' | grep -v node_modules | grep -v public`
Expected: No results (formspree fully removed).

Run: `grep -r 'datastar' . --include='*.html' --include='*.js' | grep -v node_modules | grep -v public`
Expected: No results (datastar fully removed).

**Step 3: Commit any remaining changes and push**

```bash
git add -A
git commit -m "feat: complete admin dashboard with Edge Config integration"
git push origin main
```

**Step 4: After push, user must complete Vercel setup**

Remind the user to complete the Vercel dashboard setup from Task 7 before the dashboard will work. The landing pages will work immediately; only the admin dashboard requires the environment variables.

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Install `@vercel/edge-config` | `package.json` |
| 2 | Create API serverless function | `api/config.js` |
| 3 | Update middleware for Edge Config | `middleware.js` |
| 4 | Build admin dashboard HTML | `admin/index.html` |
| 5 | Build script copies admin page | `build.js` |
| 6 | Update vercel.json for functions | `vercel.json` |
| 7 | Setup instructions doc | `docs/ADMIN-SETUP.md` |
| 8 | Integration test and deploy | — |

## Environment Variables Required

| Variable | Where to get it | Purpose |
|----------|----------------|---------|
| `EDGE_CONFIG` | Auto-created when connecting Edge Config to project | SDK connection string |
| `EDGE_CONFIG_ID` | Edge Config store page (starts with `ecfg_`) | REST API writes |
| `VERCEL_API_TOKEN` | vercel.com/account/tokens | REST API auth |
| `ADMIN_PASSWORD` | You choose | Dashboard login |
