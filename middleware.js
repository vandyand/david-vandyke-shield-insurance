import { NextResponse } from 'next/server';
import { get } from '@vercel/edge-config';

const ALL_NICHES = ['landscaper', 'contractor', 'restaurant', 'home-business'];
const VARIANTS = 'abcdefghij';

// Default: all niches have both variants active
const DEFAULT_CONFIG = {
  'general': ['a', 'b'],
  'landscaper': ['a', 'b'],
  'contractor': ['a', 'b'],
  'restaurant': ['a', 'b'],
  'home-business': ['a', 'b'],
};

export async function middleware(request) {
  const { pathname } = request.nextUrl;

  // Determine niche from path
  const nicheSlug = ALL_NICHES.find(n => pathname === `/${n}` || pathname === `/${n}/`);
  const isHome = pathname === '/' || pathname === '/index.html';

  if (!nicheSlug && !isHome) return NextResponse.next();

  const slug = nicheSlug || 'general';

  // Read active variants from Edge Config (with fallback)
  let activeVariants;
  try {
    const abConfig = await get('ab_config');
    activeVariants = abConfig?.[slug] || DEFAULT_CONFIG[slug] || ['a'];
  } catch {
    activeVariants = DEFAULT_CONFIG[slug] || ['a'];
  }

  // If no variants are active, serve variant 'a' as fallback
  if (!activeVariants.length) activeVariants = ['a'];

  const cookieName = `variant_${slug}`;
  const existingVariant = request.cookies.get(cookieName)?.value;

  // Assign variant: use existing if still active, otherwise reassign
  let variant = existingVariant;
  if (!variant || !activeVariants.includes(variant)) {
    variant = activeVariants[Math.floor(Math.random() * activeVariants.length)];
  }

  // Rewrite to correct HTML file
  let target;
  if (slug === 'general') {
    target = variant === 'a' ? '/index.html' : `/general/${variant}.html`;
  } else {
    target = `/${slug}/${variant}.html`;
  }

  const url = request.nextUrl.clone();
  url.pathname = target;
  const response = NextResponse.rewrite(url);

  // Set sticky cookie (30 days)
  response.cookies.set(cookieName, variant, {
    maxAge: 60 * 60 * 24 * 30,
    path: '/',
    sameSite: 'lax',
  });

  return response;
}

export const config = {
  matcher: ['/', '/index.html', '/landscaper', '/landscaper/', '/contractor', '/contractor/', '/restaurant', '/restaurant/', '/home-business', '/home-business/'],
};
