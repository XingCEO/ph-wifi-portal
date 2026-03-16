"use client";

import { Store, Building2, Bus, TreePalm, Coffee, ShoppingBag } from "lucide-react";
import AnimateIn from "./AnimateIn";
import type { Dictionary } from "../dictionaries";

type CoverageKey = "sariSari" | "cafes" | "community" | "transport" | "public" | "markets";

const locations: { icon: typeof Store; key: CoverageKey }[] = [
  { icon: Store, key: "sariSari" },
  { icon: Coffee, key: "cafes" },
  { icon: Building2, key: "community" },
  { icon: Bus, key: "transport" },
  { icon: TreePalm, key: "public" },
  { icon: ShoppingBag, key: "markets" },
];

export default function Coverage({ dict }: { dict: Dictionary; lang: string }) {
  return (
    <section className="py-24 sm:py-32 bg-[var(--color-warm-gray)]/50">
      <div className="max-w-6xl mx-auto px-5 sm:px-8">
        <div className="text-center mb-14">
          <AnimateIn>
            <p className="text-sm font-semibold text-[var(--color-brand-green)] tracking-wide uppercase mb-3">
              {dict.coverage.label}
            </p>
          </AnimateIn>
          <AnimateIn delay={0.1}>
            <h2
              className="text-3xl sm:text-4xl font-800 tracking-tight mb-4"
              style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
            >
              {dict.coverage.title}
            </h2>
          </AnimateIn>
          <AnimateIn delay={0.2}>
            <p className="text-lg text-[var(--color-text-secondary)] max-w-xl mx-auto">
              {dict.coverage.description}
            </p>
          </AnimateIn>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 sm:gap-5 max-w-3xl mx-auto">
          {locations.map((loc, i) => {
            const Icon = loc.icon;
            return (
              <AnimateIn key={loc.key} delay={0.1 + i * 0.06}>
                <div className="flex flex-col items-center gap-3 p-6 sm:p-8 rounded-2xl bg-white/60 backdrop-blur-xl border border-white/40 hover:border-[var(--color-brand-green)]/20 hover:shadow-lg hover:shadow-[var(--color-brand-green)]/[0.04] transition-all duration-300 hover:-translate-y-1 group">
                  <div className="w-12 h-12 rounded-xl bg-[var(--color-brand-green)]/6 flex items-center justify-center group-hover:bg-[var(--color-brand-green)]/10 transition-colors">
                    <Icon
                      size={24}
                      className="text-[var(--color-brand-green)]"
                      strokeWidth={1.5}
                    />
                  </div>
                  <span className="text-sm font-semibold text-[var(--color-text-primary)] text-center leading-tight">
                    {dict.coverage[loc.key]}
                  </span>
                </div>
              </AnimateIn>
            );
          })}
        </div>
      </div>
    </section>
  );
}
