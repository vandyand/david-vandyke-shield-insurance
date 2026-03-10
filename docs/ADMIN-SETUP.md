# Admin Dashboard Setup

The admin dashboard at `/_admin` requires these Vercel environment variables to be configured before it will work. The landing pages work without these — only the dashboard and live variant toggling need them.

## Step 1: Create Edge Config Store

1. Go to **Vercel Dashboard → your project → Storage → Create Database**
2. Select **Edge Config** → name it `ab-config` → **Create**
3. Vercel automatically creates the `EDGE_CONFIG` environment variable and connects it to your project

## Step 2: Get the Edge Config ID

1. In the Edge Config store page, find the **ID** (starts with `ecfg_`)
2. Add it as an environment variable in your project settings:
   - Key: `EDGE_CONFIG_ID`
   - Value: `ecfg_xxxxxxxxxxxx`

## Step 3: Create a Vercel API Token

1. Go to [vercel.com/account/tokens](https://vercel.com/account/tokens)
2. Create a new token (you can scope it to this project)
3. Add it as an environment variable:
   - Key: `VERCEL_API_TOKEN`
   - Value: the token you just created

## Step 4: Set the Admin Password

Add an environment variable:
- Key: `ADMIN_PASSWORD`
- Value: a strong password of your choosing

## Step 5: Initialize Edge Config Data

1. In the Edge Config store page, click **Add Item**
2. Key: `ab_config`
3. Value (paste this JSON):

```json
{"general":["a","b"],"landscaper":["a","b"],"contractor":["a","b"],"restaurant":["a","b"],"home-business":["a","b"]}
```

This sets all variants as active initially. You can then toggle them from the dashboard.

## Step 6: Redeploy

After setting all environment variables, trigger a redeployment so they take effect.

## Using the Dashboard

1. Visit `davidvandykeinsurance.com/_admin`
2. Enter your admin password
3. Toggle variants on/off for each niche
4. Click **Save Changes** — changes go live within ~10 seconds
5. Use the **Preview** links to see each variant directly

## Environment Variables Summary

| Variable | Purpose |
|----------|---------|
| `EDGE_CONFIG` | Auto-created — SDK connection string for reading Edge Config |
| `EDGE_CONFIG_ID` | Edge Config store ID for REST API writes |
| `VERCEL_API_TOKEN` | Vercel API token for REST API authentication |
| `ADMIN_PASSWORD` | Password for the admin dashboard |
