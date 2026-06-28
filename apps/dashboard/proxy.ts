import { type NextRequest, NextResponse } from "next/server";

// Content-Security-Policy with a per-request nonce. The nonce flows to Next's own inline
// scripts (Next reads the CSP from the request header) and to our no-flash theme script
// (the layout reads `x-nonce`). No 'unsafe-inline' for scripts. The dashboard talks to the
// API (connect-src) and renders Google avatars (img-src https:).
// Must match the fetch base in app/lib/api.ts exactly, or connect-src blocks the API calls.
const API_ORIGIN = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function proxy(request: NextRequest): NextResponse {
  const nonce = btoa(crypto.randomUUID());
  const csp = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https:",
    "font-src 'self' data:",
    `connect-src 'self' ${API_ORIGIN}`,
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
  ].join("; ");

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("content-security-policy", csp);

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("content-security-policy", csp);
  return response;
}

export const config = {
  // Run on document requests; skip static assets (a per-request nonce would defeat caching).
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|woff2?|txt|xml)$).*)",
  ],
};
