"use client";

import { Store, Building2, Bus, TreePalm, Coffee, ShoppingBag } from "lucide-react";
import AnimateIn from "./AnimateIn";
import type { Dictionary } from "../dictionaries";

const locations = [
  { icon: Store, labelEn: "Sari-sari Stores", labelFil: "Mga Sari-sari Store", labelZh: "雜貨店" },
  { icon: Coffee, labelEn: "Cafés & Restaurants", labelFil: "Mga Café at Restaurant", labelZh: "咖啡廳與餐廳" },
  { icon: Building2, labelEn: "Community Centers", labelFil: "Mga Community Center", labelZh: "社區中心" },
  { icon: Bus, labelEn: "Transport Hubs", labelFil: "Mga Transport Hub", labelZh: "交通樞紐" },
  { icon: TreePalm, labelEn: "Public Spaces", labelFil: "Mga Pampublikong Lugar", labelZh: "公共空間" },
  { icon: ShoppingBag, labelEn: "Markets & Malls", labelFil: "Mga Palengke at Mall", labelZh: "市場與商場" },
];

const labelMap: Record<string, "labelEn" | "labelFil" | "labelZh"> = {
  en: "labelEn",
  fil: "labelFil",
  "zh-hant": "labelZh",
};

export default function Coverage({ dict, lang }: { dict: Dictionary; lang: string }) {
  const labelKey = labelMap[lang] || "labelEn";

  return (
    <section className="py-24 sm:py-32 bg-[var(--color-warm-gray)]/50">
      <div className="max-w-6xl mx-auto px-5 sm:px-8">
        <div className="text-center mb-14">
          <AnimateIn>
            <p className="text-sm font-semibold text-[var(--color-brand-green)] tracking-wide uppercase mb-3">
              {lang === "fil" ? "Saan Kami Matatagpuan" : lang === "zh-hant" ? "部署地點" : "Where We Are"}
            </p>
          </AnimateIn>
          <AnimateIn delay={0.1}>
            <h2
              className="text-3xl sm:text-4xl font-800 tracking-tight mb-4"
              style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
            >
              {lang === "fil"
                ? "WiFi kung saan ka man naroroon"
                : lang === "zh-hant"
                ? "在你所到之處，都有 WiFi"
                : "WiFi wherever you are"}
            </h2>
          </AnimateIn>
          <AnimateIn delay={0.2}>
            <p className="text-lg text-[var(--color-text-secondary)] max-w-xl mx-auto">
              {lang === "fil"
                ? "Nagde-deploy kami ng mga hotspot sa mga lugar kung saan pinaka-kailangan ng mga tao ang connectivity."
                : lang === "zh-hant"
                ? "我們在人們最需要連線的地方部署熱點。"
                : "We deploy hotspots in the places where people need connectivity the most."}
            </p>
          </AnimateIn>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 sm:gap-5 max-w-3xl mx-auto">
          {locations.map((loc, i) => {
            const Icon = loc.icon;
            return (
              <AnimateIn key={loc.labelEn} delay={0.1 + i * 0.06}>
                <div className="flex flex-col items-center gap-3 p-6 sm:p-8 rounded-2xl bg-white border border-[#eae6e0] hover:border-[var(--color-brand-green)]/20 hover:shadow-lg hover:shadow-[var(--color-brand-green)]/[0.04] transition-all duration-300 hover:-translate-y-1 group">
                  <div className="w-12 h-12 rounded-xl bg-[var(--color-brand-green)]/6 flex items-center justify-center group-hover:bg-[var(--color-brand-green)]/10 transition-colors">
                    <Icon
                      size={24}
                      className="text-[var(--color-brand-green)]"
                      strokeWidth={1.5}
                    />
                  </div>
                  <span className="text-sm font-semibold text-[var(--color-text-primary)] text-center leading-tight">
                    {loc[labelKey]}
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
