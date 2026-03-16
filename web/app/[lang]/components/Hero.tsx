"use client";

import { Wifi, ArrowRight } from "lucide-react";
import AnimateIn from "./AnimateIn";
import ScrollIndicator from "./ScrollIndicator";
import type { Dictionary } from "../dictionaries";

function WifiIllustration() {
  return (
    <svg
      viewBox="0 0 400 380"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="w-full max-w-[380px] mx-auto"
    >
      {/* Background circle */}
      <circle cx="200" cy="190" r="140" fill="#2d6a4f" fillOpacity="0.02" stroke="#2d6a4f" strokeWidth="1" strokeOpacity="0.05" strokeDasharray="6 6" />
      <circle cx="200" cy="190" r="100" fill="#2d6a4f" fillOpacity="0.02" stroke="#2d6a4f" strokeWidth="0.8" strokeOpacity="0.04" strokeDasharray="4 4" />

      {/* Phone body */}
      <rect x="155" y="110" width="90" height="160" rx="14" fill="white" stroke="#2d6a4f" strokeWidth="1.8" strokeOpacity="0.18" />
      <rect x="162" y="124" width="76" height="130" rx="3" fill="#2d6a4f" fillOpacity="0.03" />

      {/* Screen content */}
      <rect x="172" y="138" width="56" height="6" rx="3" fill="#2d6a4f" fillOpacity="0.12" />
      <rect x="172" y="150" width="40" height="4" rx="2" fill="#2d6a4f" fillOpacity="0.06" />
      <rect x="172" y="158" width="48" height="4" rx="2" fill="#2d6a4f" fillOpacity="0.06" />

      {/* Play button on screen */}
      <circle cx="200" cy="190" r="16" fill="#2d6a4f" fillOpacity="0.06" stroke="#2d6a4f" strokeWidth="1.2" strokeOpacity="0.15" />
      <polygon points="196,182 196,198 208,190" fill="#2d6a4f" fillOpacity="0.2" />

      {/* Progress bar */}
      <rect x="172" y="218" width="56" height="3" rx="1.5" fill="#2d6a4f" fillOpacity="0.06" />
      <rect x="172" y="218" width="36" height="3" rx="1.5" fill="#e9a319" fillOpacity="0.4" />

      {/* Connect button */}
      <rect x="178" y="230" width="44" height="14" rx="7" fill="#2d6a4f" fillOpacity="0.08" />

      {/* WiFi waves */}
      <path d="M182 98 Q200 78 218 98" stroke="#2d6a4f" strokeWidth="2.5" strokeOpacity="0.3" fill="none" strokeLinecap="round" />
      <path d="M168 82 Q200 56 232 82" stroke="#2d6a4f" strokeWidth="2" strokeOpacity="0.18" fill="none" strokeLinecap="round" />
      <path d="M155 68 Q200 36 245 68" stroke="#2d6a4f" strokeWidth="1.5" strokeOpacity="0.1" fill="none" strokeLinecap="round" />

      {/* Person left - student */}
      <circle cx="72" cy="170" r="10" fill="#e9a319" fillOpacity="0.12" stroke="#e9a319" strokeWidth="1" strokeOpacity="0.2" />
      <rect x="64" y="184" width="16" height="20" rx="4" fill="#e9a319" fillOpacity="0.08" />
      <rect x="60" y="208" width="10" height="3" rx="1.5" fill="#2d6a4f" fillOpacity="0.06" />

      {/* Person right - parent */}
      <circle cx="328" cy="170" r="10" fill="#2d6a4f" fillOpacity="0.1" stroke="#2d6a4f" strokeWidth="1" strokeOpacity="0.15" />
      <rect x="320" y="184" width="16" height="20" rx="4" fill="#2d6a4f" fillOpacity="0.06" />
      <rect x="330" y="208" width="10" height="3" rx="1.5" fill="#2d6a4f" fillOpacity="0.06" />

      {/* Store bottom */}
      <rect x="170" y="310" width="60" height="35" rx="3" fill="#2d6a4f" fillOpacity="0.03" stroke="#2d6a4f" strokeWidth="1" strokeOpacity="0.08" />
      <path d="M165 310 L200 295 L235 310" stroke="#2d6a4f" strokeWidth="1" strokeOpacity="0.1" fill="#2d6a4f" fillOpacity="0.02" />
      <rect x="188" y="322" width="24" height="23" rx="1" fill="#2d6a4f" fillOpacity="0.04" />

      {/* Connection lines */}
      <line x1="82" y1="178" x2="155" y2="185" stroke="#2d6a4f" strokeWidth="1" strokeOpacity="0.06" strokeDasharray="5 5" />
      <line x1="318" y1="178" x2="245" y2="185" stroke="#2d6a4f" strokeWidth="1" strokeOpacity="0.06" strokeDasharray="5 5" />
      <line x1="200" y1="270" x2="200" y2="295" stroke="#2d6a4f" strokeWidth="1" strokeOpacity="0.06" strokeDasharray="5 5" />

      {/* Floating particles */}
      <circle cx="110" cy="130" r="2.5" fill="#e9a319" fillOpacity="0.2" />
      <circle cx="290" cy="130" r="2.5" fill="#e9a319" fillOpacity="0.2" />
      <circle cx="130" cy="260" r="2" fill="#2d6a4f" fillOpacity="0.08" />
      <circle cx="270" cy="260" r="2" fill="#2d6a4f" fillOpacity="0.08" />
      <circle cx="100" cy="220" r="1.5" fill="#e9a319" fillOpacity="0.12" />
      <circle cx="300" cy="220" r="1.5" fill="#e9a319" fillOpacity="0.12" />
    </svg>
  );
}

