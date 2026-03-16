import { NextRequest, NextResponse } from "next/server";

const locales = ["en", "fil", "zh-hant"];
const defaultLocale = "en";

const skipPrefixes = [
  "/_next",
  "/api",
  "/portal",
  "/admin",
  "/health",
  "/static",
  "/thanks",
  "/metrics",
  "/favicon.ico",
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (skipPrefixes.some((prefix) => pathname.startsWith(prefix))) {
    return NextResponse.next();
  }

  const pathnameHasLocale = locales.some(
    (locale) => pathname.startsWith(`/${locale}/`) || pathname === `/${locale}`
  );

  if (pathnameHasLocale) {
    return NextResponse.next();
  }

  // Detect preferred locale from Accept-Language
  const acceptLanguage = request.headers.get("accept-language") || "";
  let detectedLocale = defaultLocale;

  if (/zh/i.test(acceptLanguage)) {
    detectedLocale = "zh-hant";
  } else if (/fil|tl/i.test(acceptLanguage)) {
    detectedLocale = "fil";
  }

  const url = request.nextUrl.clone();
  url.pathname = `/${detectedLocale}${pathname}`;
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/((?!_next|api|portal|admin|health|static|thanks|metrics|favicon.ico).*)"],
};
