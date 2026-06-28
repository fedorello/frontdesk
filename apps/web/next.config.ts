import type { NextConfig } from "next";

// Baseline security headers on every response. (A Content-Security-Policy is intentionally
// left out for now — the inline no-flash theme script in the layout would need a per-request
// nonce or hash; tracked as a follow-up rather than shipping `unsafe-inline`.)
const securityHeaders = [
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
  { key: "X-Frame-Options", value: "DENY" }, // clickjacking: never frame the app
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
];

const nextConfig: NextConfig = {
  // Emit a self-contained server bundle for a small production Docker image.
  output: "standalone",
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
