// Weekend ad pause cron — pauses a known set of adsets Friday night, resumes them Monday morning.
// Called by Vercel Cron per vercel.json schedule.
// No external storage dependency — the adset list is hardcoded below.

function cleanEnv(v) { return (v || '').replace(/\\n/g, '').replace(/\n/g, '').trim(); }

const FB_TOKEN = cleanEnv(process.env.FACEBOOK_BUSINESS_TOKEN);
const CRON_SECRET = cleanEnv(process.env.CRON_SECRET);

// Adsets managed by the weekend pause schedule.
// To add/remove: edit this list. Names are for readability only.
const MANAGED_ADSETS = [
  // 2026-05-22: all Facebook ad spend cut. List emptied so the weekend resume cron
  // is a no-op and won't resurrect any adset. When ads resume, re-add the adset IDs
  // here (see git history for prior entries).
];

export default async function handler(req, res) {
  const authHeader = req.headers.authorization || '';
  if (CRON_SECRET && authHeader !== `Bearer ${CRON_SECRET}`) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  const action = (req.query.action || '').toLowerCase();
  if (action !== 'pause' && action !== 'resume') {
    return res.status(400).json({ error: 'action must be pause or resume' });
  }

  const targetStatus = action === 'pause' ? 'PAUSED' : 'ACTIVE';
  const results = [];
  for (const adset of MANAGED_ADSETS) {
    try {
      await updateAdset(adset.id, targetStatus);
      results.push({ id: adset.id, name: adset.name, ok: true });
    } catch (e) {
      results.push({ id: adset.id, name: adset.name, ok: false, err: String(e.message || e) });
    }
  }

  return res.status(200).json({ action, count: MANAGED_ADSETS.length, results });
}

async function updateAdset(id, status) {
  const body = new URLSearchParams({ status, access_token: FB_TOKEN });
  const r = await fetch(`https://graph.facebook.com/v19.0/${id}`, { method: 'POST', body });
  const data = await r.json();
  if (data.error) throw new Error(data.error.message);
  return data;
}
