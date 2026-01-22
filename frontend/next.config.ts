import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "cdn.simpleicons.org",
      },
    ],
  },
  async rewrites() {
    return [
      // API proxy
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/:path*`,
      },
      // Clean URLs: /pricing -> /dashboard/pricing (for dashboard.spacevoice.ai)
      {
        source: "/pricing",
        destination: "/dashboard/pricing",
      },
      {
        source: "/agents",
        destination: "/dashboard/agents",
      },
      {
        source: "/agents/:path*",
        destination: "/dashboard/agents/:path*",
      },
      {
        source: "/calls",
        destination: "/dashboard/calls",
      },
      {
        source: "/crm",
        destination: "/dashboard/crm",
      },
      {
        source: "/settings",
        destination: "/dashboard/settings",
      },
      {
        source: "/workspaces",
        destination: "/dashboard/workspaces",
      },
      {
        source: "/integrations",
        destination: "/dashboard/integrations",
      },
    ];
  },
};

export default nextConfig;
