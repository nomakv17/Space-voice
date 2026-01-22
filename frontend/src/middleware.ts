import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Domain-based routing middleware for SpaceVoice
 *
 * Routes:
 * - spacevoice.ai / www.spacevoice.ai → Landing page (/)
 * - dashboard.spacevoice.ai → Dashboard (/dashboard)
 *
 * This allows a single Next.js deployment to serve both the marketing
 * landing page and the authenticated dashboard on different domains.
 */
export function middleware(request: NextRequest) {
  const hostname = request.headers.get("host") ?? "";
  const pathname = request.nextUrl.pathname;

  // Main domain (spacevoice.ai) - redirect dashboard routes to subdomain
  if (hostname === "spacevoice.ai" || hostname === "www.spacevoice.ai") {
    if (pathname.startsWith("/dashboard")) {
      return NextResponse.redirect(
        new URL(`https://dashboard.spacevoice.ai${pathname}`, request.url)
      );
    }
    // Also redirect /login and /onboarding to dashboard subdomain
    if (pathname === "/login" || pathname.startsWith("/onboarding")) {
      return NextResponse.redirect(
        new URL(`https://dashboard.spacevoice.ai${pathname}`, request.url)
      );
    }
  }

  // Dashboard subdomain - redirect root to /dashboard
  if (hostname === "dashboard.spacevoice.ai" && pathname === "/") {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  // Match all paths except static files and API routes
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|audio|widget).*)"],
};
