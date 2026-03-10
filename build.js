const fs = require('fs');
const path = require('path');

const ROOT = __dirname;
const PUBLIC = path.join(ROOT, 'public');
const TEMPLATES = path.join(ROOT, 'templates');
const SECTIONS = path.join(TEMPLATES, 'sections');
const NICHES = path.join(ROOT, 'niches');

// ── 1. Clean and create output dir ──────────────────────────────────────────
if (fs.existsSync(PUBLIC)) fs.rmSync(PUBLIC, { recursive: true });
fs.mkdirSync(PUBLIC, { recursive: true });

// ── 2. Load and assemble the template ───────────────────────────────────────
let baseTemplate = fs.readFileSync(path.join(TEMPLATES, 'base.html'), 'utf8');

// Replace {{section:name}} with contents of templates/sections/name.html
baseTemplate = baseTemplate.replace(/\{\{section:([a-z0-9-]+)\}\}/g, (_, name) => {
  const sectionPath = path.join(SECTIONS, `${name}.html`);
  return fs.readFileSync(sectionPath, 'utf8');
});

// ── 3. Read niche configs ───────────────────────────────────────────────────
const nicheFiles = fs.readdirSync(NICHES).filter(f => f.endsWith('.json'));
const niches = nicheFiles.map(f => JSON.parse(fs.readFileSync(path.join(NICHES, f), 'utf8')));

// ── 4. Helpers ──────────────────────────────────────────────────────────────

