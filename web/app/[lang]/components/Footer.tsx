import Link from "next/link";
import type { Dictionary } from "../dictionaries";

export default function Footer({
  dict,
  lang,
}: {
  dict: Dictionary;
  lang: string;
}) {
  const year = new Date().getFullYear();

  return (
    <footer className="bg-[var(--color-text-primary)] text-white/60 pt-16 pb-8">
      <div className="max-w-6xl mx-auto px-5 sm:px-8">
        <div className="grid sm:grid-cols-3 gap-10 mb-14">
          {/* Brand */}
          <div>
            <Link
              href={`/${lang}`}
              className="inline-block text-xl font-800 text-white no-underline mb-3"
              style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
            >
              Abot<span className="text-[var(--color-brand-green-light)]">Kamay</span>
            </Link>
            <p className="text-sm leading-relaxed">
              {dict.footer.tagline}
            </p>
          </div>

          {/* Navigation */}
          <div>
            <h4 className="text-white text-sm font-semibold mb-4 uppercase tracking-wider">
              {lang === "fil" ? "Mga Link" : lang === "zh-hant" ? "快速連結" : "Quick Links"}
            </h4>
            <nav className="flex flex-col gap-2.5">
              <a href="#how-it-works" className="text-sm hover:text-white transition-colors no-underline">
                {dict.nav.howItWorks}
              </a>
              <a href="#why" className="text-sm hover:text-white transition-colors no-underline">
                {dict.nav.about}
              </a>
              <a href="#advertising" className="text-sm hover:text-white transition-colors no-underline">
                {dict.nav.advertise}
              </a>
              <a href="#contact" className="text-sm hover:text-white transition-colors no-underline">
                {dict.nav.contact}
              </a>
            </nav>
          </div>

          {/* Contact */}
          <div>
            <h4 className="text-white text-sm font-semibold mb-4 uppercase tracking-wider">
              {dict.contact.label}
            </h4>
            <a
              href={`mailto:${dict.contact.email}`}
              className="text-sm hover:text-white transition-colors no-underline"
            >
              {dict.contact.email}
            </a>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="border-t border-white/8 pt-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-xs text-white/30">
            &copy; {year} {dict.footer.copyright}
          </p>
          <div className="flex items-center gap-1">
            {[
              { code: "en", label: "EN" },
              { code: "fil", label: "FIL" },
              { code: "zh-hant", label: "中文" },
            ].map((l) => (
              <Link
                key={l.code}
                href={`/${l.code}`}
                className={`text-xs px-2.5 py-1 rounded-md transition-colors no-underline ${
                  lang === l.code
                    ? "bg-white/10 text-white"
                    : "text-white/30 hover:text-white/60"
                }`}
              >
                {l.label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}
