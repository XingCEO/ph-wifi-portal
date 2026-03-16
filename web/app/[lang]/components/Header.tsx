"use client";

import { useState } from "react";
import Link from "next/link";
import { Menu, X } from "lucide-react";
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

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-[var(--color-warm-white)]/72 backdrop-blur-xl saturate-[1.8] border-b border-white/30">
      <div className="max-w-6xl mx-auto px-5 sm:px-8 flex items-center justify-between h-16">
        <Link
          href={`/${lang}`}
          className="font-[var(--font-display)] text-xl font-800 tracking-tight text-[var(--color-text-primary)] no-underline"
          style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
        >
          Abot<span className="text-[var(--color-brand-green)]">Kamay</span>
        </Link>

        <nav className="hidden md:flex items-center gap-8">
          <a
            href="#how-it-works"
            className="text-sm font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors no-underline"
          >
            {dict.nav.howItWorks}
          </a>
          <a
            href="#why"
            className="text-sm font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors no-underline"
          >
            {dict.nav.about}
          </a>
          <a
            href="#advertising"
            className="text-sm font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors no-underline"
          >
            {dict.nav.advertise}
          </a>
          <a
            href="#contact"
            className="text-sm font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors no-underline"
          >
            {dict.nav.contact}
          </a>

          <div className="flex items-center gap-1 ml-4 border-l border-[#e8e4de] pl-4">
            {languages.map((l) => (
              <Link
                key={l.code}
                href={`/${l.code}`}
                className={`text-xs px-2.5 py-1.5 rounded-md transition-colors no-underline ${
                  lang === l.code
                    ? "bg-[var(--color-brand-green)] text-white font-semibold"
                    : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-warm-gray)]"
                }`}
              >
                {l.label}
              </Link>
            ))}
          </div>
        </nav>

        <button
          onClick={() => setMenuOpen(!menuOpen)}
          className="md:hidden p-2 text-[var(--color-text-secondary)]"
          aria-label="Toggle menu"
        >
          {menuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {/* Mobile menu backdrop + panel */}
      {menuOpen && (
        <>
          <div
            className="fixed inset-0 top-16 bg-black/40 backdrop-blur-md z-40 md:hidden"
            onClick={() => setMenuOpen(false)}
          />
          <div className="fixed top-16 left-0 right-0 z-50 md:hidden bg-white/72 backdrop-blur-xl saturate-[1.8] border-t border-white/30 px-5 py-6 shadow-2xl rounded-b-2xl mx-2">
            <nav className="flex flex-col gap-4">
              <a
                href="#how-it-works"
                onClick={() => setMenuOpen(false)}
                className="text-base font-medium text-[var(--color-text-secondary)] no-underline"
              >
                {dict.nav.howItWorks}
              </a>
              <a
                href="#why"
                onClick={() => setMenuOpen(false)}
                className="text-base font-medium text-[var(--color-text-secondary)] no-underline"
              >
                {dict.nav.about}
              </a>
              <a
                href="#advertising"
                onClick={() => setMenuOpen(false)}
                className="text-base font-medium text-[var(--color-text-secondary)] no-underline"
              >
                {dict.nav.advertise}
              </a>
              <a
                href="#contact"
                onClick={() => setMenuOpen(false)}
                className="text-base font-medium text-[var(--color-text-secondary)] no-underline"
              >
                {dict.nav.contact}
              </a>
              <div className="flex items-center gap-2 pt-4 border-t border-[#e8e4de]">
                {languages.map((l) => (
                  <Link
                    key={l.code}
                    href={`/${l.code}`}
                    className={`text-sm px-3 py-1.5 rounded-md no-underline ${
                      lang === l.code
                        ? "bg-[var(--color-brand-green)] text-white font-semibold"
                        : "text-[var(--color-text-muted)] bg-[var(--color-warm-gray)]"
                    }`}
                  >
                    {l.label}
                  </Link>
                ))}
              </div>
            </nav>
          </div>
        </>
      )}
    </header>
  );
}
