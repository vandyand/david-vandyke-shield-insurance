// Leads API — backed by Google Sheets via Apps Script web app
// GET: list all leads (Make.com writes the lead rows; status/notes overrides come from the lead_status tab)
// PATCH: update status/notes for a lead — writes to the lead_status tab via Apps Script doPost
// POST: not supported — Make.com is the only source of new leads

function cleanEnv(v) { return (v || '').replace(/\\n/g, '').replace(/\n/g, '').trim(); }
const ADMIN_PASSWORD = cleanEnv(process.env.ADMIN_PASSWORD);
const LEADS_SHEET_URL = cleanEnv(process.env.LEADS_SHEET_URL);
const LEADS_SHEET_TOKEN = cleanEnv(process.env.LEADS_SHEET_TOKEN);

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PATCH, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();

  // Auth — dashboard sends Bearer <password>, Make.com sends same
  const password = req.headers.authorization?.replace('Bearer ', '').trim();
  if (password !== ADMIN_PASSWORD) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  try {
    if (req.method === 'GET') {
      const leads = await getLeads();
      return res.status(200).json({ leads });
    }

    if (req.method === 'PATCH') {
      const { id, status, notes, _delete } = req.body || {};
      if (!id) return res.status(400).json({ error: 'id required' });
      if (_delete) {
        return res.status(400).json({ error: 'delete not supported — set status to "Closed-Lost" or similar instead' });
      }
      const update = { id };
      if (status !== undefined) update.status = status;
      if (notes !== undefined) update.notes = notes;
      const result = await postStatus(update);
      return res.status(200).json(result);
    }

    return res.status(405).json({ error: 'Method not allowed — leads come from the sheet, only PATCH (status/notes) supported' });
  } catch (err) {
    console.error('Leads API error:', err.message, err.stack);
    return res.status(500).json({ error: err.message || 'Internal error' });
  }
}

async function postStatus(update) {
  const url = `${LEADS_SHEET_URL}?token=${encodeURIComponent(LEADS_SHEET_TOKEN)}`;
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(update),
    redirect: 'follow',
  });
  // Apps Script web app POSTs return 200 even when the redirect chain swallows the body.
  // Treat HTTP 200 as success; the dashboard re-fetches via GET to verify the merged status.
  if (!r.ok) {
    throw new Error(`Sheet writeback failed: ${r.status} ${await r.text()}`);
  }
  return { success: true, id: update.id, ...update };
}

async function getLeads() {
  const url = `${LEADS_SHEET_URL}?token=${encodeURIComponent(LEADS_SHEET_TOKEN)}`;
  const r = await fetch(url, { redirect: 'follow' });
  if (!r.ok) {
    throw new Error(`Sheet read failed: ${r.status} ${await r.text()}`);
  }
  const data = await r.json();
  if (data.error) throw new Error(`Sheet error: ${data.error}`);
  return Array.isArray(data.leads) ? data.leads : [];
}
