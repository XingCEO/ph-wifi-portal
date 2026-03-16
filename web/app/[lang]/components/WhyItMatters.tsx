"use client";

import { MapPin, Megaphone, Heart } from "lucide-react";
import AnimateIn from "./AnimateIn";
import CountUp from "./CountUp";
import type { Dictionary } from "../dictionaries";

const points = [
  { icon: MapPin, key: "point1" as const },
  { icon: Megaphone, key: "point2" as const },
  { icon: Heart, key: "point3" as const },
];

const stats = [
  { value: "98M", suffix: "", label: "Internet users in the Philippines" },
  { value: "86%", suffix: "", label: "Mobile data consumed over WiFi" },
  { value: "8.8hrs", suffix: "", label: "Average daily time online" },
  { value: "19M", suffix: "", label: "Filipinos still offline" },
];

export default function WhyItMatters({ dict }: { dict: Dictionary }) {
  return (
    <section id="why" className="py-24 sm:py-32 bg-white">
      <div className="max-w-6xl mx-auto px-5 sm:px-8">
        {/* Stats bar */}
        <AnimateIn>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-20 p-10 rounded-3xl bg-gradient-to-br from-[var(--color-brand-green)]/[0.03] to-[var(--color-brand-gold)]/[0.02] border border-[var(--color-brand-green)]/8">
            {stats.map((stat, i) => (
              <div key={stat.value} className={`text-center ${i < 3 ? "md:border-r md:border-[var(--color-brand-green)]/8" : ""}`}>
                <div
                  className="text-2xl sm:text-3xl font-800 text-[var(--color-brand-green)] mb-1.5"
                  style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
                >
                  <CountUp value={stat.value} />
                </div>
                <div className="text-xs sm:text-sm text-[var(--color-text-muted)] leading-snug">
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </AnimateIn>

        <div className="grid lg:grid-cols-5 gap-12 lg:gap-16">
          {/* Left - Text */}
          <div className="lg:col-span-2">
            <AnimateIn>
              <p className="text-sm font-semibold text-[var(--color-brand-green)] tracking-wide uppercase mb-3">
                {dict.why.label}
              </p>
            </AnimateIn>
            <AnimateIn delay={0.1}>
              <h2
                className="text-3xl sm:text-4xl font-800 tracking-tight mb-5"
                style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
              >
                {dict.why.title}
              </h2>
            </AnimateIn>
            <AnimateIn delay={0.2}>
              <p className="text-lg text-[var(--color-text-secondary)] leading-relaxed mb-8">
                {dict.why.description}
              </p>
            </AnimateIn>
            <AnimateIn delay={0.3}>
              <div className="border-l-[3px] border-[var(--color-brand-gold)] pl-5 py-1">
                <p className="text-lg font-500 text-[var(--color-text-primary)] italic leading-relaxed">
                  {dict.why.closing}
                </p>
              </div>
            </AnimateIn>
          </div>

          {/* Right - Cards */}
          <div className="lg:col-span-3 flex flex-col gap-4">
            {points.map((point, i) => {
              const Icon = point.icon;
              const titleKey = `${point.key}Title` as keyof typeof dict.why;
              const descKey = `${point.key}Desc` as keyof typeof dict.why;

              return (
                <AnimateIn key={point.key} delay={0.15 + i * 0.1} direction="right">
                  <div className="flex gap-5 p-6 rounded-2xl bg-white/60 backdrop-blur-xl border border-white/40 hover:border-[var(--color-brand-green)]/20 transition-all duration-300 hover:shadow-lg hover:shadow-[var(--color-brand-green)]/[0.04] hover:-translate-y-0.5 group">
                    <div className="w-12 h-12 rounded-xl bg-[var(--color-brand-gold)]/10 flex items-center justify-center shrink-0 group-hover:bg-[var(--color-brand-gold)]/15 transition-colors">
                      <Icon
                        size={22}
                        className="text-[var(--color-brand-gold)]"
                        strokeWidth={1.6}
                      />
                    </div>
                    <div>
                      <h3
                        className="text-lg font-700 mb-2"
                        style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
                      >
                        {dict.why[titleKey]}
                      </h3>
                      <p className="text-[var(--color-text-secondary)] leading-relaxed text-[15px]">
                        {dict.why[descKey]}
                      </p>
                    </div>
                  </div>
                </AnimateIn>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
