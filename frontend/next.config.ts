import type { NextConfig } from 'next';

const previousBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
const defaultOrigin = process.env.VERCEL ? 'https://examind.duckdns.org' : 'http://localhost:8000';
const apiOrigin = new URL(
  process.env.EXAMIND_API_ORIGIN || (previousBaseUrl?.startsWith('http') ? previousBaseUrl : defaultOrigin),
).origin;

const config: NextConfig = {
  async rewrites() {
    return [{ source: '/api/v1/:path*', destination: `${apiOrigin}/api/v1/:path*` }];
  },
};

export default config;
