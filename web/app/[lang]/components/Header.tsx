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

export default function Header({
  dict,
  lang,
}: {
  dict: Dictionary;
  lang: string;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    document.body.style.overflow = menuOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [menuOpen]);

  const navItems = [
    { href: "#how-it-works", label: dict.nav.howItWorks },
    { href: "#why", label: dict.nav.about },
    { href: "#advertising", label: dict.nav.advertise },
    { href: "#contact", label: dict.nav.contact },
  ];

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

        {/* ── Desktop ── */}
        <div
          className="hidden md:flex"
          style={{
            maxWidth: "72rem",
            margin: "0 auto",
            padding: "0 2rem",
            height: "4rem",
            display: "flex",
            alignItems: "center",
          }}
        >
          {/* Logo */}
          <Link
            href={`/${lang}`}
            className="no-underline"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              flexShrink: 0,
              fontFamily: "var(--font-plus-jakarta), sans-serif",
            }}
          >
            <div
              style={{
                width: "2rem",
                height: "2rem",
                borderRadius: "0.5rem",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: "#0099DB",
                flexShrink: 0,
              }}
            >
              <Wifi size={16} color="white" strokeWidth={2.5} />
            </div>
            <span style={{ fontSize: "1.15rem", fontWeight: 800, letterSpacing: "-0.02em" }}>
              <span style={{ color: "#1B4F8A" }}>Abot</span>
              <span style={{ color: "#F58220" }}>Kamay</span>
            </span>
          </Link>

          {/* Nav — right after logo */}
          <nav
            style={{
              display: "flex",
              alignItems: "center",
              gap: "1.25rem",
              marginLeft: "2rem",
            }}
          >
            {navItems.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="link-underline"
                style={{
                  fontSize: "0.875rem",
                  fontWeight: 500,
                  whiteSpace: "nowrap",
                  color: "var(--color-text-secondary)",
                  textDecoration: "none",
                  transition: "color 0.2s",
                }}
                onMouseEnter={(e) => { e.currentTarget.style.color = "var(--color-text-primary)"; }}
                onMouseLeave={(e) => { e.currentTarget.style.color = "var(--color-text-secondary)"; }}
              >
                {item.label}
              </a>
            ))}
          </nav>

          {/* Spacer */}
          <div style={{ flex: 1 }} />

          {/* Right: Lang + Auth */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.75rem",
              flexShrink: 0,
            }}
          >
            {/* Language switcher */}
            <div style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
              {languages.map((l) => (
                <Link
                  key={l.code}
                  href={`/${l.code}`}
                  className="no-underline"
                  style={{
                    fontSize: "0.75rem",
                    padding: "0.375rem 0.625rem",
                    borderRadius: "9999px",
                    fontWeight: 500,
                    transition: "all 0.2s",
                    ...(lang === l.code
                      ? { background: "var(--color-brand-green)", color: "white", boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }
                      : { color: "var(--color-text-muted)" }),
                  }}
                >
                  {l.label}
                </Link>
              ))}
            </div>

            <div style={{ width: "1px", height: "1rem", background: "#e0dbd5" }} />

            {/* Login */}
            <Link
              href="/login"
              className="no-underline"
              style={{
                fontSize: "0.875rem",
                fontWeight: 500,
                whiteSpace: "nowrap",
                color: "var(--color-text-secondary)",
                textDecoration: "none",
                padding: "0 0.25rem",
                transition: "color 0.2s",
              }}
              onMouseEnter={(e) => { e.currentTarget.style.color = "var(--color-text-primary)"; }}
              onMouseLeave={(e) => { e.currentTarget.style.color = "var(--color-text-secondary)"; }}
            >
              {dict.nav.login}
            </Link>

            {/* Sign up CTA */}
            <Link
              href="/register"
              className="no-underline btn-scale"
              style={{
                fontSize: "0.875rem",
                fontWeight: 600,
                whiteSpace: "nowrap",
                color: "white",
                padding: "0.5rem 1rem",
                borderRadius: "0.75rem",
                background: "var(--color-brand-green)",
                boxShadow: "0 1px 4px rgba(27,79,138,0.2)",
                textDecoration: "none",
                transition: "all 0.2s",
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = "var(--color-brand-green-light)"; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = "var(--color-brand-green)"; }}
            >
              {dict.nav.register}
            </Link>
          </div>
        </div>

        {/* ── Mobile ── */}
        <div className="md:hidden flex items-center justify-between h-16 px-5">
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
              <span style={{ color: "#1B4F8A" }}>Abot</span>
              <span style={{ color: "#F58220" }}>Kamay</span>
            </span>
          </Link>
          <button
            onClick={() => setMenuOpen(true)}
            className="p-2 rounded-lg text-[var(--color-text-secondary)] hover:bg-[var(--color-warm-gray)] transition-colors"
            aria-label="Open menu"
          >
            <Menu size={22} />
          </button>
        </div>
      </header>

      {/* ── Mobile fullscreen menu ── */}
      {menuOpen && (
        <div className="fixed inset-0 z-[100] md:hidden animate-fade-in">
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
                  <span style={{ color: "#1B4F8A" }}>Abot</span>
                  <span style={{ color: "#F58220" }}>Kamay</span>
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

            {/* Nav links */}
            <nav className="flex flex-col items-center gap-2 flex-1 justify-center">
              {navItems.map((item) => (
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
              <div className="flex items-center gap-3">
                <Link
                  href="/login"
                  onClick={() => setMenuOpen(false)}
                  className="flex-1 text-center text-base font-semibold text-[var(--color-text-primary)] py-3 rounded-2xl border-2 border-[#e0dbd5] no-underline hover:bg-[var(--color-warm-gray)] transition-colors"
                >
                  {dict.nav.login}
                </Link>
                <Link
                  href="/register"
                  onClick={() => setMenuOpen(false)}
                  className="flex-1 text-center text-base font-semibold text-white py-3 rounded-2xl no-underline transition-all btn-scale"
                  style={{ background: "var(--color-brand-green)" }}
                >
                  {dict.nav.register}
                </Link>
              </div>

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
