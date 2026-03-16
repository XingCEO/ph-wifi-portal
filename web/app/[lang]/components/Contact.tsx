"use client";

import { Mail, ArrowUpRight } from "lucide-react";
import AnimateIn from "./AnimateIn";
import type { Dictionary } from "../dictionaries";

export default function Contact({ dict }: { dict: Dictionary }) {
  return (
    <section id="contact" className="py-24 sm:py-32 relative overflow-hidden">
      {/* Gradient background */}
      <div className="absolute inset-0 bg-gradient-to-b from-[var(--color-warm-white)] via-[var(--color-brand-green)]/[0.03] to-[var(--color-warm-white)]" />

      <div className="max-w-6xl mx-auto px-5 sm:px-8 relative">
        <AnimateIn>
          <div className="max-w-2xl mx-auto text-center p-10 sm:p-14 rounded-3xl bg-white border border-[#eae6e0] shadow-xl shadow-black/[0.03]">
            <p className="text-sm font-semibold text-[var(--color-brand-green)] tracking-wide uppercase mb-3">
              {dict.contact.label}
            </p>
            <h2
              className="text-3xl sm:text-4xl font-800 tracking-tight mb-5"
              style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
            >
              {dict.contact.title}
            </h2>
            <p className="text-lg text-[var(--color-text-secondary)] leading-relaxed mb-10">
              {dict.contact.description}
            </p>
            <a
              href={`mailto:${dict.contact.email}`}
              className="inline-flex items-center gap-3 px-8 py-4 bg-[var(--color-brand-green)] text-white font-semibold rounded-xl hover:bg-[var(--color-brand-green-light)] transition-colors text-base no-underline group"
            >
              <Mail size={18} strokeWidth={1.8} />
              <span>{dict.contact.email}</span>
              <ArrowUpRight
                size={16}
                className="opacity-50 group-hover:opacity-100 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all"
              />
            </a>
          </div>
        </AnimateIn>
      </div>
    </section>
  );
}
