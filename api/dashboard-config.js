export default async function handler(req, res) {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();

  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Auth — expects Bearer <password>
  function cleanEnv(v) { return (v || '').replace(/\\n/g, '').trim(); }
  const password = req.headers.authorization?.replace('Bearer ', '').trim();
  if (password !== cleanEnv(process.env.ADMIN_PASSWORD)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  return res.status(200).json({
    token: process.env.FACEBOOK_BUSINESS_TOKEN,
    accountId: '516088847542788',
  });
}
