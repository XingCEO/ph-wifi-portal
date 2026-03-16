"use client";

import { Wifi, Play, Globe } from "lucide-react";
import AnimateIn from "./AnimateIn";
import type { Dictionary } from "../dictionaries";

const steps = [
  { icon: Wifi, key: "step1" as const, color: "#2d6a4f" },
  { icon: Play, key: "step2" as const, color: "#e9a319" },
  { icon: Globe, key: "step3" as const, color: "#2d6a4f" },
];

function StepConnector() {
  return (
    <div className="hidden md:flex items-center justify-center">
      <svg width="48" height="24" viewBox="0 0 48 24" fill="none" className="text-[var(--color-brand-green)]">
        <path
          d="M0 12 H36 M32 6 L42 12 L32 18"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeOpacity="0.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}

export default function HowItWorks({ dict }: { dict: Dictionary }) {
  return (
    <section id="how-it-works" className="py-24 sm:py-32">
      <div className="max-w-6xl mx-auto px-5 sm:px-8">
        <div className="text-center mb-16">
          <AnimateIn>
            <p className="text-sm font-semibold text-[var(--color-brand-green)] tracking-wide uppercase mb-3">
              {dict.howItWorks.label}
            </p>
          </AnimateIn>
          <AnimateIn delay={0.1}>
            <h2
              className="text-3xl sm:text-4xl font-800 tracking-tight"
              style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
            >
              {dict.howItWorks.title}
            </h2>
          </AnimateIn>
        </div>

        <div className="flex flex-col items-center md:flex-row md:items-stretch justify-center gap-4 md:gap-0">
          {steps.map((step, i) => {
            const Icon = step.icon;
            const titleKey = `${step.key}Title` as keyof typeof dict.howItWorks;
            const descKey = `${step.key}Desc` as keyof typeof dict.howItWorks;

            return (
              <div key={step.key} className="contents">
                {i > 0 && <StepConnector />}
                <AnimateIn delay={0.15 + i * 0.12} className="flex-1 w-full max-w-xs">
                  <div className="relative p-8 rounded-2xl bg-white/60 backdrop-blur-xl border border-white/40 hover:border-[var(--color-brand-green)]/25 transition-all hover:shadow-lg hover:shadow-[var(--color-brand-green)]/5 group h-full text-center md:text-left">
                    {/* Step number */}
                    <div
                      className="absolute top-6 right-6 text-5xl font-800 leading-none"
                      style={{
                        fontFamily: "var(--font-plus-jakarta), sans-serif",
                        color: step.color,
                        opacity: 0.07,
                      }}
                    >
                      {i + 1}
                    </div>

                    <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-6 transition-colors mx-auto md:mx-0"
                      style={{ backgroundColor: `${step.color}10` }}
                    >
                      <Icon
                        size={26}
                        style={{ color: step.color }}
                        strokeWidth={1.6}
                      />
                    </div>

                    <h3
                      className="text-xl font-700 mb-3"
                      style={{
                        fontFamily: "var(--font-plus-jakarta), sans-serif",
                      }}
                    >
                      {dict.howItWorks[titleKey]}
                    </h3>
                    <p className="text-[var(--color-text-secondary)] leading-relaxed">
                      {dict.howItWorks[descKey]}
                    </p>
                  </div>
                </AnimateIn>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
