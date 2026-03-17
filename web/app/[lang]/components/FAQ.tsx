"use client";

import { useState } from "react";
import { Plus, Minus } from "lucide-react";
import AnimateIn from "./AnimateIn";
import type { Dictionary } from "../dictionaries";

export default function FAQ({ dict }: { dict: Dictionary }) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const faqs = dict.faq.items as Array<{ q: string; a: string }>;

  return (
    <section id="faq" className="py-24 sm:py-32 bg-[var(--color-warm-white)]">
      <div className="max-w-2xl mx-auto px-5 sm:px-8">
        {/* Header */}
        <AnimateIn>
          <div className="text-center mb-14">
            <span
              className="text-xs font-bold tracking-[0.15em] uppercase mb-4 block"
              style={{ color: "var(--color-brand-green)" }}
            >
              {dict.faq.label}
            </span>
            <h2
              className="text-3xl sm:text-4xl font-extrabold tracking-tight mb-4"
              style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
            >
              {dict.faq.title}
            </h2>
            <p
              className="text-lg"
              style={{ color: "var(--color-text-secondary)" }}
            >
              {dict.faq.description}
            </p>
          </div>
        </AnimateIn>

        {/* Accordion */}
        <AnimateIn delay={0.1}>
          <div className="flex flex-col gap-3">
            {faqs.map((faq, i) => {
              const isOpen = openIndex === i;
              return (
                <div
                  key={i}
                  className="rounded-2xl overflow-hidden transition-all card-lift"
                  style={{
                    background: "white",
                    border: isOpen
                      ? "1px solid rgba(45,106,79,0.2)"
                      : "1px solid rgba(0,0,0,0.06)",
                    boxShadow: isOpen
                      ? "0 4px 16px rgba(45,106,79,0.08)"
                      : "0 1px 4px rgba(0,0,0,0.04)",
                  }}
                >
                  <button
                    onClick={() => setOpenIndex(isOpen ? null : i)}
                    className="w-full flex items-center justify-between px-6 py-5 text-left"
                    aria-expanded={isOpen}
                  >
                    <span
                      className="font-semibold text-[var(--color-text-primary)] pr-4 text-base leading-snug"
                      style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
                    >
                      {faq.q}
                    </span>
                    <div
                      className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center transition-colors"
                      style={{
                        background: isOpen
                          ? "var(--color-brand-green)"
                          : "var(--color-warm-gray)",
                      }}
                    >
                      {isOpen ? (
                        <Minus
                          size={13}
                          strokeWidth={2.5}
                          style={{ color: "white" }}
                        />
                      ) : (
                        <Plus
                          size={13}
                          strokeWidth={2.5}
                          style={{ color: "var(--color-text-secondary)" }}
                        />
                      )}
                    </div>
                  </button>

                  {/* Answer with height transition */}
                  <div
                    style={{
                      maxHeight: isOpen ? "500px" : "0",
                      opacity: isOpen ? 1 : 0,
                      overflow: "hidden",
                      transition: "max-height 0.35s ease, opacity 0.3s ease",
                    }}
                  >
                    <p
                      className="px-6 pb-5 text-base leading-relaxed"
                      style={{ color: "var(--color-text-secondary)" }}
                    >
                      {faq.a}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </AnimateIn>
      </div>
    </section>
  );
}
