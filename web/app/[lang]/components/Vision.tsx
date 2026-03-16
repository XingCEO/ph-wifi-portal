"use client";

import AnimateIn from "./AnimateIn";
import type { Dictionary } from "../dictionaries";

export default function Vision({ dict }: { dict: Dictionary }) {
  const stats = [
    { value: dict.vision.stat1Value, label: dict.vision.stat1Label },
    { value: dict.vision.stat2Value, label: dict.vision.stat2Label },
    { value: dict.vision.stat3Value, label: dict.vision.stat3Label },
  ];

  return (
    <section className="py-24 sm:py-32 bg-white relative overflow-hidden">
      {/* Decorative background */}
      <div className="absolute inset-0 opacity-[0.02]">
        <svg width="100%" height="100%">
          <defs>
            <pattern id="vision-grid" width="64" height="64" patternUnits="userSpaceOnUse">
              <line x1="0" y1="0" x2="64" y2="0" stroke="currentColor" strokeWidth="0.5" />
              <line x1="0" y1="0" x2="0" y2="64" stroke="currentColor" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#vision-grid)" />
        </svg>
      </div>

      <div className="max-w-6xl mx-auto px-5 sm:px-8 relative">
        <div className="max-w-3xl mx-auto text-center mb-14">
          <AnimateIn>
            <p className="text-sm font-semibold text-[var(--color-brand-green)] tracking-wide uppercase mb-3">
              {dict.vision.label}
            </p>
          </AnimateIn>
          <AnimateIn delay={0.1}>
            <h2
              className="text-3xl sm:text-4xl font-800 tracking-tight mb-6"
              style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
            >
              {dict.vision.title}
            </h2>
          </AnimateIn>
          <AnimateIn delay={0.2}>
            <p className="text-lg text-[var(--color-text-secondary)] leading-relaxed">
              {dict.vision.description}
            </p>
          </AnimateIn>
        </div>

        <AnimateIn delay={0.3}>
          <div className="grid grid-cols-3 gap-4 sm:gap-8 max-w-2xl mx-auto">
            {stats.map((stat) => (
              <div
                key={stat.label}
                className="text-center p-6 sm:p-8 rounded-2xl bg-[var(--color-warm-white)] border border-[#eae6e0]"
              >
                <div
                  className="text-3xl sm:text-4xl font-800 text-[var(--color-brand-green)] mb-2"
                  style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
                >
                  {stat.value}
                </div>
                <div className="text-xs sm:text-sm text-[var(--color-text-muted)] font-medium leading-tight">
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </AnimateIn>
      </div>
    </section>
  );
}
