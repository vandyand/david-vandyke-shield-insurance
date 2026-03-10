export default async function handler(req, res) {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();

  // Auth
  const password = req.headers.authorization?.replace('Bearer ', '');
  if (password !== process.env.ADMIN_PASSWORD) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  const edgeConfigId = process.env.EDGE_CONFIG_ID;
  const vercelToken = process.env.VERCEL_API_TOKEN;

  if (req.method === 'GET') {
    try {
      const response = await fetch(
        `https://api.vercel.com/v1/edge-config/${edgeConfigId}/items`,
        { headers: { Authorization: `Bearer ${vercelToken}` } }
      );
      const items = await response.json();
      const abConfig = items.find(item => item.key === 'ab_config');
      return res.status(200).json({ ab_config: abConfig?.value || null });
    } catch (error) {
      return res.status(500).json({ error: 'Failed to read config' });
    }
  }

  if (req.method === 'POST') {
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
            items: [{ operation: 'upsert', key: 'ab_config', value: ab_config }],
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
