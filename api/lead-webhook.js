// Meta Lead Ads webhook — receives new lead notifications and emails David
// GET: webhook verification handshake with Meta
// POST: new lead submitted, fetch details, send email

const VERIFY_TOKEN = (process.env.LEAD_WEBHOOK_VERIFY_TOKEN || 'shield_lead_verify_2026').trim();
const PAGE_TOKEN = process.env.FACEBOOK_PAGE_TOKEN;
const RESEND_API_KEY = process.env.RESEND_API_KEY;
const NOTIFY_EMAIL = 'davidvd@shieldagency.com';
const FROM_EMAIL = 'Shield Insurance Leads <leads@davidvandykeinsurance.com>';

export default async function handler(req, res) {
  // ── Webhook verification (Meta sends GET when you register the webhook) ───
  if (req.method === 'GET') {
    const mode = req.query['hub.mode'];
    const token = req.query['hub.verify_token'];
    const challenge = req.query['hub.challenge'];

    if (mode === 'subscribe' && token === VERIFY_TOKEN) {
      console.log('Webhook verified');
      return res.status(200).send(challenge);
    }
    return res.status(403).json({ error: 'Verification failed' });
  }

  // ── New lead notification (Meta sends POST) ───────────────────────────────
  if (req.method === 'POST') {
    try {
      const body = req.body;

      // Meta sends an array of entry objects
      const entries = body?.entry || [];
      for (const entry of entries) {
        for (const change of entry.changes || []) {
          if (change.field !== 'leadgen') continue;

          const leadId = change.value?.leadgen_id;
          const formId = change.value?.form_id;
          const pageId = change.value?.page_id;

          if (!leadId) continue;

          // Fetch lead field data from Meta
          const leadData = await fetchLeadData(leadId);
          await sendEmail(leadData, leadId, formId);
        }
      }

      return res.status(200).json({ status: 'ok' });
    } catch (err) {
      console.error('Webhook error:', err);
      // Always return 200 to Meta so it doesn't retry indefinitely
      return res.status(200).json({ status: 'error logged' });
    }
  }

  return res.status(405).json({ error: 'Method not allowed' });
}

async function fetchLeadData(leadId) {
  const url = `https://graph.facebook.com/v19.0/${leadId}?fields=field_data,created_time&access_token=${PAGE_TOKEN}`;
  const r = await fetch(url);
  const data = await r.json();

  // field_data is an array of { name, values } objects
  const fields = {};
  for (const f of data.field_data || []) {
    fields[f.name] = f.values?.[0] || '';
  }
  fields.created_time = data.created_time;
  return fields;
}

async function sendEmail(fields, leadId, formId) {
  const name = fields.full_name || 'Unknown';
  const phone = fields.phone_number || 'Not provided';
  const insuranceType = fields.insurance_type || 'Not specified';
  const time = fields.created_time
    ? new Date(fields.created_time).toLocaleString('en-US', { timeZone: 'America/Detroit' })
    : 'Just now';

  const html = `
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 24px;">
      <div style="background: #1a365d; color: white; padding: 20px 24px; border-radius: 8px 8px 0 0;">
        <h1 style="margin: 0; font-size: 20px;">🎯 New Lead — Shield Insurance</h1>
        <p style="margin: 4px 0 0; opacity: 0.8; font-size: 14px;">${time} (Michigan time)</p>
      </div>
      <div style="border: 1px solid #e2e8f0; border-top: none; padding: 24px; border-radius: 0 0 8px 8px;">
        <table style="width: 100%; border-collapse: collapse;">
          <tr>
            <td style="padding: 10px 0; color: #718096; width: 160px; font-size: 14px;">Name</td>
            <td style="padding: 10px 0; font-weight: 600; color: #1a202c; font-size: 16px;">${name}</td>
          </tr>
          <tr style="border-top: 1px solid #f7fafc;">
            <td style="padding: 10px 0; color: #718096; font-size: 14px;">Phone</td>
            <td style="padding: 10px 0; font-weight: 600; color: #1a202c; font-size: 16px;">
              <a href="tel:${phone}" style="color: #2c5282; text-decoration: none;">${phone}</a>
            </td>
          </tr>
          <tr style="border-top: 1px solid #f7fafc;">
            <td style="padding: 10px 0; color: #718096; font-size: 14px;">Looking for</td>
            <td style="padding: 10px 0; font-weight: 600; color: #1a202c; font-size: 16px;">${insuranceType}</td>
          </tr>
        </table>
        <div style="margin-top: 24px; padding: 16px; background: #fffbeb; border: 1px solid #f6e05e; border-radius: 6px;">
          <p style="margin: 0; color: #744210; font-size: 14px;">
            ⏱ <strong>Call within the hour</strong> — lead conversion drops sharply after 60 minutes.
          </p>
        </div>
        <p style="margin-top: 16px; font-size: 12px; color: #a0aec0;">Lead ID: ${leadId} · Form ID: ${formId}</p>
      </div>
    </div>
  `;

  const r = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${RESEND_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      from: FROM_EMAIL,
      to: [NOTIFY_EMAIL],
      subject: `New lead: ${name} — ${insuranceType} insurance`,
      html,
    }),
  });

  const result = await r.json();
  if (!r.ok) {
    throw new Error(`Resend error: ${JSON.stringify(result)}`);
  }
  console.log('Email sent:', result.id);
}
