import Link from "next/link";
import { Wifi, Facebook, Twitter, Instagram, Linkedin, Mail } from "lucide-react";
import type { Dictionary } from "../dictionaries";

export default function Footer({
  dict,
  lang,
}: {
  dict: Dictionary;
  lang: string;
}) {
  const year = new Date().getFullYear();

  const socialLinks = [
    { Icon: Facebook, href: "https://facebook.com/abotkamay", label: "Facebook" },
    { Icon: Twitter, href: "https://twitter.com/abotkamay", label: "Twitter" },
    { Icon: Instagram, href: "https://instagram.com/abotkamay", label: "Instagram" },
    { Icon: Linkedin, href: "https://linkedin.com/company/abotkamay", label: "LinkedIn" },
  ];

  return (
    <footer className="bg-[var(--color-text-primary)] text-white/60 pt-16 pb-8">
      <div className="max-w-6xl mx-auto px-5 sm:px-8">
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-10 mb-14">
          {/* Brand */}
          <div className="lg:col-span-1">
            <Link
              href={`/${lang}`}
              className="inline-flex items-center gap-2 mb-4 no-underline group"
              style={{ fontFamily: "var(--font-plus-jakarta), sans-serif" }}
            >
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                style={{ background: "#0099DB" }}
              >
                <Wifi size={15} color="white" strokeWidth={2.5} />
              </div>
              <span className="text-xl font-extrabold text-white tracking-tight">
                Abot<span style={{ color: "#F58220" }}>Kamay</span>
              </span>
            </Link>
            <p className="text-sm leading-relaxed mb-6">
              {dict.footer.tagline}
            </p>
            {/* Social icons */}
            <div className="flex items-center gap-3">
              {socialLinks.map(({ Icon, href, label }) => (
                <a
                  key={label}
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={label}
                  className="footer-social-icon w-8 h-8 rounded-lg flex items-center justify-center transition-all no-underline"
                >
                  <Icon size={14} style={{ color: "rgba(255,255,255,0.6)" }} />
                </a>
              ))}
            </div>
          </div>

          {/* Product links */}
          <div>
            <h4 className="text-white text-sm font-semibold mb-4 uppercase tracking-wider">
              {dict.footer.quickLinks}
            </h4>
            <nav className="flex flex-col gap-2.5">
              {[
                { href: "#how-it-works", label: dict.nav.howItWorks },
                { href: "#why", label: dict.nav.about },
                { href: "#advertising", label: dict.nav.advertise },
                { href: "#pricing", label: dict.footer.pricing },
                { href: "#contact", label: dict.nav.contact },
              ].map((item) => (
                <a
                  key={item.href}
                  href={item.href}
                  className="text-sm hover:text-white transition-colors no-underline link-underline w-fit"
                >
                  {item.label}
                </a>
              ))}
            </nav>
          </div>

          {/* Legal */}
          <div>
            <h4 className="text-white text-sm font-semibold mb-4 uppercase tracking-wider">
              {dict.footer.legal}
            </h4>
            <nav className="flex flex-col gap-2.5">
              <a href="/privacy" className="text-sm hover:text-white transition-colors no-underline link-underline w-fit">
                {dict.footer.privacy}
              </a>
              <a href="/terms" className="text-sm hover:text-white transition-colors no-underline link-underline w-fit">
                {dict.footer.terms}
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
              className="inline-flex items-center gap-2 text-sm hover:text-white transition-colors no-underline group"
            >
              <Mail size={14} className="flex-shrink-0" />
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
