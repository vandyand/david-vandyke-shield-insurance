#!/usr/bin/env python3
"""
Meta Ads Performance Report
Usage: python3 scripts/meta_report.py [--days 30] [--level campaign|adset|ad]
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

# ── Config ────────────────────────────────────────────────────────────────────

TOKEN      = os.environ.get('FACEBOOK_BUSINESS_TOKEN')
ACCOUNT_ID = os.environ.get('FACEBOOK_ADS_ACCOUNT_ID', '516088847542788')
API_VER    = 'v19.0'
BASE_URL   = f'https://graph.facebook.com/{API_VER}'

# ── Helpers ───────────────────────────────────────────────────────────────────

def api_get(path, params=None):
    params = params or {}
    params['access_token'] = TOKEN
    url = f'{BASE_URL}{path}?{urllib.parse.urlencode(params)}'
    with urllib.request.urlopen(url, timeout=15) as r:
        data = json.loads(r.read())
    if 'error' in data:
        print(f'API error: {data["error"]["message"]}', file=sys.stderr)
        sys.exit(1)
    return data

def fmt_currency(val):
    return f'${float(val):>8.2f}' if val else '      —  '

def fmt_int(val):
    return f'{int(val):>8,}' if val else '       —'

def fmt_pct(val):
    return f'{float(val):>6.2f}%' if val else '     —'

def get_action(actions, action_type):
    if not actions:
        return None
    for a in actions:
        if a['action_type'] == action_type:
            return a['value']
    return None

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Meta Ads Performance Report')
    parser.add_argument('--days', type=int, default=30, help='Number of days to look back (default: 30)')
    parser.add_argument('--level', choices=['campaign', 'adset', 'ad'], default='adset', help='Breakdown level (default: adset)')
    args = parser.parse_args()

    if not TOKEN:
        print('Error: FACEBOOK_BUSINESS_TOKEN not set. Run: source ~/.bashrc', file=sys.stderr)
        sys.exit(1)

    since = (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')
    until = datetime.now().strftime('%Y-%m-%d')

    print(f'\n{"═"*80}')
    print(f'  META ADS REPORT  |  Last {args.days} days ({since} → {until})')
    print(f'{"═"*80}\n')

    # ── Campaigns ────────────────────────────────────────────────────────────
    campaigns = api_get(f'/act_{ACCOUNT_ID}/campaigns', {
        'fields': 'id,name,status,objective,daily_budget,lifetime_budget'
    })

    print(f'CAMPAIGNS ({len(campaigns["data"])} total)')
    print(f'{"─"*80}')
    for c in campaigns['data']:
        budget = ''
        if c.get('daily_budget'):
            budget = f'  Daily: ${int(c["daily_budget"])/100:.0f}'
        elif c.get('lifetime_budget'):
            budget = f'  Lifetime: ${int(c["lifetime_budget"])/100:.0f}'
        status_icon = '🟢' if c['status'] == 'ACTIVE' else '⏸ '
        print(f'  {status_icon} {c["name"]:<40} [{c["status"]:<8}] {c["objective"]}{budget}')
    print()

    # ── Insights ─────────────────────────────────────────────────────────────
    insight_fields = [
        'campaign_name', 'adset_name', 'ad_name',
        'spend', 'impressions', 'clicks', 'cpc', 'cpm', 'ctr',
        'actions', 'cost_per_action_type',
        'reach', 'frequency',
    ]

    insights = api_get(f'/act_{ACCOUNT_ID}/insights', {
        'fields': ','.join(insight_fields),
        'time_range': json.dumps({'since': since, 'until': until}),
        'level': args.level,
        'limit': 100,
    })

    rows = insights.get('data', [])

    if not rows:
        print('  No data for this period. Campaign may still be paused or recently launched.')
        print('  Tip: Run this after the campaign has been active for at least 1 day.\n')
        return

    # ── Summary totals ───────────────────────────────────────────────────────
    total_spend      = sum(float(r.get('spend', 0)) for r in rows)
    total_impressions = sum(int(r.get('impressions', 0)) for r in rows)
    total_clicks     = sum(int(r.get('clicks', 0)) for r in rows)
    total_leads      = sum(int(get_action(r.get('actions'), 'lead') or 0) for r in rows)
    total_schedules  = sum(int(get_action(r.get('actions'), 'onsite_conversion.post_save') or 0) for r in rows)

    avg_ctr  = (total_clicks / total_impressions * 100) if total_impressions else 0
    avg_cpc  = (total_spend / total_clicks) if total_clicks else 0
    avg_cpl  = (total_spend / total_leads) if total_leads else 0

    print('SUMMARY')
    print(f'{"─"*80}')
    print(f'  Spend:        ${total_spend:,.2f}')
    print(f'  Impressions:  {total_impressions:,}')
    print(f'  Clicks:       {total_clicks:,}')
    print(f'  CTR:          {avg_ctr:.2f}%')
    print(f'  Avg CPC:      ${avg_cpc:.2f}')
    if total_leads:
        print(f'  Leads:        {total_leads:,}  (CPL: ${avg_cpl:.2f})')
    print()

    # ── Breakdown by level ───────────────────────────────────────────────────
    level_label = {'campaign': 'CAMPAIGN', 'adset': 'AD SET', 'ad': 'AD'}[args.level]
    name_field  = {'campaign': 'campaign_name', 'adset': 'adset_name', 'ad': 'ad_name'}[args.level]

    rows_sorted = sorted(rows, key=lambda r: float(r.get('spend', 0)), reverse=True)

    print(f'{level_label} BREAKDOWN')
    print(f'{"─"*80}')
    header = f'  {"Name":<35} {"Spend":>9} {"Impr":>9} {"Clicks":>7} {"CTR":>7} {"CPC":>7} {"Leads":>6}'
    print(header)
    print(f'  {"─"*35} {"─"*9} {"─"*9} {"─"*7} {"─"*7} {"─"*7} {"─"*6}')

    for r in rows_sorted:
        name     = r.get(name_field, 'Unknown')[:34]
        spend    = float(r.get('spend', 0))
        impr     = int(r.get('impressions', 0))
        clicks   = int(r.get('clicks', 0))
        ctr      = float(r.get('ctr', 0))
        cpc      = float(r.get('cpc', 0)) if r.get('cpc') else 0
        leads    = int(get_action(r.get('actions'), 'lead') or 0)

        print(f'  {name:<35} ${spend:>8.2f} {impr:>9,} {clicks:>7,} {ctr:>6.2f}% ${cpc:>6.2f} {leads:>6}')

    print(f'\n{"═"*80}\n')


if __name__ == '__main__':
    main()
