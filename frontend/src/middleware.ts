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
  const rawHostname = request.headers.get("host") ?? "";
  const hostname = rawHostname.split(":")[0].toLowerCase().trim(); // Normalize: remove port, lowercase
  const pathname = request.nextUrl.pathname;

  // Main domain (spacevoice.ai) - serve landing page, redirect dashboard routes
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
    // Serve landing page - add debug headers
    const response = NextResponse.next();
    response.headers.set("x-debug-hostname", rawHostname);
    response.headers.set("x-debug-matched", "main-domain");
    return response;
  }

  // Dashboard subdomain - redirect root to /dashboard
  if (hostname === "dashboard.spacevoice.ai") {
    if (pathname === "/") {
      return NextResponse.redirect(new URL("/dashboard", request.url));
    }
    // Continue to dashboard pages - add debug headers
    const response = NextResponse.next();
    response.headers.set("x-debug-hostname", rawHostname);
    response.headers.set("x-debug-matched", "dashboard-subdomain");
    return response;
  }

  // Unknown domain (localhost, preview URLs, etc.) - add debug headers
  const response = NextResponse.next();
  response.headers.set("x-debug-hostname", rawHostname);
  response.headers.set("x-debug-matched", "no-match-fallthrough");
  return response;
}

export const config = {
  // Match all paths except static files and API routes
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|audio|widget).*)"],
};
