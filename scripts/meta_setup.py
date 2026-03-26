#!/usr/bin/env python3
"""
Meta Ads Campaign Setup & Management
Configures campaigns, ad sets, and ads for Shield Insurance niche landing pages.

Usage:
  python3 scripts/meta_setup.py status            # Show current state
  python3 scripts/meta_setup.py fix-adset         # Fix existing ad set (optimization goal + geo)
  python3 scripts/meta_setup.py create-adsets     # Create niche ad sets (landscaper, contractor, etc.)
  python3 scripts/meta_setup.py create-ad <adset_id> <niche>  # Create a link ad for a niche
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.parse

# ── Config ────────────────────────────────────────────────────────────────────

TOKEN      = os.environ.get('FACEBOOK_BUSINESS_TOKEN')
ACCOUNT_ID = os.environ.get('FACEBOOK_ADS_ACCOUNT_ID', '516088847542788')
PAGE_ID    = '627164777142840'
CAMPAIGN_ID = '120239927519070511'
API_VER    = 'v19.0'
BASE_URL   = f'https://graph.facebook.com/{API_VER}'
SITE       = 'https://davidvandykeinsurance.com'

# Michigan statewide geo targeting
MICHIGAN_GEO = {
    'regions': [{'key': '3865', 'name': 'Michigan', 'country': 'US'}],
    'location_types': ['home', 'recent'],
}

# Niche configurations: landing page slug + interest targeting
NICHES = {
    'general': {
        'url': f'{SITE}/',
        'name': 'General — Michigan Residents',
        'interests': [
            {'id': '6003138184776', 'name': 'Home insurance'},
            {'id': '6003283735711', 'name': 'Life insurance'},
        ],
    },
    'landscaper': {
        'url': f'{SITE}/landscaper/',
        'name': 'Landscapers & Lawn Care',
        'interests': [
            {'id': '6003409387424', 'name': 'Landscaping'},
            {'id': '6003397425735', 'name': 'Lawn care'},
        ],
    },
    'contractor': {
        'url': f'{SITE}/contractor/',
        'name': 'Contractors & Tradespeople',
        'interests': [
            {'id': '6003228602763', 'name': 'General contractor'},
            {'id': '6003395720887', 'name': 'Construction'},
        ],
    },
    'restaurant': {
        'url': f'{SITE}/restaurant/',
        'name': 'Restaurants & Food Service',
        'interests': [
            {'id': '6003384407595', 'name': 'Restaurant'},
            {'id': '6003139187855', 'name': 'Food service'},
        ],
    },
    'home-business': {
        'url': f'{SITE}/home-business/',
        'name': 'Home-Based Businesses',
        'interests': [
            {'id': '6003264791844', 'name': 'Home business'},
            {'id': '6003139617720', 'name': 'Small business'},
        ],
    },
}

def utm_url(base_url, campaign, adset):
    params = urllib.parse.urlencode({
        'utm_source': 'facebook',
        'utm_medium': 'paid',
        'utm_campaign': campaign,
        'utm_content': adset,
    })
    sep = '&' if '?' in base_url else '?'
    return f'{base_url}{sep}{params}'

# ── API helpers ───────────────────────────────────────────────────────────────

def api_get(path, params=None):
    params = params or {}
    params['access_token'] = TOKEN
    url = f'{BASE_URL}{path}?{urllib.parse.urlencode(params)}'
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read())

def api_post(path, data):
    data['access_token'] = TOKEN
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(f'{BASE_URL}{path}', data=body, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())

def api_update(object_id, data):
    data['access_token'] = TOKEN
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(f'{BASE_URL}/{object_id}', data=body, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())

def check_error(resp, action):
    if 'error' in resp:
        print(f'  ✗ {action} failed: {resp["error"]["message"]}')
        return True
    return False

# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_status():
    print(f'\n{"═"*70}')
    print('  CAMPAIGN STATUS')
    print(f'{"═"*70}\n')

    campaign = api_get(f'/{CAMPAIGN_ID}', {
        'fields': 'id,name,status,objective,special_ad_categories,daily_budget'
    })
    print(f'Campaign: {campaign["name"]}')
    print(f'  Status:    {campaign["status"]}')
    print(f'  Objective: {campaign["objective"]}')
    print(f'  Special Ad Categories: {campaign.get("special_ad_categories", [])}')
    print()

    adsets = api_get(f'/{CAMPAIGN_ID}/adsets', {
        'fields': 'id,name,status,optimization_goal,daily_budget,targeting'
    })
    print(f'Ad Sets ({len(adsets["data"])}):')
    for a in adsets['data']:
        budget = f'${int(a["daily_budget"])/100:.0f}/day' if a.get('daily_budget') else 'no budget'
        print(f'  [{a["status"]:<8}] {a["name"]:<40} {budget}')
        print(f'             Optimization: {a["optimization_goal"]}')
        geo = a.get('targeting', {}).get('geo_locations', {})
        if geo.get('regions'):
            print(f'             Geo: {", ".join(r["name"] for r in geo["regions"])}')
        elif geo.get('cities'):
            print(f'             Geo: {", ".join(c["name"] for c in geo["cities"])} (cities)')
    print()

    ads = api_get(f'/{CAMPAIGN_ID}/ads', {'fields': 'id,name,status'})
    print(f'Ads ({len(ads["data"])}):')
    for ad in ads['data']:
        print(f'  [{ad["status"]:<8}] {ad["name"]}  (id: {ad["id"]})')
    print()


def cmd_fix_adset():
    """Update existing ad set: expand geo to Michigan statewide.
    Note: optimization_goal cannot be changed on existing ad sets —
    use create-adsets to create properly configured niche ad sets instead.
    """
    adsets = api_get(f'/{CAMPAIGN_ID}/adsets', {'fields': 'id,name,targeting'})
    if not adsets['data']:
        print('No ad sets found.')
        return

    adset = adsets['data'][0]
    print(f'Updating ad set: {adset["name"]} ({adset["id"]})')

    # Preserve existing targeting, just update geo
    existing = adset.get('targeting', {})
    targeting = {
        **existing,
        **MICHIGAN_GEO,
        'targeting_automation': {'advantage_audience': 1},
        'brand_safety_content_filter_levels': ['FACEBOOK_RELAXED', 'AN_RELAXED'],
    }
    # Remove city-level geo since we're going statewide
    targeting.pop('cities', None)

    resp = api_update(adset['id'], {'targeting': json.dumps(targeting)})

    if check_error(resp, 'Update ad set geo'):
        return
    print(f'  ✓ Geo updated → Michigan statewide')
    print(f'  ℹ  To change optimization_goal, use: python3 scripts/meta_setup.py create-adsets')


def cmd_create_campaign():
    """Create a fresh campaign with correct settings, then create all niche ad sets."""
    print('\nCreating new Shield Insurance campaign...\n')

    resp = api_post(f'/act_{ACCOUNT_ID}/campaigns', {
        'name': 'Shield Insurance — Niche Landing Pages',
        'objective': 'OUTCOME_LEADS',
        'status': 'PAUSED',
        'special_ad_categories': json.dumps(['FINANCIAL_PRODUCTS_SERVICES']),
        'is_adset_budget_sharing_enabled': 'false',
    })
    if check_error(resp, 'Create campaign'):
        return

    campaign_id = resp['id']
    print(f'  ✓ Campaign created (id: {campaign_id})')
    print(f'    Name: Shield Insurance — Niche Landing Pages\n')

    # Create all niche ad sets under this new campaign
    print('Creating niche ad sets...\n')
    for slug, niche in NICHES.items():
        targeting = {
            **MICHIGAN_GEO,
            'brand_safety_content_filter_levels': ['FACEBOOK_RELAXED', 'AN_RELAXED'],
        }

        data = {
            'campaign_id': campaign_id,
            'name': f'Shield — {niche["name"]}',
            'status': 'PAUSED',
            'optimization_goal': 'LEAD_GENERATION',
            'billing_event': 'IMPRESSIONS',
            'daily_budget': 2500,  # $25/day in cents
            'targeting': json.dumps(targeting),
            'destination_type': 'WEBSITE',
        }

        r = api_post(f'/act_{ACCOUNT_ID}/adsets', data)
        if check_error(r, f'Create ad set for {slug}'):
            continue
        adset_id = r['id']
        print(f'  ✓ {niche["name"]:<35} adset id: {adset_id}')
        print(f'    Run: python3 scripts/meta_setup.py create-ad {adset_id} {slug}')

    print(f'\n  ℹ  Campaign is PAUSED. Activate in Meta Ads Manager after adding ad copy.')
    print(f'  ℹ  Old campaign (id: {CAMPAIGN_ID}) left paused — delete manually if no longer needed.\n')


def cmd_create_adsets():
    """Create one ad set per niche under the main campaign."""
    print(f'\nCreating niche ad sets under campaign {CAMPAIGN_ID}...\n')

    for slug, niche in NICHES.items():
        # Note: Advantage+ audience targeting NOT allowed under Special Ad Category
        # (Financial Products & Services). Use standard geo + broad targeting only.
        targeting = {
            **MICHIGAN_GEO,
            'brand_safety_content_filter_levels': ['FACEBOOK_RELAXED', 'AN_RELAXED'],
        }

        data = {
            'campaign_id': CAMPAIGN_ID,
            'name': f'Shield — {niche["name"]}',
            'status': 'PAUSED',
            'optimization_goal': 'LEAD_GENERATION',
            'billing_event': 'IMPRESSIONS',
            'daily_budget': 2500,  # $25/day in cents
            'targeting': json.dumps(targeting),
            'destination_type': 'WEBSITE',
        }

        resp = api_post(f'/act_{ACCOUNT_ID}/adsets', data)
        if check_error(resp, f'Create ad set for {slug}'):
            continue
        adset_id = resp['id']
        print(f'  ✓ Created ad set: {niche["name"]} (id: {adset_id})')
        print(f'    Next: python3 scripts/meta_setup.py create-ad {adset_id} {slug}')
    print()


def cmd_create_ad(adset_id, niche_slug):
    """Create a link ad pointing to the niche landing page with UTM params."""
    if niche_slug not in NICHES:
        print(f'Unknown niche: {niche_slug}. Options: {", ".join(NICHES.keys())}')
        return

    niche = NICHES[niche_slug]
    landing_url = utm_url(niche['url'], 'shield-insurance', niche_slug)

    print(f'Creating ad for niche: {niche_slug}')
    print(f'  Landing URL: {landing_url}')

    # Create the creative
    creative_data = {
        'name': f'Shield Insurance — {niche["name"]}',
        'object_story_spec': json.dumps({
            'page_id': PAGE_ID,
            'link_data': {
                'link': landing_url,
                'message': '{{AD_BODY}}',  # placeholder — update in Ads Manager
                'name': '{{AD_HEADLINE}}',  # placeholder — update in Ads Manager
                'call_to_action': {
                    'type': 'LEARN_MORE',
                    'value': {'link': landing_url},
                },
            },
        }),
    }

    creative_resp = api_post(f'/act_{ACCOUNT_ID}/adcreatives', creative_data)
    if check_error(creative_resp, 'Create creative'):
        return
    creative_id = creative_resp['id']
    print(f'  ✓ Created creative (id: {creative_id})')

    # Create the ad
    ad_data = {
        'name': f'Shield — {niche["name"]}',
        'adset_id': adset_id,
        'creative': json.dumps({'creative_id': creative_id}),
        'status': 'PAUSED',
    }

    ad_resp = api_post(f'/act_{ACCOUNT_ID}/ads', ad_data)
    if check_error(ad_resp, 'Create ad'):
        return
    print(f'  ✓ Created ad (id: {ad_resp["id"]})')
    print(f'  ⚠  Update ad copy (headline + body) in Meta Ads Manager before activating')


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if not TOKEN:
        print('Error: FACEBOOK_BUSINESS_TOKEN not set. Run: source ~/.bashrc')
        sys.exit(1)

    parser = argparse.ArgumentParser(description='Meta Ads Campaign Setup')
    subparsers = parser.add_subparsers(dest='command')

    subparsers.add_parser('status', help='Show current campaign state')
    subparsers.add_parser('fix-adset', help='Fix existing ad set geo (deprecated — use create-campaign)')
    subparsers.add_parser('create-campaign', help='Create fresh campaign + all niche ad sets')
    subparsers.add_parser('create-adsets', help='Create niche ad sets under existing campaign')

    create_ad = subparsers.add_parser('create-ad', help='Create a link ad for a niche')
    create_ad.add_argument('adset_id', help='Ad set ID')
    create_ad.add_argument('niche', help='Niche slug', choices=NICHES.keys())

    args = parser.parse_args()

    if args.command == 'status':
        cmd_status()
    elif args.command == 'fix-adset':
        cmd_fix_adset()
    elif args.command == 'create-campaign':
        cmd_create_campaign()
    elif args.command == 'create-adsets':
        cmd_create_adsets()
    elif args.command == 'create-ad':
        cmd_create_ad(args.adset_id, args.niche)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
