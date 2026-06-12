# Speed-to-Lead Responder (MVP) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When a new insurance lead submits the site's lead form, instantly email them a warm reply with a Calendly booking link, notify David, and send one nudge email if they haven't booked — turning raw leads into booked calls before they go cold.

**Architecture:** A new `api/lead-intake.js` Vercel function receives leads from our own landing-page form (and can also receive Make/Zapier-forwarded leads). Each lead is normalized, written to the existing Google Sheet, and immediately emailed (lead + David) via Resend. A Calendly webhook (`api/calendly-webhook.js`) flips the lead's Sheet status to `Booked`. A cron (`api/cron/lead-nudge.js`) sends one follow-up to leads still un-booked after a delay. The Sheet's `status` field is the state machine: `Contacted → Nudged → Booked`. No SMS, no Meta API, no new datastore.

**Tech Stack:** Vanilla ESM Vercel serverless functions (matches repo), Resend (email — already wired), Google Sheets Apps Script web app (existing lead store), Calendly (booking link + webhook), `node:test` (built-in test runner — keeps the repo's near-zero-dep footprint).

**Testability convention:** Each handler is a thin Vercel wrapper around a pure-ish `core(input, deps)` function. Tests exercise `core` with injected fake deps (`sheet`, `send`); the wrapper just adapts `req`/`res`. No network in tests.

---

## Operator Prerequisites (Task 0)

These are human setup steps with no code. Do them before Task 6.

- [ ] **Calendly:** create/confirm a public scheduling link for David (e.g. a 15-min "Insurance Quote Call"). Record the URL — it becomes env var `CALENDLY_BOOKING_URL`.
- [ ] **Calendly webhook:** in Calendly (Integrations → Webhooks, or via API) create a webhook subscription for the `invitee.created` event pointing at `https://davidvandykeinsurance.com/api/calendly-webhook`. Record the **signing key** → env var `CALENDLY_WEBHOOK_SIGNING_KEY`.
- [ ] **Resend:** confirm `pragmagen.xyz` is a verified sending domain in Resend (the existing functions already send from `leads@pragmagen.xyz`, so this should already be true). The responder also emails *leads* (not just David) — confirm Resend plan limits cover pilot volume.
- [ ] **Vercel env vars:** add `CALENDLY_BOOKING_URL`, `CALENDLY_WEBHOOK_SIGNING_KEY`, and `LEAD_NUDGE_DELAY_HOURS` (set to `3`) to the project. `RESEND_API_KEY`, `LEADS_SHEET_URL`, `LEADS_SHEET_TOKEN`, `CRON_SECRET` already exist.
- [ ] **Google Sheet:** confirm the Apps Script web app accepts the existing `{mode:'append', ...lead}` POST shape and that leads have a `status` column and a `created_at` column. The responder writes `status` values `Contacted`, `Nudged`, `Booked`. No schema change needed beyond those columns already used by `poll-meta-leads.js`.
- [ ] **(Out of scope, track separately)** Twilio SMS — verification was rejected; retry later via the sole-proprietor 10DLC path. Not part of this plan.

---

## File Structure

- `lib/lead.js` — `normalizeLead(raw, source)`: pure normalization to a canonical lead shape.
- `lib/emails.js` — pure email-template functions returning `{subject, html}`.
- `lib/sheet.js` — Google Sheet client: `listLeads`, `appendLead`, `updateLeadStatus`.
- `lib/send.js` — `sendEmail(...)`: Resend wrapper.
- `lib/test-helpers.js` — `withMockFetch(routes, fn)` test utility.
- `api/lead-intake.js` — POST: receive a lead, store, email lead + David. Exports `handleLeadIntake(lead, deps)` core.
- `api/calendly-webhook.js` — POST: verify signature, mark lead `Booked`, notify David. Exports `handleCalendlyEvent(payload, deps)` core.
- `api/cron/lead-nudge.js` — cron: nudge un-booked leads. Exports `runNudge(now, deps)` core.
- `templates/sections/lead-form.html` — short top-of-funnel lead form section.
- `vercel.json` — add the nudge cron entry.
- `package.json` — add `test` script.

---

### Task 1: Test harness

**Files:**
- Create: `lib/test-helpers.js`
- Modify: `package.json` (add `test` script)
- Test: `lib/test-helpers.test.js`

- [ ] **Step 1: Write the failing test**

```js
// lib/test-helpers.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { withMockFetch } from './test-helpers.js';

test('withMockFetch routes calls by URL substring and restores fetch', async () => {
  const original = globalThis.fetch;
  const calls = [];
  await withMockFetch(
    [{ match: 'example.com', response: { ok: true, json: { id: 'x1' } } }],
    async () => {
      const r = await fetch('https://example.com/thing', { method: 'POST', body: '{}' });
      calls.push(await r.json());
    }
  );
  assert.equal(calls[0].id, 'x1');
  assert.equal(globalThis.fetch, original, 'fetch is restored after the block');
});

test('withMockFetch records requests and throws on unmatched URL', async () => {
  await assert.rejects(
    withMockFetch([], async () => { await fetch('https://nope.test/x'); }),
    /no mock route/i
  );
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test lib/test-helpers.test.js`
Expected: FAIL — `Cannot find module './test-helpers.js'`.

- [ ] **Step 3: Write minimal implementation**

```js
// lib/test-helpers.js
// Test-only helper. Swaps globalThis.fetch for a route-matching mock, restores it after.
export async function withMockFetch(routes, fn) {
  const original = globalThis.fetch;
  const requests = [];
  globalThis.fetch = async (url, opts = {}) => {
    const u = String(url);
    requests.push({ url: u, opts });
    const route = routes.find(r => u.includes(r.match));
    if (!route) {
      throw new Error(`no mock route for ${u}`);
    }
    const res = route.response || {};
    return {
      ok: res.ok !== false,
      status: res.status || (res.ok === false ? 500 : 200),
      json: async () => res.json ?? {},
      text: async () => res.text ?? JSON.stringify(res.json ?? {}),
    };
  };
  try {
    await fn(requests);
  } finally {
    globalThis.fetch = original;
  }
}
```

- [ ] **Step 4: Add the test script to package.json**

Modify `package.json` — add a `test` entry to `scripts` so it reads:

```json
  "scripts": {
    "build": "node build.cjs",
    "test": "node --test"
  },
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npm test`
Expected: PASS — 2 tests pass (`node --test` discovers `*.test.js` files).

- [ ] **Step 6: Commit**

```bash
git add lib/test-helpers.js lib/test-helpers.test.js package.json
git commit -m "test: add node:test harness and fetch mock helper"
```

---

### Task 2: Lead normalization

**Files:**
- Create: `lib/lead.js`
- Test: `lib/lead.test.js`

A lead can arrive from our own form (`source: 'website-form'`) or a Make/Zapier-forwarded Meta lead (`source: 'meta'`). `normalizeLead` produces one canonical shape and always assigns an `id` (using the incoming Meta `id` if present, else a generated one).

- [ ] **Step 1: Write the failing test**

```js
// lib/lead.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { normalizeLead } from './lead.js';

test('normalizeLead maps website form fields and generates an id', () => {
  const lead = normalizeLead(
    { name: 'Jane Doe', email: 'jane@x.com', phone: '616-555-0100', insurance_type: 'auto', niche: 'contractor' },
    'website-form'
  );
  assert.equal(lead.name, 'Jane Doe');
  assert.equal(lead.email, 'jane@x.com');
  assert.equal(lead.phone, '616-555-0100');
  assert.equal(lead.type, 'auto');
  assert.equal(lead.niche, 'contractor');
  assert.equal(lead.source, 'website-form');
  assert.match(lead.id, /^web_/);
  assert.ok(lead.created_at, 'created_at is set');
  assert.equal(lead.status, 'New');
});

test('normalizeLead keeps an incoming Meta id and trims fields', () => {
  const lead = normalizeLead(
    { id: '99001', full_name: '  Bob  ', email: 'BOB@X.COM ', phone_number: ' 100 ', insurance_type: 'home' },
    'meta'
  );
  assert.equal(lead.id, '99001');
  assert.equal(lead.name, 'Bob');
  assert.equal(lead.email, 'bob@x.com');
  assert.equal(lead.phone, '100');
  assert.equal(lead.source, 'meta');
});

test('normalizeLead throws when name and contact info are all missing', () => {
  assert.throws(() => normalizeLead({}, 'website-form'), /lead requires/i);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test lib/lead.test.js`
Expected: FAIL — `Cannot find module './lead.js'`.

- [ ] **Step 3: Write minimal implementation**

```js
// lib/lead.js
// Canonical lead shape used across the responder. Accepts website-form and Meta payloads.
import { randomUUID } from 'node:crypto';

const s = (v) => String(v ?? '').trim();

export function normalizeLead(raw, source) {
  const name = s(raw.name || raw.full_name);
  const email = s(raw.email || raw.contact_email).toLowerCase();
  const phone = s(raw.phone || raw.phone_number || raw.contact_phone);
  if (!name && !email && !phone) {
    throw new Error('lead requires at least a name, email, or phone');
  }
  const id = s(raw.id) || `web_${randomUUID().slice(0, 8)}`;
  return {
    id,
    name,
    email,
    phone,
    type: s(raw.type || raw.insurance_type),
    niche: s(raw.niche),
    source,
    created_at: s(raw.created_at) || new Date().toISOString(),
    status: 'New',
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test lib/lead.test.js`
Expected: PASS — 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add lib/lead.js lib/lead.test.js
git commit -m "feat: add canonical lead normalization"
```

---

### Task 3: Email templates

**Files:**
- Create: `lib/emails.js`
- Test: `lib/emails.test.js`

Pure functions returning `{subject, html}`. `leadWelcomeEmail` and `leadNudgeEmail` go to the *lead* and contain the booking link. `davidNewLeadEmail` and `davidBookedEmail` go to David.

- [ ] **Step 1: Write the failing test**

```js
// lib/emails.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { leadWelcomeEmail, leadNudgeEmail, davidNewLeadEmail, davidBookedEmail } from './emails.js';

const lead = { id: 'web_1', name: 'Jane Doe', email: 'jane@x.com', phone: '616-555-0100', type: 'auto' };
const bookingUrl = 'https://calendly.com/david/quote?name=Jane%20Doe';

test('leadWelcomeEmail addresses the lead and embeds the booking link', () => {
  const { subject, html } = leadWelcomeEmail(lead, bookingUrl);
  assert.match(subject, /Jane/);
  assert.ok(html.includes(bookingUrl), 'booking link present');
  assert.ok(html.includes('Jane'), 'lead first name present');
});

test('leadNudgeEmail is a distinct follow-up that still has the booking link', () => {
  const { subject, html } = leadNudgeEmail(lead, bookingUrl);
  assert.notEqual(subject, leadWelcomeEmail(lead, bookingUrl).subject);
  assert.ok(html.includes(bookingUrl));
});

test('davidNewLeadEmail summarizes the lead for David', () => {
  const { subject, html } = davidNewLeadEmail(lead);
  assert.match(subject, /Jane Doe/);
  assert.ok(html.includes('616-555-0100'));
});

test('davidBookedEmail announces a booked call', () => {
  const { subject, html } = davidBookedEmail(lead);
  assert.match(subject, /booked/i);
  assert.ok(html.includes('Jane Doe'));
});

test('email HTML escapes lead-supplied values', () => {
  const evil = { ...lead, name: 'A<script>x</script>' };
  const { html } = davidNewLeadEmail(evil);
  assert.ok(!html.includes('<script>'), 'script tag escaped');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test lib/emails.test.js`
Expected: FAIL — `Cannot find module './emails.js'`.

- [ ] **Step 3: Write minimal implementation**

```js
// lib/emails.js
// Pure email-template functions. Each returns { subject, html }.
const esc = (v) => String(v ?? '').replace(/[<>&"]/g, c => (
  { '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[c]));
const firstName = (name) => esc(String(name || 'there').trim().split(/\s+/)[0]);

const NAVY = '#1a365d';

function shell(headline, bodyHtml) {
  return `
  <div style="font-family:-apple-system,sans-serif;max-width:600px;margin:0 auto;padding:24px">
    <div style="background:${NAVY};color:#fff;padding:20px 24px;border-radius:8px 8px 0 0">
      <h1 style="margin:0;font-size:20px">${headline}</h1>
    </div>
    <div style="border:1px solid #e2e8f0;border-top:none;padding:24px;border-radius:0 0 8px 8px">
      ${bodyHtml}
    </div>
  </div>`;
}

function bookButton(bookingUrl) {
  return `<p style="margin:24px 0"><a href="${esc(bookingUrl)}"
    style="background:#d69e2e;color:#1a202c;font-weight:700;padding:14px 28px;
    border-radius:6px;text-decoration:none;display:inline-block">Book your quote call →</a></p>`;
}

export function leadWelcomeEmail(lead, bookingUrl) {
  return {
    subject: `${firstName(lead.name)}, let's get your insurance quote started`,
    html: shell('Thanks for reaching out to Shield Insurance', `
      <p style="font-size:16px;color:#1a202c">Hi ${firstName(lead.name)},</p>
      <p style="font-size:15px;color:#4a5568">Thanks for your interest in an insurance quote.
      David VanDyke is an independent agent who shops multiple carriers to find you the right
      coverage at the best price. The fastest way to get your quote is a quick 15-minute call —
      pick a time that works for you:</p>
      ${bookButton(bookingUrl)}
      <p style="font-size:13px;color:#a0aec0">If the button doesn't work, copy this link:
      <br>${esc(bookingUrl)}</p>`),
  };
}

export function leadNudgeEmail(lead, bookingUrl) {
  return {
    subject: `${firstName(lead.name)}, still want that insurance quote?`,
    html: shell('Your quote call is one click away', `
      <p style="font-size:16px;color:#1a202c">Hi ${firstName(lead.name)},</p>
      <p style="font-size:15px;color:#4a5568">Just following up — David still has time set aside
      to get you a no-obligation quote. It only takes 15 minutes:</p>
      ${bookButton(bookingUrl)}
      <p style="font-size:13px;color:#a0aec0">Prefer email? Just reply to this message.</p>`),
  };
}

export function davidNewLeadEmail(lead) {
  return {
    subject: `New lead: ${esc(lead.name) || 'Unknown'} — ${esc(lead.type) || 'insurance'}`,
    html: shell('🎯 New Lead — Shield Insurance', `
      <p style="font-size:15px;color:#4a5568">A new lead came in and has been emailed an
      instant reply with your booking link.</p>
      <table style="width:100%;border-collapse:collapse;font-size:15px">
        <tr><td style="padding:8px 0;color:#718096;width:120px">Name</td>
            <td style="padding:8px 0;font-weight:600">${esc(lead.name) || 'Unknown'}</td></tr>
        <tr><td style="padding:8px 0;color:#718096">Phone</td>
            <td style="padding:8px 0;font-weight:600">${esc(lead.phone) || 'Not provided'}</td></tr>
        <tr><td style="padding:8px 0;color:#718096">Email</td>
            <td style="padding:8px 0">${esc(lead.email) || 'Not provided'}</td></tr>
        <tr><td style="padding:8px 0;color:#718096">Looking for</td>
            <td style="padding:8px 0;font-weight:600">${esc(lead.type) || 'Not specified'}</td></tr>
      </table>`),
  };
}

export function davidBookedEmail(lead) {
  return {
    subject: `✅ Call booked: ${esc(lead.name) || 'a lead'}`,
    html: shell('✅ A lead just booked a call', `
      <p style="font-size:15px;color:#4a5568"><strong>${esc(lead.name) || 'A lead'}</strong>
      booked a quote call. Check your Calendly for the time.</p>
      <table style="width:100%;border-collapse:collapse;font-size:15px">
        <tr><td style="padding:8px 0;color:#718096;width:120px">Phone</td>
            <td style="padding:8px 0;font-weight:600">${esc(lead.phone) || 'Not provided'}</td></tr>
        <tr><td style="padding:8px 0;color:#718096">Email</td>
            <td style="padding:8px 0">${esc(lead.email) || 'Not provided'}</td></tr>
      </table>`),
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test lib/emails.test.js`
Expected: PASS — 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add lib/emails.js lib/emails.test.js
git commit -m "feat: add responder email templates"
```

---

### Task 4: Google Sheet client

**Files:**
- Create: `lib/sheet.js`
- Test: `lib/sheet.test.js`

Wraps the existing Apps Script web app (`LEADS_SHEET_URL` + `LEADS_SHEET_TOKEN`). Reuses the proven patterns from `api/leads.js` and `api/cron/poll-meta-leads.js` — notably: append POSTs return a 302 redirect that must be treated as success.

- [ ] **Step 1: Write the failing test**

```js
// lib/sheet.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { withMockFetch } from './test-helpers.js';
import { listLeads, appendLead, updateLeadStatus } from './sheet.js';

test('listLeads returns the leads array from the sheet', async () => {
  await withMockFetch(
    [{ match: 'SHEET', response: { json: { leads: [{ id: 'a', status: 'Contacted' }] } } }],
    async () => {
      const leads = await listLeads({ url: 'https://SHEET', token: 't' });
      assert.equal(leads.length, 1);
      assert.equal(leads[0].id, 'a');
    }
  );
});

test('appendLead treats a 302 redirect as success', async () => {
  await withMockFetch(
    [{ match: 'SHEET', response: { ok: false, status: 302 } }],
    async () => {
      const ok = await appendLead({ url: 'https://SHEET', token: 't' }, { id: 'b', status: 'Contacted' });
      assert.equal(ok, true);
    }
  );
});

test('updateLeadStatus posts an id+status payload', async () => {
  await withMockFetch(
    [{ match: 'SHEET', response: { ok: true, status: 200 } }],
    async (requests) => {
      await updateLeadStatus({ url: 'https://SHEET', token: 't' }, 'b', 'Booked');
      const body = JSON.parse(requests.at(-1).opts.body);
      assert.equal(body.id, 'b');
      assert.equal(body.status, 'Booked');
    }
  );
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test lib/sheet.test.js`
Expected: FAIL — `Cannot find module './sheet.js'`.

- [ ] **Step 3: Write minimal implementation**

```js
// lib/sheet.js
// Google Sheet client over the Apps Script web app. cfg = { url, token }.
function endpoint(cfg) {
  return `${cfg.url}?token=${encodeURIComponent(cfg.token)}`;
}

export async function listLeads(cfg) {
  const r = await fetch(endpoint(cfg), { redirect: 'follow' });
  if (!r.ok) throw new Error(`sheet read failed: ${r.status}`);
  const data = await r.json();
  if (data.error) throw new Error(`sheet error: ${data.error}`);
  return Array.isArray(data.leads) ? data.leads : [];
}

export async function appendLead(cfg, lead) {
  const r = await fetch(endpoint(cfg), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode: 'append', ...lead }),
    redirect: 'manual',
  });
  // Apps Script 302-redirects after a successful doPost; the redirect target 405s. Treat 302/2xx as success.
  if (r.status !== 302 && !r.ok) throw new Error(`sheet append failed: ${r.status}`);
  return true;
}

export async function updateLeadStatus(cfg, id, status) {
  const r = await fetch(endpoint(cfg), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, status }),
    redirect: 'manual',
  });
  if (r.status !== 302 && !r.ok) throw new Error(`sheet status update failed: ${r.status}`);
  return true;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test lib/sheet.test.js`
Expected: PASS — 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add lib/sheet.js lib/sheet.test.js
git commit -m "feat: add Google Sheet lead client"
```

---

### Task 5: Resend send wrapper

**Files:**
- Create: `lib/send.js`
- Test: `lib/send.test.js`

- [ ] **Step 1: Write the failing test**

```js
// lib/send.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { withMockFetch } from './test-helpers.js';
import { sendEmail } from './send.js';

test('sendEmail posts to Resend with from/to/subject/html', async () => {
  await withMockFetch(
    [{ match: 'api.resend.com', response: { ok: true, json: { id: 'e1' } } }],
    async (requests) => {
      const id = await sendEmail({ apiKey: 'k' }, {
        from: 'X <a@b.com>', to: 'c@d.com', subject: 'Hi', html: '<p>Hi</p>',
      });
      assert.equal(id, 'e1');
      const body = JSON.parse(requests.at(-1).opts.body);
      assert.deepEqual(body.to, ['c@d.com']);
      assert.equal(body.subject, 'Hi');
    }
  );
});

test('sendEmail throws on a Resend error response', async () => {
  await withMockFetch(
    [{ match: 'api.resend.com', response: { ok: false, status: 422, json: { message: 'bad' } } }],
    async () => {
      await assert.rejects(
        sendEmail({ apiKey: 'k' }, { from: 'x', to: 'y', subject: 's', html: 'h' }),
        /resend/i
      );
    }
  );
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test lib/send.test.js`
Expected: FAIL — `Cannot find module './send.js'`.

- [ ] **Step 3: Write minimal implementation**

```js
// lib/send.js
// Resend email wrapper. cfg = { apiKey }. msg = { from, to, replyTo?, subject, html }.
export async function sendEmail(cfg, msg) {
  const body = {
    from: msg.from,
    to: Array.isArray(msg.to) ? msg.to : [msg.to],
    subject: msg.subject,
    html: msg.html,
  };
  if (msg.replyTo) body.reply_to = msg.replyTo;
  const r = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${cfg.apiKey}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const result = await r.json();
  if (!r.ok) throw new Error(`Resend error: ${JSON.stringify(result)}`);
  return result.id;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test lib/send.test.js`
Expected: PASS — 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add lib/send.js lib/send.test.js
git commit -m "feat: add Resend send wrapper"
```

---

### Task 6: Lead-intake handler

**Files:**
- Create: `api/lead-intake.js`
- Test: `api/lead-intake.test.js`

`handleLeadIntake(rawLead, source, deps)` is the testable core. `deps` = `{ sheet, send, bookingUrl, davidEmail, fromEmail }` where `sheet`/`send` are objects with the needed methods. The Vercel `handler` builds real deps from env and adapts `req`/`res`.

Booking URL is personalized per lead: `${CALENDLY_BOOKING_URL}?name=<name>&email=<email>`.

- [ ] **Step 1: Write the failing test**

```js
// api/lead-intake.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { handleLeadIntake, personalizedBookingUrl } from './lead-intake.js';

function fakeDeps() {
  const sent = [];
  const appended = [];
  return {
    sent, appended,
    deps: {
      bookingUrl: 'https://calendly.com/david/quote',
      davidEmail: 'david@x.com',
      fromEmail: 'Shield <leads@pragmagen.xyz>',
      sheet: {
        appendLead: async (lead) => { appended.push(lead); return true; },
      },
      send: {
        sendEmail: async (msg) => { sent.push(msg); return 'e_' + sent.length; },
      },
    },
  };
}

test('personalizedBookingUrl appends name and email params', () => {
  const url = personalizedBookingUrl('https://c.com/x', { name: 'Jane Doe', email: 'j@x.com' });
  assert.match(url, /name=Jane(\+|%20)Doe/);
  assert.match(url, /email=j%40x\.com/);
});

test('handleLeadIntake emails the lead and David, then appends with status Contacted', async () => {
  const { deps, sent, appended } = fakeDeps();
  const result = await handleLeadIntake(
    { name: 'Jane Doe', email: 'jane@x.com', phone: '616-555-0100', insurance_type: 'auto' },
    'website-form',
    deps
  );
  assert.equal(result.ok, true);
  const recipients = sent.map(m => m.to);
  assert.ok(recipients.includes('jane@x.com'), 'lead emailed');
  assert.ok(recipients.includes('david@x.com'), 'David emailed');
  assert.equal(appended.length, 1);
  assert.equal(appended[0].status, 'Contacted');
  assert.match(appended[0].id, /^web_/);
});

test('handleLeadIntake still appends the lead if the lead email send fails', async () => {
  const { deps, appended } = fakeDeps();
  deps.send.sendEmail = async (msg) => {
    if (msg.to === 'jane@x.com') throw new Error('resend down');
    return 'e1';
  };
  const result = await handleLeadIntake(
    { name: 'Jane Doe', email: 'jane@x.com', phone: '1' }, 'website-form', deps
  );
  assert.equal(result.ok, true);
  assert.equal(appended.length, 1, 'lead is recorded even when its email failed');
  assert.equal(appended[0].status, 'New', 'status reflects that contact did not complete');
});

test('handleLeadIntake rejects an empty lead', async () => {
  const { deps } = fakeDeps();
  await assert.rejects(handleLeadIntake({}, 'website-form', deps), /lead requires/i);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test api/lead-intake.test.js`
Expected: FAIL — `Cannot find module './lead-intake.js'`.

- [ ] **Step 3: Write minimal implementation**

```js
// api/lead-intake.js
// POST: receive a lead (our landing-page form, or a Make/Zapier-forwarded lead),
// instantly email the lead + David, and record it in the Google Sheet.
import { normalizeLead } from '../lib/lead.js';
import { leadWelcomeEmail, davidNewLeadEmail } from '../lib/emails.js';
import { appendLead } from '../lib/sheet.js';
import { sendEmail } from '../lib/send.js';

export function personalizedBookingUrl(base, lead) {
  const u = new URL(base);
  if (lead.name) u.searchParams.set('name', lead.name);
  if (lead.email) u.searchParams.set('email', lead.email);
  return u.toString();
}

// Testable core. deps = { bookingUrl, davidEmail, fromEmail, sheet:{appendLead}, send:{sendEmail} }.
export async function handleLeadIntake(rawLead, source, deps) {
  const lead = normalizeLead(rawLead, source);
  const bookingUrl = personalizedBookingUrl(deps.bookingUrl, lead);

  let contacted = true;
  if (lead.email) {
    const welcome = leadWelcomeEmail(lead, bookingUrl);
    try {
      await deps.send.sendEmail({ from: deps.fromEmail, to: lead.email, ...welcome });
    } catch (e) {
      contacted = false;
      console.error(`lead welcome email failed for ${lead.id}:`, e.message);
    }
  } else {
    contacted = false; // no email address — cannot run the email responder
  }

  const davidMsg = davidNewLeadEmail(lead);
  try {
    await deps.send.sendEmail({ from: deps.fromEmail, to: deps.davidEmail, ...davidMsg });
  } catch (e) {
    console.error(`David notify email failed for ${lead.id}:`, e.message);
  }

  lead.status = contacted ? 'Contacted' : 'New';
  await deps.sheet.appendLead(lead);
  return { ok: true, id: lead.id, status: lead.status };
}

function cleanEnv(v) { return (v || '').replace(/\\n/g, '').replace(/\n/g, '').trim(); }

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const deps = {
    bookingUrl: cleanEnv(process.env.CALENDLY_BOOKING_URL),
    davidEmail: 'davidvd@shieldagency.com',
    fromEmail: 'Shield Insurance Leads <leads@pragmagen.xyz>',
    sheet: {
      appendLead: (lead) => appendLead(
        { url: cleanEnv(process.env.LEADS_SHEET_URL), token: cleanEnv(process.env.LEADS_SHEET_TOKEN) },
        lead
      ),
    },
    send: {
      sendEmail: (msg) => sendEmail({ apiKey: cleanEnv(process.env.RESEND_API_KEY) }, msg),
    },
  };

  try {
    const result = await handleLeadIntake(req.body || {}, req.body?.source || 'website-form', deps);
    return res.status(200).json(result);
  } catch (err) {
    console.error('lead-intake error:', err.message);
    return res.status(400).json({ error: err.message || 'Bad request' });
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test api/lead-intake.test.js`
Expected: PASS — 4 tests pass.

- [ ] **Step 5: Run the full suite**

Run: `npm test`
Expected: PASS — all tests across all files pass.

- [ ] **Step 6: Commit**

```bash
git add api/lead-intake.js api/lead-intake.test.js
git commit -m "feat: add lead-intake handler with instant email responder"
```

---

### Task 7: Short top-of-funnel lead form

**Files:**
- Create: `templates/sections/lead-form.html`
- Reference: `templates/sections/contact.html` (existing form section — match its markup/style conventions before writing this)

The existing `contact.html` / `quote` form is a long high-intent form. Cold ad traffic needs a *short* form: name, email, phone, insurance type. It POSTs JSON to `/api/lead-intake`.

- [ ] **Step 1: Read the existing section for conventions**

Run: `cat templates/sections/contact.html`
Note the wrapper classes, Tailwind utility patterns, and how `build.cjs` includes sections, so the new section is consistent.

- [ ] **Step 2: Create the lead-form section**

```html
<!-- templates/sections/lead-form.html -->
<!-- Short top-of-funnel lead form. Posts JSON to /api/lead-intake. -->
<section id="lead-form" class="bg-slate-50 py-12 px-4">
  <div class="max-w-md mx-auto">
    <h2 class="text-2xl font-bold text-slate-900 text-center">Get your free quote</h2>
    <p class="text-slate-600 text-center mt-2 mb-6">
      Takes 30 seconds. David will help you find the right coverage at the best price.
    </p>
    <form id="leadForm" class="space-y-4">
      <input name="name" type="text" required placeholder="Full name"
        class="w-full px-4 py-3 rounded-lg border border-slate-300" />
      <input name="email" type="email" required placeholder="Email"
        class="w-full px-4 py-3 rounded-lg border border-slate-300" />
      <input name="phone" type="tel" required placeholder="Phone"
        class="w-full px-4 py-3 rounded-lg border border-slate-300" />
      <select name="insurance_type" required
        class="w-full px-4 py-3 rounded-lg border border-slate-300 text-slate-700">
        <option value="">What do you need insured?</option>
        <option value="auto">Auto</option>
        <option value="home">Home</option>
        <option value="auto+home">Auto + Home (bundle)</option>
        <option value="business">Business</option>
        <option value="other">Something else</option>
      </select>
      <button type="submit"
        class="w-full bg-amber-500 hover:bg-amber-600 text-slate-900 font-bold py-3 rounded-lg">
        Get my free quote →
      </button>
      <p id="leadFormMsg" class="text-center text-sm"></p>
    </form>
  </div>
  <script>
    document.getElementById('leadForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = e.target;
      const msg = document.getElementById('leadFormMsg');
      const btn = form.querySelector('button');
      btn.disabled = true; msg.textContent = 'Sending…'; msg.className = 'text-center text-sm text-slate-500';
      const payload = Object.fromEntries(new FormData(form).entries());
      payload.source = 'website-form';
      payload.niche = (document.body.dataset.niche || '');
      try {
        const r = await fetch('/api/lead-intake', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!r.ok) throw new Error('failed');
        msg.textContent = 'Done! Check your email for a link to book your quote call.';
        msg.className = 'text-center text-sm text-green-600';
        form.reset();
      } catch (err) {
        msg.textContent = 'Something went wrong — please call David directly at the number above.';
        msg.className = 'text-center text-sm text-red-600';
        btn.disabled = false;
      }
    });
  </script>
</section>
```

- [ ] **Step 3: Verify the build picks up the new section**

Run: `npm run build`
Expected: build completes; if `build.cjs` requires sections to be referenced in a niche JSON or a template, add `lead-form` there following the existing pattern for `contact`. Confirm a compiled page in `public/` contains the `leadForm` markup.

- [ ] **Step 4: Commit**

```bash
git add templates/sections/lead-form.html
git commit -m "feat: add short top-of-funnel lead form section"
```

---

### Task 8: Calendly webhook — mark booked

**Files:**
- Create: `api/calendly-webhook.js`
- Test: `api/calendly-webhook.test.js`

Calendly signs webhooks with an HMAC-SHA256 over `t,<timestamp>;v1,<payload>` using the signing key. On `invitee.created`, match the invitee email to a lead and set its Sheet status to `Booked`, then email David.

- [ ] **Step 1: Write the failing test**

```js
// api/calendly-webhook.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { handleCalendlyEvent } from './calendly-webhook.js';

function fakeDeps(leads) {
  const updates = [];
  const sent = [];
  return {
    updates, sent,
    deps: {
      davidEmail: 'david@x.com',
      fromEmail: 'Shield <leads@pragmagen.xyz>',
      sheet: {
        listLeads: async () => leads,
        updateLeadStatus: async (id, status) => { updates.push({ id, status }); return true; },
      },
      send: { sendEmail: async (m) => { sent.push(m); return 'e1'; } },
    },
  };
}

test('invitee.created flips the matching lead to Booked and emails David', async () => {
  const { deps, updates, sent } = fakeDeps([
    { id: 'web_1', email: 'jane@x.com', name: 'Jane Doe', status: 'Contacted' },
  ]);
  const result = await handleCalendlyEvent(
    { event: 'invitee.created', payload: { email: 'JANE@x.com', name: 'Jane Doe' } },
    deps
  );
  assert.equal(result.matched, true);
  assert.deepEqual(updates[0], { id: 'web_1', status: 'Booked' });
  assert.equal(sent[0].to, 'david@x.com');
});

test('a non-created event is ignored', async () => {
  const { deps, updates } = fakeDeps([]);
  const result = await handleCalendlyEvent({ event: 'invitee.canceled', payload: {} }, deps);
  assert.equal(result.ignored, true);
  assert.equal(updates.length, 0);
});

test('an invitee with no matching lead does not update anything', async () => {
  const { deps, updates } = fakeDeps([{ id: 'web_1', email: 'someone@else.com' }]);
  const result = await handleCalendlyEvent(
    { event: 'invitee.created', payload: { email: 'ghost@x.com' } }, deps
  );
  assert.equal(result.matched, false);
  assert.equal(updates.length, 0);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test api/calendly-webhook.test.js`
Expected: FAIL — `Cannot find module './calendly-webhook.js'`.

- [ ] **Step 3: Write minimal implementation**

```js
// api/calendly-webhook.js
// POST: Calendly webhook. On invitee.created, mark the matching lead Booked and notify David.
import { createHmac, timingSafeEqual } from 'node:crypto';
import { listLeads, updateLeadStatus } from '../lib/sheet.js';
import { davidBookedEmail } from '../lib/emails.js';
import { sendEmail } from '../lib/send.js';

// Testable core. deps = { davidEmail, fromEmail, sheet:{listLeads,updateLeadStatus}, send:{sendEmail} }.
export async function handleCalendlyEvent(body, deps) {
  if (body?.event !== 'invitee.created') return { ignored: true };
  const email = String(body.payload?.email || '').trim().toLowerCase();
  const name = String(body.payload?.name || '').trim();
  if (!email) return { matched: false };

  const leads = await deps.sheet.listLeads();
  const lead = leads.find(l => String(l.email || '').trim().toLowerCase() === email);
  if (!lead) return { matched: false };

  await deps.sheet.updateLeadStatus(lead.id, 'Booked');
  const msg = davidBookedEmail({ ...lead, name: lead.name || name });
  try {
    await deps.send.sendEmail({ from: deps.fromEmail, to: deps.davidEmail, ...msg });
  } catch (e) {
    console.error(`David booked-notify failed for ${lead.id}:`, e.message);
  }
  return { matched: true, id: lead.id };
}

// Verifies the Calendly-Webhook-Signature header. Returns true/false.
export function verifyCalendlySignature(signingKey, header, rawBody) {
  if (!signingKey) return true; // no key configured → skip (dev only)
  if (!header) return false;
  const parts = Object.fromEntries(header.split(',').map(p => p.split('=')));
  const expected = createHmac('sha256', signingKey)
    .update(`${parts.t}.${rawBody}`).digest('hex');
  const got = parts.v1 || '';
  if (got.length !== expected.length) return false;
  return timingSafeEqual(Buffer.from(got), Buffer.from(expected));
}

function cleanEnv(v) { return (v || '').replace(/\\n/g, '').replace(/\n/g, '').trim(); }

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const rawBody = typeof req.body === 'string' ? req.body : JSON.stringify(req.body || {});
  const ok = verifyCalendlySignature(
    cleanEnv(process.env.CALENDLY_WEBHOOK_SIGNING_KEY),
    req.headers['calendly-webhook-signature'],
    rawBody
  );
  if (!ok) return res.status(403).json({ error: 'Invalid signature' });

  const sheetCfg = {
    url: cleanEnv(process.env.LEADS_SHEET_URL),
    token: cleanEnv(process.env.LEADS_SHEET_TOKEN),
  };
  const deps = {
    davidEmail: 'davidvd@shieldagency.com',
    fromEmail: 'Shield Insurance Leads <leads@pragmagen.xyz>',
    sheet: {
      listLeads: () => listLeads(sheetCfg),
      updateLeadStatus: (id, status) => updateLeadStatus(sheetCfg, id, status),
    },
    send: { sendEmail: (m) => sendEmail({ apiKey: cleanEnv(process.env.RESEND_API_KEY) }, m) },
  };

  try {
    const body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body;
    const result = await handleCalendlyEvent(body || {}, deps);
    return res.status(200).json({ status: 'ok', ...result });
  } catch (err) {
    console.error('calendly-webhook error:', err.message);
    return res.status(200).json({ status: 'error logged' });
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test api/calendly-webhook.test.js`
Expected: PASS — 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add api/calendly-webhook.js api/calendly-webhook.test.js
git commit -m "feat: add Calendly webhook to mark leads booked"
```

---

### Task 9: Nudge cron

**Files:**
- Create: `api/cron/lead-nudge.js`
- Modify: `vercel.json` (add cron entry)
- Test: `api/cron/lead-nudge.test.js`

`runNudge(now, deps)` finds leads with status `Contacted` whose `created_at` is older than `LEAD_NUDGE_DELAY_HOURS`, sends one nudge email, and sets status `Nudged` (so they are nudged exactly once).

- [ ] **Step 1: Write the failing test**

```js
// api/cron/lead-nudge.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { runNudge } from './lead-nudge.js';

function fakeDeps(leads) {
  const sent = [], updates = [];
  return {
    sent, updates,
    deps: {
      delayHours: 3,
      bookingUrl: 'https://calendly.com/david/quote',
      fromEmail: 'Shield <leads@pragmagen.xyz>',
      sheet: {
        listLeads: async () => leads,
        updateLeadStatus: async (id, status) => { updates.push({ id, status }); return true; },
      },
      send: { sendEmail: async (m) => { sent.push(m); return 'e1'; } },
    },
  };
}

const hoursAgo = (now, h) => new Date(now.getTime() - h * 3600e3).toISOString();

test('runNudge nudges a Contacted lead older than the delay, exactly once', async () => {
  const now = new Date('2026-05-21T12:00:00Z');
  const { deps, sent, updates } = fakeDeps([
    { id: 'a', email: 'a@x.com', name: 'Al', status: 'Contacted', created_at: hoursAgo(now, 5) },
  ]);
  const result = await runNudge(now, deps);
  assert.equal(result.nudged, 1);
  assert.equal(sent[0].to, 'a@x.com');
  assert.deepEqual(updates[0], { id: 'a', status: 'Nudged' });
});

test('runNudge skips leads that are too recent, already Nudged, or Booked', async () => {
  const now = new Date('2026-05-21T12:00:00Z');
  const { deps, sent } = fakeDeps([
    { id: 'recent', email: 'r@x.com', status: 'Contacted', created_at: hoursAgo(now, 1) },
    { id: 'done', email: 'd@x.com', status: 'Nudged', created_at: hoursAgo(now, 9) },
    { id: 'won', email: 'w@x.com', status: 'Booked', created_at: hoursAgo(now, 9) },
  ]);
  const result = await runNudge(now, deps);
  assert.equal(result.nudged, 0);
  assert.equal(sent.length, 0);
});

test('runNudge skips a Contacted lead with no email address', async () => {
  const now = new Date('2026-05-21T12:00:00Z');
  const { deps, updates } = fakeDeps([
    { id: 'noemail', email: '', status: 'Contacted', created_at: hoursAgo(now, 9) },
  ]);
  const result = await runNudge(now, deps);
  assert.equal(result.nudged, 0);
  assert.equal(updates.length, 0);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test api/cron/lead-nudge.test.js`
Expected: FAIL — `Cannot find module './lead-nudge.js'`.

- [ ] **Step 3: Write minimal implementation**

```js
// api/cron/lead-nudge.js
// Cron: send one follow-up email to leads still un-booked after LEAD_NUDGE_DELAY_HOURS.
import { listLeads, updateLeadStatus } from '../../lib/sheet.js';
import { leadNudgeEmail } from '../../lib/emails.js';
import { sendEmail } from '../../lib/send.js';
import { personalizedBookingUrl } from '../lead-intake.js';

// Testable core. deps = { delayHours, bookingUrl, fromEmail, sheet:{listLeads,updateLeadStatus}, send:{sendEmail} }.
export async function runNudge(now, deps) {
  const cutoff = now.getTime() - deps.delayHours * 3600e3;
  const leads = await deps.sheet.listLeads();
  let nudged = 0;
  for (const lead of leads) {
    if (lead.status !== 'Contacted') continue;
    if (!lead.email) continue;
    const created = Date.parse(lead.created_at || '');
    if (!Number.isFinite(created) || created > cutoff) continue;

    const bookingUrl = personalizedBookingUrl(deps.bookingUrl, lead);
    const msg = leadNudgeEmail(lead, bookingUrl);
    try {
      await deps.send.sendEmail({ from: deps.fromEmail, to: lead.email, ...msg });
      await deps.sheet.updateLeadStatus(lead.id, 'Nudged');
      nudged++;
    } catch (e) {
      console.error(`nudge failed for ${lead.id}:`, e.message);
    }
  }
  return { nudged, checked: leads.length };
}

function cleanEnv(v) { return (v || '').replace(/\\n/g, '').replace(/\n/g, '').trim(); }

export default async function handler(req, res) {
  const authHeader = req.headers.authorization || '';
  const cronSecret = cleanEnv(process.env.CRON_SECRET);
  if (cronSecret && authHeader !== `Bearer ${cronSecret}`) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  const sheetCfg = {
    url: cleanEnv(process.env.LEADS_SHEET_URL),
    token: cleanEnv(process.env.LEADS_SHEET_TOKEN),
  };
  const deps = {
    delayHours: Number(cleanEnv(process.env.LEAD_NUDGE_DELAY_HOURS)) || 3,
    bookingUrl: cleanEnv(process.env.CALENDLY_BOOKING_URL),
    fromEmail: 'Shield Insurance Leads <leads@pragmagen.xyz>',
    sheet: {
      listLeads: () => listLeads(sheetCfg),
      updateLeadStatus: (id, status) => updateLeadStatus(sheetCfg, id, status),
    },
    send: { sendEmail: (m) => sendEmail({ apiKey: cleanEnv(process.env.RESEND_API_KEY) }, m) },
  };
  try {
    const result = await runNudge(new Date(), deps);
    return res.status(200).json(result);
  } catch (err) {
    console.error('lead-nudge error:', err.message);
    return res.status(500).json({ error: err.message });
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test api/cron/lead-nudge.test.js`
Expected: PASS — 3 tests pass.

- [ ] **Step 5: Register the cron**

Modify `vercel.json` — add one entry to the `crons` array so it reads:

```json
  "crons": [
    { "path": "/api/cron/ad-schedule?action=pause", "schedule": "0 4 * * 6" },
    { "path": "/api/cron/ad-schedule?action=resume", "schedule": "0 11 * * 1" },
    { "path": "/api/cron/poll-meta-leads", "schedule": "*/5 * * * *" },
    { "path": "/api/cron/lead-nudge", "schedule": "0 * * * *" }
  ]
```

This runs the nudge check hourly; each lead is nudged at most once (status flips to `Nudged`).

- [ ] **Step 6: Run the full suite**

Run: `npm test`
Expected: PASS — every test file passes.

- [ ] **Step 7: Commit**

```bash
git add api/cron/lead-nudge.js api/cron/lead-nudge.test.js vercel.json
git commit -m "feat: add hourly lead-nudge cron"
```

---

## Manual Verification (after deploy)

These confirm the live pilot pipeline end-to-end. Not automated.

- [ ] Deploy to Vercel; confirm `CALENDLY_BOOKING_URL`, `CALENDLY_WEBHOOK_SIGNING_KEY`, `LEAD_NUDGE_DELAY_HOURS` env vars are set.
- [ ] Submit the lead form on a niche page with a real email. Confirm: (a) the lead email arrives within seconds with a working, name-prefilled Calendly link; (b) David gets the new-lead email; (c) a row appears in the Sheet with status `Contacted`.
- [ ] Book a slot via the Calendly link. Confirm the lead's Sheet status flips to `Booked` and David gets the booked email.
- [ ] Submit a lead and do NOT book. After `LEAD_NUDGE_DELAY_HOURS`, confirm one nudge email arrives and status flips to `Nudged`; confirm no second nudge on the next cron run.

---

## Self-Review

**Spec coverage** (against `2026-05-21-agent-run-insurance-lead-gen-design.md`):
- §4 wedge "instant response, book the call" → Tasks 6 (instant email + booking link), 7 (form), 9 (nudge). SMS deliberately deferred per the locked MVP scope (Twilio rejected).
- §5 component 1 (landing pages) → reused; component 4 (speed-to-lead responder) → Tasks 6–9; component 6 (reporting) → out of scope for this plan (operator reads the Sheet/admin during the pilot).
- §6 "build new: speed-to-lead responder" → delivered. Multi-tenant layer, nurture-beyond-one-nudge, client dashboard → correctly deferred (Phase 2 / not pilot-critical).
- §8 pilot week 1 "deploy the responder so conversion doesn't depend on David" → this plan is exactly that deliverable.

**Placeholder scan:** no TBD/TODO; every code step has complete code; the one HTML task references an existing file to match conventions and includes full markup.

**Type consistency:** lead shape (`id, name, email, phone, type, niche, source, created_at, status`) is consistent across `normalizeLead`, the Sheet client, email templates, and all three handlers. `personalizedBookingUrl` is defined once in `lead-intake.js` and imported by `lead-nudge.js`. Status values `New/Contacted/Nudged/Booked` are used consistently. `deps` injection shape is consistent across the three `handle*`/`run*` cores.

**Known gap (acceptable):** booking match is by email only — a lead who books with a different email than they submitted won't auto-match. Acceptable at pilot volume; David reconciles manually via the Sheet. Phone-fallback matching is a Phase 2 refinement.
