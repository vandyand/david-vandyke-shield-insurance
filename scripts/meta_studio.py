#!/usr/bin/env python3
"""
Ad Creative Studio
Generates niche-targeted ad images via Ideogram, then uploads to Meta and creates ads.

COST: ~$0.04/image using V_2A_TURBO. Always confirm before generating.

Usage:
  python3 scripts/meta_studio.py generate <niche> [--count 1]   # Generate image(s) for a niche
  python3 scripts/meta_studio.py list                            # List saved creatives
  python3 scripts/meta_studio.py upload <image_file>            # Upload image to Meta
  python3 scripts/meta_studio.py create-ad <adset_id> <niche> <image_hash> # Create ad in Meta
"""

import os
import sys
import json
import time
import argparse
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────

IDEOGRAM_KEY  = os.environ.get('IDEOGRAM_API_KEY')
FB_TOKEN      = os.environ.get('FACEBOOK_BUSINESS_TOKEN')
ACCOUNT_ID    = os.environ.get('FACEBOOK_ADS_ACCOUNT_ID', '516088847542788')
PAGE_ID       = '627164777142840'
FB_API_VER    = 'v19.0'
FB_BASE       = f'https://graph.facebook.com/{FB_API_VER}'
SITE          = 'https://davidvandykeinsurance.com'

CREATIVES_DIR = Path(__file__).parent.parent / 'resources' / 'ad-creatives'
CREATIVES_DIR.mkdir(parents=True, exist_ok=True)

# Cost guard: warn if generating more than this at once
MAX_IMAGES_WITHOUT_CONFIRM = 3
COST_PER_IMAGE = 0.04  # V_2A_TURBO

# ── Niche ad prompts ──────────────────────────────────────────────────────────
# Each niche has a landing page URL and image prompt designed for Facebook ads.
# Style: clean graphic design, navy (#1a365d) and gold (#d69e2e) brand colors,
# white text, bold headline, professional icon or scene. NOT photorealistic.

