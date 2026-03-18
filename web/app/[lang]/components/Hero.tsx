"use client";

import { Wifi, ArrowRight, Zap, Shield, Users, MapPin } from "lucide-react";
import AnimateIn from "./AnimateIn";
import ScrollIndicator from "./ScrollIndicator";
import IPhoneMockup from "./IPhoneMockup";
import PortalScreen from "./PortalScreen";
import type { Dictionary } from "../dictionaries";

export default function Hero({ dict }: { dict: Dictionary }) {
  return (
    <section className="relative min-h-screen flex items-center pt-16 overflow-hidden">
      {/* Background radial glow */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 80% 60% at 50% 0%, rgba(27,79,138,0.05) 0%, transparent 70%)",
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
                    boxShadow: "0 4px 16px rgba(27,79,138,0.3)",
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

          {/* Right — iPhone mockup + feature tags below */}
          <AnimateIn delay={0.25} direction="right" duration={0.8}>
            <div className="hidden lg:flex flex-col items-center gap-8">
              {/* Phone */}
              <div className="relative">
                {/* Background glow */}
                <div className="absolute animate-glow-pulse" style={{
                  top: "10%", left: "-10%", right: "-10%", bottom: "10%",
                  background: "radial-gradient(circle, rgba(0,153,219,0.1) 0%, transparent 70%)",
                  borderRadius: "50%", filter: "blur(40px)",
                }} />

                <div className="relative animate-float" style={{ width: 240 }}>
                  <IPhoneMockup>
                    <PortalScreen dict={dict} />
                  </IPhoneMockup>

                  {/* Phone shadow */}
                  <div style={{
                    position: "absolute", bottom: -16, left: "15%", right: "15%", height: 24,
                    background: "radial-gradient(ellipse, rgba(0,0,0,0.1) 0%, transparent 70%)",
                    borderRadius: "50%", filter: "blur(6px)",
                  }} />
                </div>
              </div>

              {/* Feature tags — 2×2 grid below phone */}
              <div style={{
                display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10,
                width: "100%", maxWidth: 320,
              }}>
                {[
                  { icon: <Zap size={14} color="white" />, bg: "linear-gradient(135deg, #22c55e, #16a34a)", label: "Instant", sub: "No password" },
                  { icon: <Shield size={14} color="white" />, bg: "linear-gradient(135deg, #F58220, #f97316)", label: "Secure", sub: "Protected WiFi" },
                  { icon: <Users size={14} color="white" />, bg: "linear-gradient(135deg, #0099DB, #1B4F8A)", label: "2,847+", sub: "Users online" },
                  { icon: <MapPin size={14} color="white" />, bg: "linear-gradient(135deg, #8b5cf6, #7c3aed)", label: "50+", sub: "Hotspots" },
                ].map((item, i) => (
                  <div
                    key={i}
                    style={{
                      display: "flex", alignItems: "center", gap: 8,
                      padding: "10px 12px", borderRadius: 14,
                      background: "white",
                      boxShadow: "0 2px 12px rgba(0,0,0,0.05)",
                      border: "1px solid rgba(0,0,0,0.04)",
                    }}
                  >
                    <div style={{
                      width: 30, height: 30, borderRadius: 8, flexShrink: 0,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      background: item.bg,
                    }}>
                      {item.icon}
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: "#1a1a1a", lineHeight: 1.2 }}>{item.label}</div>
                      <div style={{ fontSize: 9, color: "#7a7a7a", lineHeight: 1.2 }}>{item.sub}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </AnimateIn>
        </div>
      </div>

      <ScrollIndicator />
    </section>
  );
}
