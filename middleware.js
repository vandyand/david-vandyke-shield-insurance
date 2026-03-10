import { NextResponse } from 'next/server';

const NICHES = {
  'landscaper': 2,
  'contractor': 2,
  'restaurant': 2,
  'home-business': 2,
};
const VARIANTS = 'abcdefghij';

export function middleware(request) {
  const { pathname } = request.nextUrl;

  // Determine niche from path
  const nicheSlug = Object.keys(NICHES).find(n => pathname === `/${n}` || pathname === `/${n}/`);
  const isHome = pathname === '/' || pathname === '/index.html';

  if (!nicheSlug && !isHome) return NextResponse.next();

  const slug = nicheSlug || 'general';
  const cookieName = `variant_${slug}`;
  const existingVariant = request.cookies.get(cookieName)?.value;
  const count = NICHES[nicheSlug] || 2;

  // Assign variant if none exists or invalid
  let variant = existingVariant;
  if (!variant || VARIANTS.indexOf(variant) === -1 || VARIANTS.indexOf(variant) >= count) {
    variant = VARIANTS[Math.floor(Math.random() * count)];
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
