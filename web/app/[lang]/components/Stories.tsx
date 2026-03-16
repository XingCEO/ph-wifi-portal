"use client";

import AnimateIn from "./AnimateIn";
import type { Dictionary } from "../dictionaries";

function StudentIllustration() {
  return (
    <svg viewBox="0 0 120 100" fill="none" className="w-full h-24">
      {/* Desk */}
      <rect x="20" y="70" width="80" height="4" rx="2" fill="#2d6a4f" fillOpacity="0.1" />
      {/* Book */}
      <rect x="30" y="52" width="24" height="18" rx="2" fill="#2d6a4f" fillOpacity="0.08" stroke="#2d6a4f" strokeWidth="1" strokeOpacity="0.15" />
      <line x1="42" y1="54" x2="42" y2="68" stroke="#2d6a4f" strokeWidth="0.75" strokeOpacity="0.1" />
      {/* Tablet/phone */}
      <rect x="62" y="48" width="30" height="22" rx="3" fill="#2d6a4f" fillOpacity="0.06" stroke="#2d6a4f" strokeWidth="1.2" strokeOpacity="0.2" />
      <rect x="66" y="53" width="22" height="12" rx="1" fill="#2d6a4f" fillOpacity="0.04" />
      {/* WiFi symbol above */}
      <path d="M72 38 Q77 30 82 38" stroke="#2d6a4f" strokeWidth="1.5" strokeOpacity="0.2" fill="none" strokeLinecap="round" />
      <path d="M68 32 Q77 22 86 32" stroke="#2d6a4f" strokeWidth="1.2" strokeOpacity="0.12" fill="none" strokeLinecap="round" />
      {/* Pencil */}
      <line x1="48" y1="68" x2="56" y2="56" stroke="#e9a319" strokeWidth="1.5" strokeOpacity="0.4" strokeLinecap="round" />
    </svg>
  );
}

function FamilyIllustration() {
  return (
    <svg viewBox="0 0 120 100" fill="none" className="w-full h-24">
      {/* Phone left */}
      <rect x="12" y="30" width="36" height="50" rx="6" fill="#2d6a4f" fillOpacity="0.06" stroke="#2d6a4f" strokeWidth="1.2" strokeOpacity="0.2" />
      <rect x="16" y="38" width="28" height="32" rx="2" fill="#2d6a4f" fillOpacity="0.04" />
      {/* Face on screen 1 */}
      <circle cx="30" cy="50" r="7" fill="#e9a319" fillOpacity="0.15" stroke="#e9a319" strokeWidth="1" strokeOpacity="0.25" />
      <circle cx="28" cy="49" r="1" fill="#2d6a4f" fillOpacity="0.3" />
      <circle cx="32" cy="49" r="1" fill="#2d6a4f" fillOpacity="0.3" />
      <path d="M27 53 Q30 56 33 53" stroke="#2d6a4f" strokeWidth="0.8" strokeOpacity="0.25" fill="none" strokeLinecap="round" />

      {/* Phone right */}
      <rect x="72" y="30" width="36" height="50" rx="6" fill="#2d6a4f" fillOpacity="0.06" stroke="#2d6a4f" strokeWidth="1.2" strokeOpacity="0.2" />
      <rect x="76" y="38" width="28" height="32" rx="2" fill="#2d6a4f" fillOpacity="0.04" />
      {/* Face on screen 2 */}
      <circle cx="90" cy="50" r="7" fill="#2d6a4f" fillOpacity="0.1" stroke="#2d6a4f" strokeWidth="1" strokeOpacity="0.2" />
      <circle cx="88" cy="49" r="1" fill="#2d6a4f" fillOpacity="0.3" />
      <circle cx="92" cy="49" r="1" fill="#2d6a4f" fillOpacity="0.3" />
      <path d="M87 53 Q90 56 93 53" stroke="#2d6a4f" strokeWidth="0.8" strokeOpacity="0.25" fill="none" strokeLinecap="round" />

      {/* Connection wave between */}
      <path d="M48 50 Q60 35 72 50" stroke="#e9a319" strokeWidth="1.5" strokeOpacity="0.3" fill="none" strokeDasharray="3 3" />
      <path d="M48 55 Q60 70 72 55" stroke="#e9a319" strokeWidth="1.5" strokeOpacity="0.3" fill="none" strokeDasharray="3 3" />
      {/* Heart */}
      <path d="M57 48 C57 45 53 43 53 46 C53 49 57 52 57 52 C57 52 61 49 61 46 C61 43 57 45 57 48Z" fill="#e9a319" fillOpacity="0.25" />
    </svg>
  );
}

