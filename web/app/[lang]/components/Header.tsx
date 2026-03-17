"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Menu, X, Wifi } from "lucide-react";
import type { Dictionary } from "../dictionaries";

const languages = [
  { code: "en", label: "EN" },
  { code: "fil", label: "FIL" },
  { code: "zh-hant", label: "中文" },
];

function getAuthLabels(lang: string) {
  if (lang === "zh-hant") return { login: "登入", register: "免費註冊" };
  if (lang === "fil") return { login: "Mag-login", register: "Mag-sign up" };
  return { login: "Log In", register: "Sign Up Free" };
}

export default function Header({
  dict,
  lang,
}: {
  dict: Dictionary;
  lang: string;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const authLabels = getAuthLabels(lang);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Prevent body scroll when mobile menu is open
  useEffect(() => {
    if (menuOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => { document.body.style.overflow = ""; };
  }, [menuOpen]);

  return (
    <>
      <header
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrolled
            ? "bg-white/92 backdrop-blur-2xl shadow-sm"
            : "bg-white/80 backdrop-blur-2xl"
        }`}
        style={{
          borderBottom: scrolled
            ? "1px solid rgba(0,0,0,0.08)"
            : "1px solid transparent",
          backgroundImage: !scrolled
            ? "linear-gradient(to bottom, rgba(255,255,255,0.9), rgba(250,248,245,0.8))"
            : undefined,
        }}
      >
        {/* Gradient border bottom line */}
        <div
          className="absolute bottom-0 left-0 right-0 h-px"
          style={{
            background:
              "linear-gradient(90deg, transparent, rgba(27,79,138,0.15) 30%, rgba(27,79,138,0.25) 50%, rgba(27,79,138,0.15) 70%, transparent)",
          }}
        />

        <div className="max-w-6xl mx-auto px-5 sm:px-8 flex items-center h-16 relative">
          {/* Logo — left */}
          <Link
            href={`/${lang}`}
            className="flex items-center gap-2 no-underline flex-shrink-0"
            style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
          >
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
              style={{ background: "#0099DB" }}
            >
              <Wifi size={16} color="white" strokeWidth={2.5} />
            </div>
            <span className="text-[1.15rem] font-extrabold tracking-tight">
              <span style={{ color: "#1B4F8A" }}>Abot</span><span style={{ color: "#F58220" }}>Kamay</span>
            </span>
          </Link>

          {/* Nav — center (desktop) */}
          <nav className="hidden md:flex items-center gap-7 absolute left-1/2 -translate-x-1/2">
            {[
              { href: "#how-it-works", label: dict.nav.howItWorks },
              { href: "#why", label: dict.nav.about },
              { href: "#advertising", label: dict.nav.advertise },
              { href: "#contact", label: dict.nav.contact },
            ].map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="text-sm font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors no-underline link-underline"
              >
                {item.label}
              </a>
            ))}
          </nav>

          {/* Right side — desktop */}
          <div className="hidden md:flex items-center gap-3 ml-auto">
            {/* Language switcher */}
            <div className="flex items-center gap-1 mr-1">
              {languages.map((l) => (
                <Link
                  key={l.code}
                  href={`/${l.code}`}
                  className={`text-xs px-2.5 py-1.5 rounded-full font-medium transition-all no-underline ${
                    lang === l.code
                      ? "text-white shadow-sm"
                      : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-warm-gray)]"
                  }`}
                  style={
                    lang === l.code
                      ? { background: "var(--color-brand-green)" }
                      : {}
                  }
                >
                  {l.label}
                </Link>
              ))}
            </div>

            <div className="w-px h-4 bg-[#e0dbd5]" />

            {/* Login */}
            <Link
              href="/login"
              className="text-sm font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors no-underline px-1"
            >
              {authLabels.login}
            </Link>

            {/* Sign up CTA */}
            <Link
              href="/register"
              className="text-sm font-semibold text-white px-4 py-2 rounded-xl no-underline btn-scale transition-all hover:shadow-md"
              style={{
                background: "var(--color-brand-green)",
                boxShadow: "0 1px 4px rgba(27,79,138,0.2)",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLAnchorElement).style.background =
                  "var(--color-brand-green-light)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLAnchorElement).style.background =
                  "var(--color-brand-green)";
              }}
            >
              {authLabels.register}
            </Link>
          </div>

          {/* Hamburger — mobile */}
          <button
            onClick={() => setMenuOpen(true)}
            className="md:hidden ml-auto p-2 rounded-lg text-[var(--color-text-secondary)] hover:bg-[var(--color-warm-gray)] transition-colors"
            aria-label="Open menu"
          >
            <Menu size={22} />
          </button>
        </div>
      </header>

      {/* Mobile fullscreen menu */}
      {menuOpen && (
        <div className="fixed inset-0 z-[100] md:hidden animate-fade-in">
          {/* Solid background overlay */}
          <div
            className="absolute inset-0"
            style={{ background: "var(--color-warm-white)" }}
          />

          <div className="relative flex flex-col h-full px-6 pt-6 pb-10">
            {/* Top row: logo + close */}
            <div className="flex items-center justify-between mb-10">
              <Link
                href={`/${lang}`}
                onClick={() => setMenuOpen(false)}
                className="flex items-center gap-2 no-underline"
                style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
              >
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center"
                  style={{ background: "#0099DB" }}
                >
                  <Wifi size={16} color="white" strokeWidth={2.5} />
                </div>
                <span className="text-[1.15rem] font-extrabold tracking-tight">
                  <span style={{ color: "#1B4F8A" }}>Abot</span><span style={{ color: "#F58220" }}>Kamay</span>
                </span>
              </Link>
              <button
                onClick={() => setMenuOpen(false)}
                className="p-2 rounded-lg text-[var(--color-text-secondary)] hover:bg-[var(--color-warm-gray)] transition-colors"
                aria-label="Close menu"
              >
                <X size={24} />
              </button>
            </div>

            {/* Nav links — large, centered */}
            <nav className="flex flex-col items-center gap-2 flex-1 justify-center">
              {[
                { href: "#how-it-works", label: dict.nav.howItWorks },
                { href: "#why", label: dict.nav.about },
                { href: "#advertising", label: dict.nav.advertise },
                { href: "#contact", label: dict.nav.contact },
              ].map((item) => (
                <a
                  key={item.href}
                  href={item.href}
                  onClick={() => setMenuOpen(false)}
                  className="text-3xl font-bold text-[var(--color-text-primary)] no-underline py-3 transition-colors hover:text-[var(--color-brand-green)]"
                  style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
                >
                  {item.label}
                </a>
              ))}
            </nav>

            {/* Bottom section */}
            <div className="flex flex-col gap-4 mt-auto">
              {/* Auth buttons */}
              <div className="flex items-center gap-3">
                <Link
                  href="/login"
                  onClick={() => setMenuOpen(false)}
                  className="flex-1 text-center text-base font-semibold text-[var(--color-text-primary)] py-3 rounded-2xl border-2 border-[#e0dbd5] no-underline hover:bg-[var(--color-warm-gray)] transition-colors"
                >
                  {authLabels.login}
                </Link>
                <Link
                  href="/register"
                  onClick={() => setMenuOpen(false)}
                  className="flex-1 text-center text-base font-semibold text-white py-3 rounded-2xl no-underline transition-all btn-scale"
                  style={{ background: "var(--color-brand-green)" }}
                >
                  {authLabels.register}
                </Link>
              </div>

              {/* Language switcher */}
              <div className="flex items-center justify-center gap-2 pt-4 border-t border-[#e8e4de]">
                {languages.map((l) => (
                  <Link
                    key={l.code}
                    href={`/${l.code}`}
                    onClick={() => setMenuOpen(false)}
                    className={`text-sm px-4 py-2 rounded-full font-medium no-underline transition-all ${
                      lang === l.code
                        ? "text-white"
                        : "text-[var(--color-text-muted)] bg-[var(--color-warm-gray)] hover:text-[var(--color-text-primary)]"
                    }`}
                    style={
                      lang === l.code
                        ? { background: "var(--color-brand-green)" }
                        : {}
                    }
                  >
                    {l.label}
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
