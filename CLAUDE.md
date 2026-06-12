# David VanDyke Shield Insurance — davidvandykeinsurance.com

Marketing site + client intake form for David VanDyke's insurance agency,
hosted on Vercel. Static pages are generated at build time; a few serverless
functions handle form submissions and lead tracking.

## How deploys work

- **Push to `main` → auto-deploys to production.** No manual deploy step.
- **Open a PR → Vercel posts a preview URL** on the PR. Check your change
  there before merging.
- Never run `vercel --prod` manually; the git integration handles it.

## Architecture

```
templates/base.html          page shell (head, scripts, sticky CTA)
templates/sections/*.html    header, hero, services, faq, contact, etc.
niches/*.json                per-niche content/variants (general.json = homepage)
build.cjs                    assembles templates + niches → public/
templates/intake.html        /intake — client intake form (standalone page)
templates/dashboard.html     /dashboard — ad/lead dashboard (password-protected)
api/                         serverless functions (intake submit, lead pipeline, crons)
```

Build locally: `npm run build`, then preview with `npx serve public`.
The `public/` directory is generated — never edit it directly.

## Editing the intake form (most common task)

The live form is **`templates/intake.html`** — edit that file directly.
(`docs/Client_Intake_Form.html` is a historical reference copy only; changes
there do nothing.)

The form is plain HTML/CSS/vanilla JS, no framework. Questions live in the
`QUESTIONS` array; conditional questions use `when: (a) => ...` predicates
with the `isAuto()` / `isHome()` / `isRenters()` helpers. The summary email
is assembled in `buildSummary()` — if you add questions, add matching lines
there so answers reach the email.

File uploads go browser → Vercel Blob (`/api/intake-upload-token`), then the
submit endpoint (`/api/intake-submit`) emails everything to David and appends
a row to the Google Sheet.

## Guardrails

- **Do not modify `api/`, `vercel.json`, `middleware.js`, or
  `templates/dashboard.html` without checking with Andrew first.** These are
  wired into the lead pipeline, ad-schedule crons, and dashboard auth — a
  breaking change there fails silently (leads stop arriving).
- **Never commit secrets.** No `.env*` files, API keys, or tokens in the
  repo. All credentials live in Vercel environment variables.
- The `/quote` URL 307-redirects to `/intake` (vercel.json) — keep it.
- Marketing pages use Tailwind via CDN with custom `navy`/`gold` colors
  (see `templates/base.html`); the intake page uses its own plain CSS.
  Match the existing style of whichever file you're editing.

## Verifying changes

After `npm run build`, the built form is at `public/intake/index.html`.
For form-logic changes, sanity-check in the browser: pick each policy type
and confirm the right question sections appear, then check the review screen
summary includes your new fields.