function StoreIllustration() {
  return (
    <svg viewBox="0 0 120 100" fill="none" className="w-full h-24">
      {/* Store front */}
      <rect x="20" y="40" width="80" height="40" rx="2" fill="#2d6a4f" fillOpacity="0.04" stroke="#2d6a4f" strokeWidth="1.2" strokeOpacity="0.15" />
      {/* Roof */}
      <path d="M15 40 L60 18 L105 40" stroke="#2d6a4f" strokeWidth="1.5" strokeOpacity="0.2" fill="#2d6a4f" fillOpacity="0.03" strokeLinejoin="round" />
      {/* Door */}
      <rect x="48" y="56" width="24" height="24" rx="2" fill="#2d6a4f" fillOpacity="0.06" stroke="#2d6a4f" strokeWidth="0.8" strokeOpacity="0.12" />
      {/* Window left */}
      <rect x="26" y="48" width="16" height="14" rx="1" fill="#e9a319" fillOpacity="0.08" stroke="#e9a319" strokeWidth="0.8" strokeOpacity="0.2" />
      <line x1="34" y1="48" x2="34" y2="62" stroke="#e9a319" strokeWidth="0.5" strokeOpacity="0.15" />
      <line x1="26" y1="55" x2="42" y2="55" stroke="#e9a319" strokeWidth="0.5" strokeOpacity="0.15" />
      {/* Window right */}
      <rect x="78" y="48" width="16" height="14" rx="1" fill="#e9a319" fillOpacity="0.08" stroke="#e9a319" strokeWidth="0.8" strokeOpacity="0.2" />
      <line x1="86" y1="48" x2="86" y2="62" stroke="#e9a319" strokeWidth="0.5" strokeOpacity="0.15" />
      <line x1="78" y1="55" x2="94" y2="55" stroke="#e9a319" strokeWidth="0.5" strokeOpacity="0.15" />
      {/* WiFi signal on roof */}
      <path d="M52 22 Q60 14 68 22" stroke="#2d6a4f" strokeWidth="1.5" strokeOpacity="0.25" fill="none" strokeLinecap="round" />
      <path d="M48 17 Q60 7 72 17" stroke="#2d6a4f" strokeWidth="1.2" strokeOpacity="0.15" fill="none" strokeLinecap="round" />
      {/* Sign */}
      <rect x="38" y="28" width="44" height="10" rx="2" fill="white" stroke="#2d6a4f" strokeWidth="0.8" strokeOpacity="0.15" />
      <rect x="42" y="32" width="36" height="3" rx="1.5" fill="#2d6a4f" fillOpacity="0.1" />
    </svg>
  );
}

const illustrations = [StudentIllustration, FamilyIllustration, StoreIllustration];

const storyKeys = ["story1", "story2", "story3"] as const;

export default function Stories({ dict }: { dict: Dictionary }) {
  return (
    <section className="py-24 sm:py-32 relative overflow-hidden">
      {/* Decorative background */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[var(--color-brand-green)]/10 to-transparent" />

      <div className="max-w-6xl mx-auto px-5 sm:px-8">
        <div className="max-w-2xl mb-16">
          <AnimateIn>
            <p className="text-sm font-semibold text-[var(--color-brand-green)] tracking-wide uppercase mb-3">
              {dict.stories.label}
            </p>
          </AnimateIn>
          <AnimateIn delay={0.1}>
            <h2
              className="text-3xl sm:text-4xl font-800 tracking-tight mb-5"
              style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
            >
              {dict.stories.title}
            </h2>
          </AnimateIn>
          <AnimateIn delay={0.2}>
            <p className="text-lg text-[var(--color-text-secondary)] leading-relaxed">
              {dict.stories.description}
            </p>
          </AnimateIn>
        </div>

        <div className="grid md:grid-cols-3 gap-6 sm:gap-8">
          {storyKeys.map((key, i) => {
            const Illustration = illustrations[i];
            const titleKey = `${key}Title` as keyof typeof dict.stories;
            const descKey = `${key}Desc` as keyof typeof dict.stories;

            return (
              <AnimateIn key={key} delay={0.15 + i * 0.1}>
                <div className="p-8 rounded-2xl bg-white/60 backdrop-blur-xl border border-white/40 hover:shadow-lg hover:shadow-black/[0.04] transition-all group h-full flex flex-col">
                  <div className="mb-6 opacity-70 group-hover:opacity-100 transition-opacity">
                    <Illustration />
                  </div>
                  <h3
                    className="text-xl font-700 mb-3"
                    style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
                  >
                    {dict.stories[titleKey]}
                  </h3>
                  <p className="text-[var(--color-text-secondary)] leading-relaxed flex-1">
                    {dict.stories[descKey]}
                  </p>
                </div>
              </AnimateIn>
            );
          })}
        </div>
      </div>
    </section>
  );
}
