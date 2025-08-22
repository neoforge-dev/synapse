import { withAuth } from "next-auth/middleware"
import { NextResponse } from "next/server"

export default withAuth(
  function middleware(req) {
    // If user is not authenticated and trying to access protected routes
    if (!req.nextauth.token && req.nextUrl.pathname.startsWith("/dashboard")) {
      return NextResponse.redirect(new URL("/login", req.url))
    }

    // If user is authenticated and trying to access auth pages, redirect to dashboard
    if (req.nextauth.token && (req.nextUrl.pathname === "/login" || req.nextUrl.pathname === "/register")) {
      return NextResponse.redirect(new URL("/dashboard", req.url))
    }

    return NextResponse.next()
  },
  {
    callbacks: {
      authorized: () => true, // Let the middleware function handle the logic
    },
  }
)

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/login",
    "/register",
  ]
}