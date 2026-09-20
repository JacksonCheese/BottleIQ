import type { NextConfig } from "next";
const config: NextConfig = {
  async rewrites() { return [{ source: "/api/:path*", destination: `${process.env.API_URL || "http://127.0.0.1:8000"}/:path*` }]; },
  async headers() { return [{ source: "/(.*)", headers: [{ key: "X-Frame-Options", value: "DENY" }, { key: "X-Content-Type-Options", value: "nosniff" }, { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" }] }]; }
};
export default config;