// HTML-escape text content to prevent broken markup from config values
function esc(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Flatten a nested object like { hero: { headline: "..." } } to { hero_headline: "..." }
// Only flattens one level of sections, skipping arrays
function flattenConfig(obj) {
  const result = {};
  for (const [sectionKey, sectionVal] of Object.entries(obj)) {
    if (typeof sectionVal === 'object' && sectionVal !== null && !Array.isArray(sectionVal)) {
      for (const [propKey, propVal] of Object.entries(sectionVal)) {
        if (!Array.isArray(propVal)) {
          result[`${sectionKey}_${propKey}`] = propVal;
        }
      }
    } else if (!Array.isArray(sectionVal)) {
      result[sectionKey] = sectionVal;
    }
  }
  return result;
}

// Deep merge: source values override target values
function deepMerge(target, source) {
  const result = { ...target };
  for (const [key, val] of Object.entries(source)) {
    if (
      typeof val === 'object' && val !== null && !Array.isArray(val) &&
      typeof result[key] === 'object' && result[key] !== null && !Array.isArray(result[key])
    ) {
      result[key] = deepMerge(result[key], val);
    } else {
      result[key] = val;
    }
  }
  return result;
}

// Render why_choose items
function renderWhyChooseItems(items) {
  return items.map(item => `<div class="bg-white p-6 rounded-xl border border-gray-200 shadow hover:shadow-lg hover:-translate-y-1 hover:border-gold transition-all">
  <i data-lucide="${esc(item.icon)}" class="w-10 h-10 text-gold mb-4" aria-hidden="true"></i>
  <h3 class="text-navy font-semibold text-lg mb-2">${esc(item.title)}</h3>
  <p class="text-gray-600">${esc(item.desc)}</p>
</div>`).join('\n');
}

// Render services items — first 4 are always visible, rest get secondary-service class (hidden on mobile)
function renderServicesItems(items, primaryCount = 4) {
  return items.map((item, i) => {
    const extraClass = i >= primaryCount ? ' secondary-service' : '';
    return `<div class="bg-white p-6 rounded-xl border border-gray-200 shadow text-center hover:shadow-lg hover:-translate-y-1 hover:border-gold transition-all${extraClass}">
  <i data-lucide="${esc(item.icon)}" class="w-10 h-10 text-navy mx-auto mb-3" aria-hidden="true"></i>
  <h3 class="text-navy font-semibold text-lg mb-2">${esc(item.title)}</h3>
  <p class="text-gray-600 text-sm">${esc(item.desc)}</p>
</div>`;
  }).join('\n');
}

// Render FAQ items
function renderFaqItems(items) {
  return items.map(item => `<details class="bg-white border border-gray-200 rounded-xl overflow-hidden hover:border-gold transition-all group">
  <summary class="flex justify-between items-center p-4 md:p-6 cursor-pointer font-semibold text-navy text-lg hover:bg-gray-50 transition-colors">
    <span>${esc(item.q)}</span>
    <span class="ml-4 w-3 h-3 border-r-2 border-b-2 border-navy transform rotate-45 group-open:-rotate-135 transition-transform"></span>
  </summary>
  <div class="px-4 md:px-6 pb-4 md:pb-6 bg-white">
    <p class="text-gray-600">${esc(item.a)}</p>
  </div>
</details>`).join('\n');
}

// ── 5. Build pages ──────────────────────────────────────────────────────────
let pageCount = 0;

for (const niche of niches) {
  const { slug, name, defaults, variants } = niche;
  const variantKeys = Object.keys(variants);

  for (const variantId of variantKeys) {
    // Merge: defaults < variant "a" values < specific variant overrides
    let merged;
    if (variantId === 'a') {
      merged = deepMerge({}, variants.a);
    } else {
      merged = deepMerge(variants.a, variants[variantId]);
    }

    // Build placeholder map
    const placeholders = {
      ...defaults,
      ...flattenConfig(merged),
      page_title: name,
      variant_id: variantId,
      niche_slug: slug,
      image_base: '/images',
    };

    // Render dynamic array sections
    if (merged.why_choose && merged.why_choose.items) {
      placeholders.why_choose_items_html = renderWhyChooseItems(merged.why_choose.items);
    }
    if (merged.services && merged.services.items) {
      placeholders.services_items_html = renderServicesItems(merged.services.items);
      // Only show toggle button on mobile if there are more than 4 services
      if (merged.services.items.length > 4) {
        placeholders.services_toggle_html = `<!-- Toggle button (mobile only) -->
      <button id="services-toggle" class="md:hidden mx-auto mt-6 px-6 py-3 bg-gold text-navy font-semibold rounded-lg shadow hover:bg-gold-dark hover:-translate-y-0.5 hover:shadow-lg transition-all flex items-center gap-2">
        <span>View All Services</span>
        <i data-lucide="chevron-down" class="w-5 h-5 transition-transform" aria-hidden="true"></i>
      </button>`;
      } else {
        placeholders.services_toggle_html = '';
      }
    }
    if (merged.faq && merged.faq.items) {
      placeholders.faq_items_html = renderFaqItems(merged.faq.items);
    }

    // Replace all {{placeholder}} in template
    let html = baseTemplate.replace(/\{\{([a-z_]+)\}\}/g, (match, key) => {
      return placeholders[key] !== undefined ? placeholders[key] : match;
    });

    // Determine output path
    let outPath;
    if (slug === 'general' && variantId === 'a') {
      outPath = path.join(PUBLIC, 'index.html');
    } else if (slug === 'general') {
      outPath = path.join(PUBLIC, 'general', `${variantId}.html`);
    } else {
      outPath = path.join(PUBLIC, slug, `${variantId}.html`);
    }

    // Create directory and write file
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, html);
    pageCount++;

    const relOut = path.relative(ROOT, outPath);
    console.log(`Building ${slug} (variant ${variantId}) → ${relOut}`);
  }
}

// ── 6. Copy static assets ───────────────────────────────────────────────────

// Copy images/
const imgSrc = path.join(ROOT, 'images');
const imgDest = path.join(PUBLIC, 'images');
fs.mkdirSync(imgDest, { recursive: true });
for (const file of fs.readdirSync(imgSrc)) {
  fs.copyFileSync(path.join(imgSrc, file), path.join(imgDest, file));
}

// Copy CNAME
fs.copyFileSync(path.join(ROOT, 'CNAME'), path.join(PUBLIC, 'CNAME'));

// Copy admin dashboard
const adminSrc = path.join(ROOT, 'admin');
const adminDest = path.join(PUBLIC, '_admin');
if (fs.existsSync(adminSrc)) {
  fs.mkdirSync(adminDest, { recursive: true });
  for (const file of fs.readdirSync(adminSrc)) {
    fs.copyFileSync(path.join(adminSrc, file), path.join(adminDest, file));
  }
}

console.log(`\nBuild complete: ${pageCount} pages generated.`);