NICHE_AD_SPECS = {
    'general': {
        'url': f'{SITE}/',
        'headline': 'One Agent. 50+ Carriers. Your Best Rate.',
        'body': 'Stop overpaying for insurance. I shop 50+ companies so you get the best coverage at the lowest price.',
        'prompts': [
            "Clean flat design Facebook ad for independent insurance agent. Navy blue (#1a365d) background split diagonally with light blue. Bold white text 'One Agent. 50+ Carriers. Your Best Rate.' Large white shield icon with checkmark on right side. Professional, minimal, high contrast. Square 1:1 format.",
            "Minimalist insurance ad graphic. Dark navy left half, bright gold (#d69e2e) right half. White bold text 'Stop Overpaying for Insurance.' on left. Simple white icons: house, car, umbrella arranged vertically on right. Clean sans-serif font. Square format.",
            "Bold typographic Facebook ad. Deep navy background. Large gold text '50+ Carriers.' below white text 'One Call.' Subtitle in white: 'Find your best rate today.' Bottom strip in gold. No photos, icon-only design. Square 1:1 crop.",
        ],
    },
    'landscaper': {
        'url': f'{SITE}/landscaper/',
        'headline': 'Landscaper? Get the Right Insurance.',
        'body': 'General liability, equipment coverage, and workers comp built for landscaping businesses. One call, done.',
        'prompts': [
            "Clean flat design Facebook ad targeting landscaping business owners. Dark green (#1a3d1a) and gold color scheme. Bold white text 'Protect Your Landscaping Business.' White icons of lawnmower, hedge trimmer, and shield checkmark. Professional minimal design. Square 1:1 format.",
            "Bold insurance ad for landscapers. Navy blue background. Gold accent bar on left. White headline text 'Landscaper Insurance. Done Right.' Below: small white icons of truck, equipment, workers. Clean professional look. Square format.",
            "Graphic design ad for landscaping contractor insurance. Split design: dark navy top half, bright green bottom half. White text overlay: 'One Agent. Every Coverage You Need.' Minimal flat icon of landscaping tools. No photos. Square 1:1.",
        ],
    },
    'contractor': {
        'url': f'{SITE}/contractor/',
        'headline': 'Contractor Insurance. Fast & Affordable.',
        'body': "General liability, tools & equipment, workers comp. I work with contractors every day—I know what you need.",
        'prompts': [
            "Clean flat design Facebook ad for construction contractor insurance. Dark navy background. Gold diagonal stripe. Bold white text 'Contractor Insurance. Fast & Affordable.' White flat icons: hard hat, hammer, shield. Professional minimal graphic. Square 1:1 format.",
            "Bold insurance ad targeting contractors and tradespeople. Steel blue and navy split background. White headline 'Get Your COI in 24 Hours.' Gold accent elements. Minimal icons of construction tools. No photos, graphic design only. Square format.",
            "Graphic ad for contractor liability insurance. Navy background with gold border accents. Large white text 'One Agent. Every Trade.' Below: small icons representing plumber, electrician, carpenter. Clean bold sans-serif. Square 1:1.",
        ],
    },
    'restaurant': {
        'url': f'{SITE}/restaurant/',
        'headline': 'Restaurant Insurance from $X/mo.',
        'body': "General liability, liquor liability, property. I work with Michigan restaurants every day. Let's talk.",
        'prompts': [
            "Clean flat design Facebook ad for restaurant insurance. Warm dark background (#1a1a2e navy). Gold and white color scheme. Bold white text 'Protect Your Restaurant.' White flat icons: fork and knife, shield, building. Professional minimal design. Square 1:1 format.",
            "Bold insurance ad for restaurant and bar owners. Dark navy background. Gold accent stripe. White headline 'Restaurant Insurance. One Call.' Minimal icons: plate, glass, checkmark shield. No photos, flat graphic design. Square format.",
            "Graphic ad targeting restaurant owners for insurance. Split navy and warm gold design. White bold text 'From Food to Liquor Liability — Covered.' Simple flat icons of restaurant. Clean professional. Square 1:1.",
        ],
    },
    'home-business': {
        'url': f'{SITE}/home-business/',
        'headline': 'Running a Business from Home? Get Covered.',
        'body': "Your homeowner's policy won't cover business losses. I'll find you the right protection fast.",
        'prompts': [
            "Clean flat design Facebook ad for home-based business insurance. Navy background. Gold and white accents. Bold white text 'Your Home Business Needs Real Coverage.' White flat icons: house with briefcase, shield, laptop. Professional minimal. Square 1:1 format.",
            "Bold insurance ad for home business owners. Dark navy split with light blue. White headline 'Home Business Insurance.' Gold accent elements. Minimal icons: home office, laptop, checkmark. No photos. Square format.",
            "Graphic ad targeting work-from-home business owners for insurance. Navy background, gold diagonal element. White bold text 'Don\\'t Let Your Homeowner\\'s Policy Leave You Exposed.' Simple flat icons. Clean design. Square 1:1.",
        ],
    },
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def confirm(prompt):
    resp = input(f'{prompt} [y/N]: ').strip().lower()
    return resp == 'y'

def ideogram_generate(prompt, niche, index):
    """Generate one image via Ideogram V_2A_TURBO. Returns local file path."""
    print(f'  Generating image {index} via Ideogram V_2A_TURBO (~$0.04)...')

    data = json.dumps({
        'image_request': {
            'prompt': prompt,
            'aspect_ratio': 'ASPECT_1_1',
            'model': 'V_2A_TURBO',
            'magic_prompt_option': 'OFF',  # OFF = use our prompt exactly
            'style_type': 'DESIGN',
            'num_images': 1,
        }
    }).encode()

    req = urllib.request.Request(
        'https://api.ideogram.ai/generate',
        data=data,
        headers={
            'Api-Key': IDEOGRAM_KEY,
            'Content-Type': 'application/json',
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read())
    except urllib.error.HTTPError as e:
        err = json.loads(e.read())
        print(f'  ✗ Ideogram error: {err}')
        return None

    images = resp.get('data', [])
    if not images:
        print(f'  ✗ No images returned: {resp}')
        return None

    image_url = images[0]['url']

    # Download and save
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = CREATIVES_DIR / f'{niche}_{ts}_{index}.jpg'
    urllib.request.urlretrieve(image_url, filename)
    print(f'  ✓ Saved: {filename.name}')
    return filename

def fb_upload_image(image_path):
    """Upload image to Meta ad account. Returns image hash."""
    import mimetypes
    import email.mime.multipart
    import email.mime.base
    import email.encoders

    # Use multipart form upload
    boundary = '----FormBoundary7MA4YWxkTrZu0gW'
    with open(image_path, 'rb') as f:
        image_data = f.read()

    body = (
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="access_token"\r\n\r\n'
        f'{FB_TOKEN}\r\n'
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="filename"; filename="{Path(image_path).name}"\r\n'
        f'Content-Type: image/jpeg\r\n\r\n'
    ).encode() + image_data + f'\r\n--{boundary}--\r\n'.encode()

    req = urllib.request.Request(
        f'{FB_BASE}/act_{ACCOUNT_ID}/adimages',
        data=body,
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read())
    except urllib.error.HTTPError as e:
        err = json.loads(e.read())
        print(f'  ✗ Upload error: {err}')
        return None

    images = resp.get('images', {})
    if images:
        hash_val = list(images.values())[0].get('hash')
        return hash_val
    return None

def fb_create_ad(adset_id, niche, image_hash, headline, body_text):
    """Create a paused ad in Meta with the given creative."""
    spec = NICHE_AD_SPECS[niche]
    landing_url = spec['url'] + '?utm_source=facebook&utm_medium=paid&utm_campaign=shield-insurance&utm_content=' + niche

    # Create creative
    creative_data = urllib.parse.urlencode({
        'access_token': FB_TOKEN,
        'name': f'Shield — {niche} — {datetime.now().strftime("%Y-%m-%d")}',
        'object_story_spec': json.dumps({
            'page_id': PAGE_ID,
            'link_data': {
                'link': landing_url,
                'message': body_text,
                'name': headline,
                'image_hash': image_hash,
                'call_to_action': {
                    'type': 'LEARN_MORE',
                    'value': {'link': landing_url},
                },
            },
        }),
    }).encode()

    req = urllib.request.Request(
        f'{FB_BASE}/act_{ACCOUNT_ID}/adcreatives',
        data=creative_data,
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            creative_resp = json.loads(r.read())
    except urllib.error.HTTPError as e:
        err = json.loads(e.read())
        print(f'  ✗ Creative error: {err.get("error", {}).get("message")}')
        return None

    creative_id = creative_resp.get('id')
    if not creative_id:
        print(f'  ✗ No creative ID: {creative_resp}')
        return None

    # Create ad
    ad_data = urllib.parse.urlencode({
        'access_token': FB_TOKEN,
        'name': f'Shield — {niche} — {datetime.now().strftime("%Y-%m-%d")}',
        'adset_id': adset_id,
        'creative': json.dumps({'creative_id': creative_id}),
        'status': 'PAUSED',
    }).encode()

    req = urllib.request.Request(f'{FB_BASE}/act_{ACCOUNT_ID}/ads', data=ad_data, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            ad_resp = json.loads(r.read())
    except urllib.error.HTTPError as e:
        err = json.loads(e.read())
        print(f'  ✗ Ad error: {err.get("error", {}).get("message")}')
        return None

    return ad_resp.get('id')

# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_generate(niche, count, yes=False):
    if niche not in NICHE_AD_SPECS:
        print(f'Unknown niche: {niche}. Options: {", ".join(NICHE_AD_SPECS.keys())}')
        return

    prompts = NICHE_AD_SPECS[niche]['prompts']
    count = min(count, len(prompts))  # don't exceed available prompts
    cost = count * COST_PER_IMAGE

    print(f'\nNiche: {niche}')
    print(f'Images: {count}  |  Est. cost: ${cost:.2f}')
    print()

    for i, p in enumerate(prompts[:count], 1):
        print(f'  Prompt {i}: {p[:80]}...')
    print()

    if not yes and not confirm(f'Generate {count} image(s) for ~${cost:.2f}?'):
        print('Cancelled.')
        return

    generated = []
    for i, prompt in enumerate(prompts[:count], 1):
        path = ideogram_generate(prompt, niche, i)
        if path:
            generated.append(path)
        time.sleep(1)  # brief pause between requests

    print(f'\n✓ Generated {len(generated)} image(s) in resources/ad-creatives/')
    print('Review them, then run:')
    for path in generated:
        print(f'  python3 scripts/meta_studio.py upload {path}')


def cmd_list():
    files = sorted(CREATIVES_DIR.glob('*.jpg')) + sorted(CREATIVES_DIR.glob('*.png'))
    if not files:
        print('No saved creatives in resources/ad-creatives/')
        return
    print(f'\n{len(files)} saved creatives:\n')
    for f in files:
        size_kb = f.stat().st_size // 1024
        print(f'  {f.name:<55} {size_kb:>5} KB')
    print()


def cmd_upload(image_path):
    path = Path(image_path)
    if not path.exists():
        print(f'File not found: {image_path}')
        return

    print(f'Uploading {path.name} to Meta...')
    image_hash = fb_upload_image(path)
    if image_hash:
        print(f'  ✓ Uploaded. Image hash: {image_hash}')
        print(f'  Next: python3 scripts/meta_studio.py create-ad <adset_id> <niche> {image_hash}')
    else:
        print('  ✗ Upload failed.')


def cmd_create_ad(adset_id, niche, image_hash):
    if niche not in NICHE_AD_SPECS:
        print(f'Unknown niche: {niche}')
        return

    spec = NICHE_AD_SPECS[niche]
    print(f'\nCreating ad for niche: {niche}')
    print(f'  Headline: {spec["headline"]}')
    print(f'  Body:     {spec["body"][:60]}...')
    print(f'  URL:      {spec["url"]}')
    print()

    if not confirm('Create this ad (PAUSED) in Meta?'):
        print('Cancelled.')
        return

    ad_id = fb_create_ad(adset_id, niche, image_hash, spec['headline'], spec['body'])
    if ad_id:
        print(f'  ✓ Ad created (PAUSED): {ad_id}')
        print(f'  Activate in Meta Ads Manager after reviewing.')
    else:
        print('  ✗ Failed to create ad.')

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Ad Creative Studio')
    sub = parser.add_subparsers(dest='command')

    gen = sub.add_parser('generate', help='Generate image(s) for a niche')
    gen.add_argument('niche', choices=list(NICHE_AD_SPECS.keys()))
    gen.add_argument('--count', type=int, default=1, help='Number of images (default: 1, max: 3)')
    gen.add_argument('--yes', action='store_true', help='Skip confirmation prompt')

    sub.add_parser('list', help='List saved creatives')

    up = sub.add_parser('upload', help='Upload image to Meta')
    up.add_argument('image_file', help='Path to image file')

    ca = sub.add_parser('create-ad', help='Create a Meta ad with uploaded image')
    ca.add_argument('adset_id')
    ca.add_argument('niche', choices=list(NICHE_AD_SPECS.keys()))
    ca.add_argument('image_hash')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    missing = []
    if args.command in ('generate', 'list') and not IDEOGRAM_KEY:
        missing.append('IDEOGRAM_API_KEY')
    if args.command in ('upload', 'create-ad') and not FB_TOKEN:
        missing.append('FACEBOOK_BUSINESS_TOKEN')
    if missing:
        print(f'Missing env vars: {", ".join(missing)}. Run: source ~/.bashrc')
        sys.exit(1)

    if args.command == 'generate':
        cmd_generate(args.niche, args.count, yes=args.yes)
    elif args.command == 'list':
        cmd_list()
    elif args.command == 'upload':
        cmd_upload(args.image_file)
    elif args.command == 'create-ad':
        cmd_create_ad(args.adset_id, args.niche, args.image_hash)

if __name__ == '__main__':
    main()
