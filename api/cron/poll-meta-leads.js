// Poll Meta lead forms every 5 min, dedupe against the sheet, append + email new leads.
// Replaces Make.com as the integration glue between Meta lead forms and the Google Sheet + email notifications.

function cleanEnv(v) { return (v || '').replace(/\\n/g, '').replace(/\n/g, '').trim(); }

const PAGE_TOKEN = cleanEnv(process.env.FACEBOOK_PAGE_TOKEN);
const RESEND_API_KEY = cleanEnv(process.env.RESEND_API_KEY);
const LEADS_SHEET_URL = cleanEnv(process.env.LEADS_SHEET_URL);
const LEADS_SHEET_TOKEN = cleanEnv(process.env.LEADS_SHEET_TOKEN);
const CRON_SECRET = cleanEnv(process.env.CRON_SECRET);
const NOTIFY_EMAIL = 'davidvd@shieldagency.com';
const FROM_EMAIL = 'Shield Insurance Leads <leads@davidvandykeinsurance.com>';

// Hardcoded list of lead form IDs to poll. Add new ones here when creating new lead-gen ads.
const FORM_IDS = [
  '970463065969282',   // MI v1 form (older Meta lead-form variant)
  '1249998820149207',  // MI v2 form (newer with email field)
  '1310970837800532',  // IN form
];

export default async function handler(req, res) {
  const authHeader = req.headers.authorization || '';
  if (CRON_SECRET && authHeader !== `Bearer ${CRON_SECRET}`) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  try {
    // 1. Snapshot existing sheet lead IDs so we don't double-process
    const existingIds = await fetchExistingLeadIds();

    // 2. Pull recent leads from each form
    const candidates = [];
    for (const formId of FORM_IDS) {
      try {
        const formLeads = await fetchFormLeads(formId);
        for (const raw of formLeads) {
          if (!existingIds.has(raw.id)) candidates.push({ raw, formId });
        }
      } catch (e) {
        console.error(`fetchFormLeads ${formId} failed:`, e.message);
      }
    }

    // 3. For each new lead: enrich with ad/adset/campaign context, append, email
    const results = [];
    for (const { raw, formId } of candidates) {
      try {
        const enriched = await enrichLead(raw, formId);
        await appendLeadToSheet(enriched);
        await sendLeadEmail(enriched);
        results.push({ id: raw.id, name: enriched.name, ok: true });
      } catch (e) {
        console.error(`process lead ${raw.id} failed:`, e.message);
        results.push({ id: raw.id, ok: false, err: e.message });
      }
    }

    return res.status(200).json({
      checked_forms: FORM_IDS.length,
      new_leads: candidates.length,
      processed: results.filter(r => r.ok).length,
      results,
    });
  } catch (e) {
    console.error('poll-meta-leads error:', e);
    return res.status(500).json({ error: e.message || String(e) });
  }
}

async function fetchExistingLeadIds() {
  const url = `${LEADS_SHEET_URL}?token=${encodeURIComponent(LEADS_SHEET_TOKEN)}`;
  const r = await fetch(url, { redirect: 'follow' });
  if (!r.ok) throw new Error(`sheet read failed: ${r.status}`);
  const data = await r.json();
  if (data.error) throw new Error(`sheet error: ${data.error}`);
  return new Set((data.leads || []).map(l => String(l.id)));
}

async function fetchFormLeads(formId) {
  // Pull the most recent 50 leads. At a 5-min poll interval that's plenty of headroom.
  const url = `https://graph.facebook.com/v19.0/${formId}/leads?fields=id,created_time,field_data,ad_id&limit=50&access_token=${PAGE_TOKEN}`;
  const r = await fetch(url);
  const data = await r.json();
  if (data.error) throw new Error(`Meta /leads ${formId}: ${data.error.message}`);
  return data.data || [];
}

async function enrichLead(raw, formId) {
  // field_data is an array of { name, values: [string] }
  const fields = {};
  for (const f of raw.field_data || []) {
    fields[f.name] = f.values?.[0] || '';
  }

  // Look up ad/adset/campaign names so the dashboard's State + Campaign columns work
  let adName = '', adsetId = '', adsetName = '', campaignId = '', campaignName = '';
  if (raw.ad_id) {
    try {
      const adUrl = `https://graph.facebook.com/v19.0/${raw.ad_id}?fields=name,adset{id,name},campaign{id,name}&access_token=${PAGE_TOKEN}`;
      const r = await fetch(adUrl);
      const d = await r.json();
      if (!d.error) {
        adName = d.name || '';
        adsetId = d.adset?.id || '';
        adsetName = d.adset?.name || '';
        campaignId = d.campaign?.id || '';
        campaignName = d.campaign?.name || '';
      }
    } catch (e) {
      console.warn(`ad enrichment for ${raw.ad_id} failed:`, e.message);
    }
  }

  return {
    id: raw.id,
    name: fields.full_name || '',
    phone: fields.phone_number || '',
    email: fields.email || '',
    type: fields.insurance_type || '',
    created_at: raw.created_time || '',
    form_id: formId,
    ad_id: raw.ad_id || '',
    ad_name: adName,
    adset_id: adsetId,
    adset_name: adsetName,
    campaign_id: campaignId,
    campaign_name: campaignName,
  };
}

