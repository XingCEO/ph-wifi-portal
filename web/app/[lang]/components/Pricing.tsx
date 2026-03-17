"use client";

import { Check } from "lucide-react";
import AnimateIn from "./AnimateIn";
import type { Dictionary } from "../dictionaries";

export default function Pricing({ dict }: { dict: Dictionary }) {
  const p = dict.pricing;

  const plans = [
    {
      key: "free",
      name: p.free.name,
      price: p.free.price,
      period: p.free.period,
      revenue: p.free.revenue,
      sites: p.free.sites,
      features: p.free.features as string[],
      popular: false,
      cta: p.cta,
      ctaHref: "#contact",
    },
    {
      key: "pro",
      name: p.pro.name,
      price: p.pro.price,
      period: p.pro.period,
      revenue: p.pro.revenue,
      sites: p.pro.sites,
      features: p.pro.features as string[],
      popular: true,
      cta: p.cta,
      ctaHref: "#contact",
    },
    {
      key: "business",
      name: p.business.name,
      price: p.business.price,
      period: p.business.period,
      revenue: p.business.revenue,
      sites: p.business.sites,
      features: p.business.features as string[],
      popular: false,
      cta: p.cta,
      ctaHref: "#contact",
    },
  ];

  return (
    <section id="pricing" className="py-24 sm:py-32 bg-[var(--color-warm-white)]">
      <div className="max-w-6xl mx-auto px-5 sm:px-8">
        {/* Header */}
        <AnimateIn>
          <div className="text-center mb-16">
            <span
              className="text-xs font-bold tracking-[0.15em] uppercase mb-4 block"
              style={{ color: "var(--color-brand-green)" }}
            >
              {p.label}
            </span>
            <h2
              className="text-3xl sm:text-4xl font-extrabold tracking-tight mb-4"
              style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
            >
              {p.title}
            </h2>
            <p
              className="text-lg max-w-xl mx-auto"
              style={{ color: "var(--color-text-secondary)" }}
            >
              {p.description}
            </p>
          </div>
        </AnimateIn>

        {/* Cards */}
        <div className="grid md:grid-cols-3 gap-6 items-start">
          {plans.map((plan, i) => (
            <AnimateIn key={plan.key} delay={0.1 * i}>
              <div
                className={`relative rounded-3xl p-8 flex flex-col gap-6 card-lift transition-all ${
                  plan.popular ? "pricing-popular" : ""
                }`}
                style={{
                  background: plan.popular
                    ? "var(--color-brand-green)"
                    : "white",
                  border: plan.popular
                    ? "none"
                    : "1px solid rgba(0,0,0,0.07)",
                  boxShadow: plan.popular
                    ? "0 0 0 2px var(--color-brand-green), 0 16px 40px rgba(45,106,79,0.15)"
                    : "0 2px 12px rgba(0,0,0,0.05)",
                }}
              >
                {/* Popular badge */}
                {plan.popular && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                    <div
                      className="px-4 py-1.5 rounded-full text-xs font-bold shadow-lg"
                      style={{
                        background: "var(--color-brand-gold)",
                        color: "white",
                        boxShadow: "0 4px 12px rgba(233,163,25,0.35)",
                      }}
                    >
                      {p.popularBadge}
                    </div>
                  </div>
                )}

                {/* Plan name + price */}
                <div>
                  <h3
                    className="text-lg font-bold mb-3"
                    style={{
                      color: plan.popular
                        ? "rgba(255,255,255,0.8)"
                        : "var(--color-text-muted)",
                      fontFamily: "var(--font-plus-jakarta), sans-serif",
                    }}
                  >
                    {plan.name}
                  </h3>
                  <div className="flex items-end gap-1 mb-1">
                    <span
                      className="text-5xl font-extrabold tracking-tight"
                      style={{
                        color: plan.popular ? "white" : "var(--color-text-primary)",
                        fontFamily: "var(--font-plus-jakarta), sans-serif",
                      }}
                    >
                      {plan.price}
                    </span>
                    <span
                      className="text-base mb-2 font-medium"
                      style={{
                        color: plan.popular
                          ? "rgba(255,255,255,0.6)"
                          : "var(--color-text-muted)",
                      }}
                    >
                      {plan.period}
                    </span>
                  </div>
                  <div
                    className="text-sm font-semibold"
                    style={{
                      color: plan.popular
                        ? "rgba(255,255,255,0.75)"
                        : "var(--color-brand-green)",
                    }}
                  >
                    {plan.revenue}
                  </div>
                  <div
                    className="text-sm mt-1"
                    style={{
                      color: plan.popular
                        ? "rgba(255,255,255,0.6)"
                        : "var(--color-text-muted)",
                    }}
                  >
                    {plan.sites}
                  </div>
                </div>

                {/* Divider */}
                <div
                  className="h-px w-full"
                  style={{
                    background: plan.popular
                      ? "rgba(255,255,255,0.15)"
                      : "rgba(0,0,0,0.06)",
                  }}
                />

                {/* Features */}
                <ul className="flex flex-col gap-3 flex-1">
                  {plan.features.map((feat: string, fi: number) => (
                    <li key={fi} className="flex items-start gap-3">
                      <div
                        className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
                        style={{
                          background: plan.popular
                            ? "rgba(255,255,255,0.2)"
                            : "rgba(45,106,79,0.1)",
                        }}
                      >
                        <Check
                          size={11}
                          strokeWidth={3}
                          style={{
                            color: plan.popular ? "white" : "var(--color-brand-green)",
                          }}
                        />
                      </div>
                      <span
                        className="text-sm leading-snug"
                        style={{
                          color: plan.popular
                            ? "rgba(255,255,255,0.85)"
                            : "var(--color-text-secondary)",
                        }}
                      >
                        {feat}
                      </span>
                    </li>
                  ))}
                </ul>

                {/* CTA */}
                <a
                  href={plan.ctaHref}
                  className="block text-center py-3.5 rounded-2xl font-bold text-sm no-underline transition-all btn-scale"
                  style={
                    plan.popular
                      ? {
                          background: "white",
                          color: "var(--color-brand-green)",
                          boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
                        }
                      : {
                          background: "var(--color-brand-green)",
                          color: "white",
                          boxShadow: "0 2px 8px rgba(45,106,79,0.2)",
                        }
                  }
                  onMouseEnter={(e) => {
                    if (!plan.popular) {
                      (e.currentTarget as HTMLAnchorElement).style.background =
                        "var(--color-brand-green-light)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!plan.popular) {
                      (e.currentTarget as HTMLAnchorElement).style.background =
                        "var(--color-brand-green)";
                    }
                  }}
                >
                  {plan.cta}
                </a>
              </div>
            </AnimateIn>
          ))}
        </div>
      </div>
    </section>
  );
}
