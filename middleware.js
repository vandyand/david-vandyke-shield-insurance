import { rewrite } from '@vercel/functions';
import { get } from '@vercel/edge-config';

const ALL_NICHES = ['landscaper', 'contractor', 'restaurant', 'home-business', 'general-indiana'];

// Map URL paths to niche slugs (when they differ)
const PATH_TO_SLUG = {
  'indiana': 'general-indiana',
};

// Default: all niches have both variants active
const DEFAULT_CONFIG = {
  'general': ['a', 'b'],
  'landscaper': ['a', 'b'],
  'contractor': ['a', 'b'],
  'restaurant': ['a', 'b'],
  'home-business': ['a', 'b'],
  'general-indiana': ['a', 'b'],
};

export default async function middleware(request) {
  const url = new URL(request.url);
  const { pathname } = url;

  // Only handle known niche paths and homepage
  // Check direct niche slug paths and aliased paths (e.g. /indiana → general-indiana)
  const pathSegment = pathname.replace(/^\/|\/$/g, '');
  let slug;

  if (pathname === '/' || pathname === '/index.html') {
    slug = 'general';
  } else if (ALL_NICHES.includes(pathSegment)) {
    slug = pathSegment;
  } else if (PATH_TO_SLUG[pathSegment]) {
    slug = PATH_TO_SLUG[pathSegment];
  } else {
    return;
  }

  // Read active variants from Edge Config (with fallback)
  let activeVariants;
  try {
    const abConfig = await get('ab_config');
    activeVariants = abConfig?.[slug] || DEFAULT_CONFIG[slug] || ['a'];
  } catch {
    activeVariants = DEFAULT_CONFIG[slug] || ['a'];
  }

  if (!activeVariants.length) activeVariants = ['a'];

  // Read existing variant cookie
  const cookies = parseCookies(request.headers.get('cookie') || '');
  const cookieName = `variant_${slug}`;
  const existingVariant = cookies[cookieName];

  // Assign variant: use existing if still active, otherwise reassign
  let variant = existingVariant;
  if (!variant || !activeVariants.includes(variant)) {
    variant = activeVariants[Math.floor(Math.random() * activeVariants.length)];
  }

  // Rewrite to correct HTML file
  if (slug === 'general') {
    url.pathname = variant === 'a' ? '/index.html' : `/general/${variant}.html`;
  } else {
    url.pathname = `/${slug}/${variant}.html`;
  }

  // Set sticky cookie (30 days)
  const maxAge = 60 * 60 * 24 * 30;
  return rewrite(url, {
    headers: {
      'Set-Cookie': `${cookieName}=${variant}; Path=/; Max-Age=${maxAge}; SameSite=Lax`,
    },
  });
}

export const config = {
  matcher: ['/', '/index.html', '/landscaper', '/landscaper/', '/contractor', '/contractor/', '/restaurant', '/restaurant/', '/home-business', '/home-business/', '/indiana', '/indiana/'],
};

function parseCookies(cookieHeader) {
  const cookies = {};
  for (const pair of cookieHeader.split(';')) {
    const [key, ...rest] = pair.trim().split('=');
    if (key) cookies[key] = rest.join('=');
  }
  return cookies;
}