export default function Hero({ dict }: { dict: Dictionary }) {
  return (
    <section className="relative min-h-screen flex items-center pt-16 overflow-hidden">
      {/* Background pattern */}
      <div className="absolute inset-0 opacity-[0.025]">
        <svg width="100%" height="100%">
          <defs>
            <pattern id="hero-dots" width="32" height="32" patternUnits="userSpaceOnUse">
              <circle cx="1" cy="1" r="0.8" fill="currentColor" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#hero-dots)" />
        </svg>
      </div>

      {/* Gradient accents */}
      <div className="absolute top-20 left-0 w-[500px] h-[500px] bg-gradient-to-br from-[var(--color-brand-green)]/[0.04] to-transparent rounded-full blur-3xl" />
      <div className="absolute bottom-20 right-0 w-[400px] h-[400px] bg-gradient-to-tl from-[var(--color-brand-gold)]/[0.04] to-transparent rounded-full blur-3xl" />

      <div className="relative max-w-6xl mx-auto px-5 sm:px-8 w-full">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-6 items-center">
          {/* Left - Text */}
          <div>
            <AnimateIn delay={0.05}>
              <div className="inline-flex items-center gap-2 px-4 py-2 mb-8 rounded-full bg-[var(--color-brand-green)]/8 border border-[var(--color-brand-green)]/12">
                <div className="w-1.5 h-1.5 rounded-full bg-[var(--color-brand-green)] animate-pulse" />
                <span className="text-sm font-semibold text-[var(--color-brand-green)] tracking-wide">
                  AbotKamay WiFi
                </span>
              </div>
            </AnimateIn>

            <AnimateIn delay={0.15}>
              <h1
                className="text-[2.75rem] sm:text-5xl lg:text-[3.5rem] font-800 tracking-[-0.03em] leading-[1.1] mb-7"
                style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
              >
                {dict.hero.title}{" "}
                <span className="bg-gradient-to-r from-[var(--color-brand-green)] to-[var(--color-brand-green-light)] bg-clip-text text-transparent">
                  {dict.hero.titleHighlight}
                </span>
              </h1>
            </AnimateIn>

            <AnimateIn delay={0.3}>
              <p className="text-lg sm:text-xl text-[var(--color-text-secondary)] max-w-lg leading-[1.7] mb-4">
                {dict.hero.description}
              </p>
            </AnimateIn>

            <AnimateIn delay={0.4}>
              <p className="text-base text-[var(--color-text-muted)] max-w-md leading-relaxed mb-10">
                {dict.hero.mission}
              </p>
            </AnimateIn>

            <AnimateIn delay={0.5}>
              <div className="flex items-center gap-4">
                <a
                  href="#contact"
                  className="inline-flex items-center gap-2.5 px-7 py-3.5 bg-[var(--color-brand-green)] text-white font-semibold rounded-xl hover:bg-[var(--color-brand-green-light)] transition-all hover:shadow-lg hover:shadow-[var(--color-brand-green)]/20 text-base no-underline group"
                >
                  {dict.hero.cta}
                  <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                </a>
                <a
                  href="#how-it-works"
                  className="inline-flex items-center gap-2 px-5 py-3.5 text-[var(--color-text-secondary)] font-medium rounded-xl hover:bg-[var(--color-warm-gray)] transition-colors text-base no-underline"
                >
                  <Wifi size={16} />
                  {dict.nav.howItWorks}
                </a>
              </div>
            </AnimateIn>
          </div>

          {/* Right - Illustration */}
          <AnimateIn delay={0.25} direction="right" duration={0.8}>
            <div className="hidden lg:block">
              <WifiIllustration />
            </div>
          </AnimateIn>
        </div>
      </div>

      <ScrollIndicator />
    </section>
  );
}