async function appendLeadToSheet(lead) {
  const url = `${LEADS_SHEET_URL}?token=${encodeURIComponent(LEADS_SHEET_TOKEN)}`;
  const body = { mode: 'append', ...lead };
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    redirect: 'manual',
  });
  // Apps Script always 302-redirects after doPost runs successfully. The redirect target
  // serves a 405 page (no auth context), which is misleading — the original POST already
  // executed our handler. So treat 302 (or any 2xx) as success.
  if (r.status !== 302 && !r.ok) {
    throw new Error(`sheet append failed: ${r.status}`);
  }
  return true;
}

async function sendLeadEmail(lead) {
  if (!RESEND_API_KEY) return;
  const time = lead.created_at
    ? new Date(lead.created_at).toLocaleString('en-US', { timeZone: 'America/Detroit' })
    : 'Just now';
  const state = /Indiana/i.test([lead.campaign_name, lead.adset_name, lead.ad_name].join(' ')) ? 'Indiana' : 'Michigan';
  const insType = lead.type || 'Not specified';

  const html = `
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 24px;">
      <div style="background: #1a365d; color: white; padding: 20px 24px; border-radius: 8px 8px 0 0;">
        <h1 style="margin: 0; font-size: 20px;">🎯 New Lead — Shield Insurance</h1>
        <p style="margin: 4px 0 0; opacity: 0.8; font-size: 14px;">${escHtml(time)} (${state})</p>
      </div>
      <div style="border: 1px solid #e2e8f0; border-top: none; padding: 24px; border-radius: 0 0 8px 8px;">
        <table style="width: 100%; border-collapse: collapse;">
          <tr>
            <td style="padding: 10px 0; color: #718096; width: 160px; font-size: 14px;">Name</td>
            <td style="padding: 10px 0; font-weight: 600; color: #1a202c; font-size: 16px;">${escHtml(lead.name || 'Unknown')}</td>
          </tr>
          <tr style="border-top: 1px solid #f7fafc;">
            <td style="padding: 10px 0; color: #718096; font-size: 14px;">Phone</td>
            <td style="padding: 10px 0; font-weight: 600; color: #1a202c; font-size: 16px;">
              <a href="tel:${escAttr(lead.phone || '')}" style="color: #2c5282; text-decoration: none;">${escHtml(lead.phone || 'Not provided')}</a>
            </td>
          </tr>
          ${lead.email ? `<tr style="border-top: 1px solid #f7fafc;">
            <td style="padding: 10px 0; color: #718096; font-size: 14px;">Email</td>
            <td style="padding: 10px 0; color: #1a202c; font-size: 16px;">
              <a href="mailto:${escAttr(lead.email)}" style="color: #2c5282; text-decoration: none;">${escHtml(lead.email)}</a>
            </td>
          </tr>` : ''}
          <tr style="border-top: 1px solid #f7fafc;">
            <td style="padding: 10px 0; color: #718096; font-size: 14px;">Looking for</td>
            <td style="padding: 10px 0; font-weight: 600; color: #1a202c; font-size: 16px;">${escHtml(insType)}</td>
          </tr>
          ${lead.campaign_name ? `<tr style="border-top: 1px solid #f7fafc;">
            <td style="padding: 10px 0; color: #718096; font-size: 14px;">Campaign</td>
            <td style="padding: 10px 0; color: #1a202c; font-size: 14px;">${escHtml(lead.campaign_name)}</td>
          </tr>` : ''}
        </table>
        <div style="margin-top: 24px; padding: 16px; background: #fffbeb; border: 1px solid #f6e05e; border-radius: 6px;">
          <p style="margin: 0; color: #744210; font-size: 14px;">
            ⏱ <strong>Call within the hour</strong> — lead conversion drops sharply after 60 minutes.
          </p>
        </div>
        <p style="margin-top: 16px; font-size: 12px; color: #a0aec0;">Lead ID: ${escHtml(lead.id)}</p>
      </div>
    </div>
  `;

  const r = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${RESEND_API_KEY}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      from: FROM_EMAIL,
      to: [NOTIFY_EMAIL],
      subject: `New ${state} lead: ${lead.name || 'Unknown'} — ${insType}`,
      html,
    }),
  });
  if (!r.ok) throw new Error(`Resend send failed: ${r.status} ${await r.text()}`);
}

function escHtml(s) {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
function escAttr(s) { return escHtml(s); }
