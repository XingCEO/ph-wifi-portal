"use client";

import { Wifi, ArrowRight, Signal } from "lucide-react";
import AnimateIn from "./AnimateIn";
import ScrollIndicator from "./ScrollIndicator";
import type { Dictionary } from "../dictionaries";

function AnimatedWifiIllustration() {
  return (
    <div className="relative w-full max-w-[360px] mx-auto">
      {/* Outer glow rings */}
      <div
        className="absolute inset-0 rounded-full animate-glow-pulse"
        style={{
          background:
            "radial-gradient(circle, rgba(45,106,79,0.12) 0%, transparent 70%)",
          transform: "scale(1.3)",
        }}
      />

      {/* Phone mockup */}
      <div className="animate-float relative mx-auto w-[200px]">
        {/* WiFi arcs above phone */}
        <div className="flex flex-col items-center gap-2 mb-4">
          <div
            className="w-3 h-3 rounded-full"
            style={{ background: "var(--color-brand-green)", opacity: 0.9 }}
          />
          <svg width="80" height="48" viewBox="0 0 80 48" fill="none">
            <path
              d="M10 40 Q40 8 70 40"
              stroke="var(--color-brand-green)"
              strokeWidth="3"
              strokeOpacity="0.7"
              fill="none"
              strokeLinecap="round"
            />
            <path
              d="M22 40 Q40 20 58 40"
              stroke="var(--color-brand-green)"
              strokeWidth="3"
              strokeOpacity="0.5"
              fill="none"
              strokeLinecap="round"
            />
            <path
              d="M31 40 Q40 30 49 40"
              stroke="var(--color-brand-green)"
              strokeWidth="3"
              strokeOpacity="0.35"
              fill="none"
              strokeLinecap="round"
            />
          </svg>
        </div>

        {/* Phone body */}
        <div
          className="relative rounded-[2rem] overflow-hidden shadow-2xl mx-auto"
          style={{
            width: 160,
            height: 280,
            background: "white",
            border: "2px solid rgba(0,0,0,0.08)",
            boxShadow:
              "0 30px 60px rgba(0,0,0,0.12), 0 0 0 1px rgba(255,255,255,0.5) inset",
          }}
        >
          {/* Status bar */}
          <div
            className="flex items-center justify-between px-5 pt-3 pb-1"
            style={{ background: "rgba(45,106,79,0.04)" }}
          >
            <span className="text-[10px] font-bold text-[var(--color-text-primary)]">
              9:41
            </span>
            <div className="flex items-center gap-1">
              <Signal size={10} style={{ color: "var(--color-brand-green)" }} />
              <Wifi size={10} style={{ color: "var(--color-brand-green)" }} />
            </div>
          </div>

          {/* Screen content */}
          <div className="flex flex-col items-center pt-6 px-4 gap-3">
            {/* Brand badge */}
            <div
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full"
              style={{
                background: "rgba(45,106,79,0.08)",
                border: "1px solid rgba(45,106,79,0.15)",
              }}
            >
              <Wifi size={10} style={{ color: "var(--color-brand-green)" }} />
              <span
                className="text-[10px] font-bold"
                style={{ color: "var(--color-brand-green)" }}
              >
                AbotKamay WiFi
              </span>
            </div>

            {/* Ad area */}
            <div
              className="w-full rounded-xl overflow-hidden"
              style={{
                height: 80,
                background:
                  "linear-gradient(135deg, rgba(45,106,79,0.06) 0%, rgba(233,163,25,0.06) 100%)",
                border: "1px solid rgba(45,106,79,0.08)",
              }}
            >
              <div className="flex items-center justify-center h-full">
                <span
                  className="text-[10px] font-medium"
                  style={{ color: "var(--color-text-muted)" }}
                >
                  Advertisement
                </span>
              </div>
            </div>

            {/* Progress bar */}
            <div className="w-full">
              <div
                className="flex justify-between mb-1"
                style={{ color: "var(--color-text-muted)" }}
              >
                <span className="text-[9px]">Loading...</span>
                <span className="text-[9px]">5s</span>
              </div>
              <div
                className="w-full h-1.5 rounded-full overflow-hidden"
                style={{ background: "rgba(0,0,0,0.06)" }}
              >
                <div
                  className="h-full rounded-full"
                  style={{
                    width: "60%",
                    background: "var(--color-brand-green)",
                  }}
                />
              </div>
            </div>

            {/* Connect button */}
            <div
              className="w-full py-2.5 rounded-xl text-center"
              style={{
                background: "var(--color-brand-green)",
              }}
            >
              <span className="text-[11px] font-bold text-white">
                Get Free Internet →
              </span>
            </div>

            {/* Free badge */}
            <div className="flex items-center gap-1">
              <div
                className="w-1.5 h-1.5 rounded-full animate-pulse"
                style={{ background: "var(--color-brand-green)" }}
              />
              <span
                className="text-[9px] font-semibold"
                style={{ color: "var(--color-brand-green)" }}
              >
                FREE • 10 minutes
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Floating badges */}
      <div
        className="absolute top-8 -left-4 animate-float-slow"
        style={{ animationDelay: "1s" }}
      >
        <div
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl shadow-lg"
          style={{
            background: "white",
            border: "1px solid rgba(45,106,79,0.12)",
            boxShadow: "0 4px 16px rgba(0,0,0,0.08)",
          }}
        >
          <div
            className="w-6 h-6 rounded-full flex items-center justify-center"
            style={{ background: "rgba(45,106,79,0.1)" }}
          >
            <Wifi size={12} style={{ color: "var(--color-brand-green)" }} />
          </div>
          <div>
            <div className="text-[10px] font-bold text-[var(--color-text-primary)]">
              Connected!
            </div>
            <div
              className="text-[9px]"
              style={{ color: "var(--color-text-muted)" }}
            >
              10 min free
            </div>
          </div>
        </div>
      </div>

      <div
        className="absolute bottom-16 -right-4 animate-float-slow"
        style={{ animationDelay: "2.5s" }}
      >
        <div
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl"
          style={{
            background: "white",
            border: "1px solid rgba(233,163,25,0.2)",
            boxShadow: "0 4px 16px rgba(0,0,0,0.08)",
          }}
        >
          <div
            className="w-6 h-6 rounded-full flex items-center justify-center"
            style={{ background: "rgba(233,163,25,0.1)" }}
          >
            <span className="text-xs">📶</span>
          </div>
          <div>
            <div className="text-[10px] font-bold text-[var(--color-text-primary)]">
              100% Free
            </div>
            <div
              className="text-[9px]"
              style={{ color: "var(--color-text-muted)" }}
            >
              No data needed
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Hero({ dict }: { dict: Dictionary }) {
  return (
    <section className="relative min-h-screen flex items-center pt-16 overflow-hidden">
      {/* Background radial glow */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 80% 60% at 50% 0%, rgba(45,106,79,0.05) 0%, transparent 70%)",
        }}
      />

      {/* Background dot pattern */}
      <div className="absolute inset-0 opacity-[0.022]">
        <svg width="100%" height="100%">
          <defs>
            <pattern
              id="hero-dots"
              width="32"
              height="32"
              patternUnits="userSpaceOnUse"
            >
              <circle cx="1" cy="1" r="0.8" fill="currentColor" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#hero-dots)" />
        </svg>
      </div>

      {/* Gradient accents */}
      <div className="absolute top-20 left-0 w-[500px] h-[500px] bg-gradient-to-br from-[var(--color-brand-green)]/[0.05] to-transparent rounded-full blur-3xl animate-glow-pulse" />
      <div className="absolute bottom-20 right-0 w-[400px] h-[400px] bg-gradient-to-tl from-[var(--color-brand-gold)]/[0.05] to-transparent rounded-full blur-3xl animate-glow-pulse" style={{ animationDelay: "2s" }} />

      <div className="relative max-w-6xl mx-auto px-5 sm:px-8 w-full py-16">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-8 items-center">
          {/* Left — Text */}
          <div>
            <AnimateIn delay={0.05}>
              <div className="inline-flex items-center gap-2 px-4 py-2 mb-8 rounded-full bg-[var(--color-brand-green)]/8 backdrop-blur-sm border border-[var(--color-brand-green)]/12">
                <div className="w-1.5 h-1.5 rounded-full bg-[var(--color-brand-green)] animate-pulse" />
                <span className="text-sm font-semibold text-[var(--color-brand-green)] tracking-wide">
                  AbotKamay WiFi
                </span>
              </div>
            </AnimateIn>

            <AnimateIn delay={0.15}>
              <h1
                className="text-[3rem] sm:text-[3.75rem] lg:text-[4.25rem] font-extrabold tracking-[-0.04em] leading-[1.05] mb-7"
                style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
              >
                {dict.hero.title}{" "}
                <span
                  className="bg-clip-text text-transparent"
                  style={{
                    backgroundImage:
                      "linear-gradient(135deg, var(--color-brand-green) 0%, var(--color-brand-green-light) 100%)",
                  }}
                >
                  {dict.hero.titleHighlight}
                </span>
              </h1>
            </AnimateIn>

            <AnimateIn delay={0.3}>
              <p className="text-xl sm:text-2xl text-[var(--color-text-secondary)] max-w-lg leading-[1.65] mb-4 font-medium">
                {dict.hero.description}
              </p>
            </AnimateIn>

            <AnimateIn delay={0.4}>
              <p className="text-base text-[var(--color-text-muted)] max-w-md leading-relaxed mb-12">
                {dict.hero.mission}
              </p>
            </AnimateIn>

            <AnimateIn delay={0.5}>
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
                <a
                  href="#contact"
                  className="inline-flex items-center gap-2.5 px-8 py-4 text-white font-bold rounded-2xl hover:shadow-xl transition-all text-base no-underline group btn-scale"
                  style={{
                    background: "var(--color-brand-green)",
                    boxShadow: "0 4px 16px rgba(45,106,79,0.3)",
                    fontFamily: "var(--font-plus-jakarta), sans-serif",
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
                  {dict.hero.cta}
                  <ArrowRight
                    size={18}
                    className="group-hover:translate-x-1 transition-transform"
                  />
                </a>
                <a
                  href="#how-it-works"
                  className="inline-flex items-center gap-2 px-6 py-4 text-[var(--color-text-secondary)] font-semibold rounded-2xl hover:bg-[var(--color-warm-gray)] transition-colors text-base no-underline border border-[#e0dbd5]"
                >
                  <Wifi size={16} />
                  {dict.nav.howItWorks}
                </a>
              </div>
            </AnimateIn>

            {/* Social proof bar */}
            <AnimateIn delay={0.65}>
              <div className="flex items-center gap-6 mt-10 pt-8 border-t border-[#e8e4de]">
                {[
                  { value: "10min", label: "Free per session" },
                  { value: "24/7", label: "Always available" },
                  { value: "100%", label: "Free for users" },
                ].map((stat) => (
                  <div key={stat.value}>
                    <div
                      className="text-xl font-extrabold"
                      style={{
                        color: "var(--color-brand-green)",
                        fontFamily: "var(--font-plus-jakarta), sans-serif",
                      }}
                    >
                      {stat.value}
                    </div>
                    <div
                      className="text-xs font-medium"
                      style={{ color: "var(--color-text-muted)" }}
                    >
                      {stat.label}
                    </div>
                  </div>
                ))}
              </div>
            </AnimateIn>
          </div>

          {/* Right — Illustration */}
          <AnimateIn delay={0.25} direction="right" duration={0.8}>
            <div className="hidden lg:flex items-center justify-center">
              <AnimatedWifiIllustration />
            </div>
          </AnimateIn>
        </div>
      </div>

      <ScrollIndicator />
    </section>
  );
}
