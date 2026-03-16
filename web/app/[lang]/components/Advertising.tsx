"use client";

import { Eye, Target, BarChart3, Coins } from "lucide-react";
import AnimateIn from "./AnimateIn";
import type { Dictionary } from "../dictionaries";

const benefits = [
  { icon: Eye, key: "benefit1" as const },
  { icon: Target, key: "benefit2" as const },
  { icon: BarChart3, key: "benefit3" as const },
  { icon: Coins, key: "benefit4" as const },
];

function PhoneMockup() {
  return (
    <div className="relative mx-auto w-48">
      <svg viewBox="0 0 200 360" fill="none" className="w-full">
        {/* Phone frame */}
        <rect x="8" y="0" width="184" height="360" rx="28" fill="white" fillOpacity="0.05" stroke="white" strokeWidth="1.5" strokeOpacity="0.15" />
        {/* Screen */}
        <rect x="18" y="16" width="164" height="328" rx="16" fill="white" fillOpacity="0.03" />
        {/* Notch */}
        <rect x="70" y="4" width="60" height="8" rx="4" fill="white" fillOpacity="0.08" />

        {/* Ad content mockup */}
        <rect x="30" y="40" width="140" height="100" rx="8" fill="white" fillOpacity="0.06" />
        {/* Play button */}
        <circle cx="100" cy="90" r="20" fill="white" fillOpacity="0.08" stroke="white" strokeWidth="1" strokeOpacity="0.15" />
        <polygon points="94,80 94,100 110,90" fill="white" fillOpacity="0.2" />

        {/* Brand logo placeholder */}
        <rect x="30" y="155" width="60" height="8" rx="4" fill="white" fillOpacity="0.1" />
        <rect x="30" y="170" width="140" height="6" rx="3" fill="white" fillOpacity="0.05" />
        <rect x="30" y="182" width="120" height="6" rx="3" fill="white" fillOpacity="0.05" />
        <rect x="30" y="194" width="100" height="6" rx="3" fill="white" fillOpacity="0.05" />

        {/* Timer */}
        <rect x="60" y="220" width="80" height="28" rx="14" fill="#e9a319" fillOpacity="0.2" stroke="#e9a319" strokeWidth="1" strokeOpacity="0.3" />
        <rect x="80" y="231" width="40" height="6" rx="3" fill="#e9a319" fillOpacity="0.4" />

        {/* Progress bar */}
        <rect x="30" y="264" width="140" height="6" rx="3" fill="white" fillOpacity="0.06" />
        <rect x="30" y="264" width="90" height="6" rx="3" fill="#e9a319" fillOpacity="0.3" />

        {/* CTA button */}
        <rect x="40" y="290" width="120" height="36" rx="12" fill="white" fillOpacity="0.1" stroke="white" strokeWidth="1" strokeOpacity="0.12" />
        <rect x="65" y="304" width="70" height="8" rx="4" fill="white" fillOpacity="0.15" />
      </svg>

      {/* Glow effect */}
      <div className="absolute inset-0 -z-10 bg-[var(--color-brand-gold)]/10 blur-3xl rounded-full scale-150" />
    </div>
  );
}

export default function Advertising({ dict }: { dict: Dictionary }) {
  return (
    <section id="advertising" className="py-24 sm:py-32 bg-[var(--color-text-primary)] relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-[var(--color-brand-green)]/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
      <div className="absolute bottom-0 left-0 w-64 h-64 bg-[var(--color-brand-gold)]/5 rounded-full blur-3xl translate-y-1/2 -translate-x-1/2" />

      <div className="max-w-6xl mx-auto px-5 sm:px-8 relative">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Left - Content */}
          <div>
            <AnimateIn>
              <p className="text-sm font-semibold text-[var(--color-brand-gold)] tracking-wide uppercase mb-3">
                {dict.advertising.label}
              </p>
            </AnimateIn>
            <AnimateIn delay={0.1}>
              <h2
                className="text-3xl sm:text-4xl font-800 tracking-tight mb-5 text-white"
                style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
              >
                {dict.advertising.title}
              </h2>
            </AnimateIn>
            <AnimateIn delay={0.2}>
              <p className="text-lg text-white/50 leading-relaxed mb-10">
                {dict.advertising.description}
              </p>
            </AnimateIn>

            <div className="grid sm:grid-cols-2 gap-4">
              {benefits.map((benefit, i) => {
                const Icon = benefit.icon;
                const titleKey = `${benefit.key}Title` as keyof typeof dict.advertising;
                const descKey = `${benefit.key}Desc` as keyof typeof dict.advertising;

                return (
                  <AnimateIn key={benefit.key} delay={0.25 + i * 0.08}>
                    <div className="p-5 rounded-xl bg-white/[0.04] border border-white/[0.06] hover:bg-white/[0.07] transition-colors">
                      <div className="flex items-center gap-3 mb-3">
                        <div className="w-8 h-8 rounded-lg bg-[var(--color-brand-gold)]/15 flex items-center justify-center">
                          <Icon size={16} className="text-[var(--color-brand-gold)]" strokeWidth={1.8} />
                        </div>
                        <h3
                          className="text-sm font-700 text-white"
                          style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
                        >
                          {dict.advertising[titleKey]}
                        </h3>
                      </div>
                      <p className="text-white/40 leading-relaxed text-sm">
                        {dict.advertising[descKey]}
                      </p>
                    </div>
                  </AnimateIn>
                );
              })}
            </div>
          </div>

          {/* Right - Phone mockup */}
          <AnimateIn delay={0.3} direction="right">
            <div className="hidden lg:block">
              <PhoneMockup />
            </div>
          </AnimateIn>
        </div>
      </div>
    </section>
  );
}
