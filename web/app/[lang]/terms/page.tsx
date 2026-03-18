import Link from "next/link";
import { getDictionary, type Locale } from "../dictionaries";
import type { Metadata } from "next";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ lang: string }>;
}): Promise<Metadata> {
  const { lang } = await params;
  const dict = await getDictionary(lang as Locale);
  return { title: `${dict.footer.terms} — AbotKamay WiFi` };
}

export default async function TermsPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  const dict = await getDictionary(lang as Locale);

  return (
    <main className="min-h-screen bg-[var(--color-warm-white)] pt-24 pb-16">
      <div className="max-w-3xl mx-auto px-5 sm:px-8">
        <Link
          href={`/${lang}`}
          className="inline-flex items-center gap-1 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] no-underline mb-8 transition-colors"
        >
          ← {lang === "zh-hant" ? "返回首頁" : lang === "fil" ? "Bumalik sa Home" : "Back to Home"}
        </Link>

        <article className="prose prose-neutral max-w-none">
          <h1 className="text-3xl font-extrabold tracking-tight mb-2" style={{ color: "var(--color-brand-green)" }}>
            {dict.footer.terms}
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mb-8">Last Updated: March 17, 2026</p>

          <Section title="1. Acceptance of Terms">
            <p>By connecting to the Abot Kamay WiFi network, you acknowledge that you have read, understood, and agree to be bound by these Terms of Service. If you do not agree, do not connect to or use this network.</p>
          </Section>

          <Section title="2. Service Description">
            <p>Abot Kamay WiFi provides public internet access at designated venues. The service may be provided free of charge, on a time-credit basis, or subject to other usage conditions as displayed at the point of access.</p>
            <p>The Company is not a telecommunications carrier or ISP. Internet connectivity is sourced from licensed third-party providers. Internet speed, bandwidth, and availability may vary. No minimum speed or continuous availability is guaranteed.</p>
          </Section>

          <Section title="3. Session and Credit Terms">
            <ul>
              <li>Session credits are non-refundable once a session has commenced</li>
              <li>Interruptions do not automatically entitle credit restoration</li>
              <li>Unused session time is non-transferable and expires at session end</li>
              <li>Credits cannot be transferred between devices or users</li>
              <li>Pricing and duration may be adjusted without prior notice</li>
            </ul>
          </Section>

          <Section title="4. Acceptable Use Policy">
            <p><strong>Users are expressly prohibited from:</strong></p>
            <ul>
              <li>Unauthorized access to systems or data (hacking)</li>
              <li>Distributing malware, spyware, or harmful code</li>
              <li>Fraud, phishing, identity theft, or financial scams</li>
              <li>Illegal downloading or distribution of copyrighted content</li>
              <li>Child sexual abuse material (CSAM) or exploitation of minors</li>
              <li>Harassment, cyberbullying, or threats</li>
              <li>Content that violates Philippine law</li>
              <li>Operating unauthorized proxies, VPN resale, or network exploitation</li>
              <li>Activities that disrupt or overload network infrastructure</li>
            </ul>
            <p>Violations result in immediate termination and may be reported to law enforcement.</p>
          </Section>

          <Section title="5. Device and Security">
            <p>Users are solely responsible for their device security. The Company is not responsible for malware, device loss/theft, or unauthorized access to user accounts via the network.</p>
            <p><strong>Avoid transmitting sensitive information (passwords, banking credentials) over public WiFi. Use a VPN for sensitive communications.</strong></p>
          </Section>

          <Section title="6. Advertising">
            <p>Users may be required to view advertisements before or during sessions. By using this service, you consent to the display of advertisements. The Company is not responsible for third-party ad content.</p>
          </Section>

          <Section title="7. Network Limitations">
            <ul>
              <li>Access may be interrupted without advance notice</li>
              <li>Bandwidth may be throttled during high-usage periods</li>
              <li>Access may be suspended for maintenance or security</li>
              <li>Data usage caps or fair-use policies may apply</li>
            </ul>
            <p>No warranty or service level guarantee is provided.</p>
          </Section>

          <Section title="8. Prohibited Resale">
            <p>Session access is for individual users only. Reselling, rebroadcasting, or tampering with hardware is prohibited and may result in legal action.</p>
          </Section>

          <Section title="9. Liability Disclaimer">
            <p>To the fullest extent permitted by law, Abot Kamay WiFi disclaims liability for: data loss/theft, security breaches, content accessed via the network, third-party transactions, or loss of business/profits. <strong>Use at your own risk.</strong></p>
          </Section>

          <Section title="10. Law Enforcement">
            <p>The Company cooperates with lawful requests from Philippine law enforcement, NTC, and government authorities. Network logs may be disclosed when required by law.</p>
          </Section>

          <Section title="11. Minors">
            <p>This service is not intended for users under 18 without parental consent. By connecting, you confirm you are 18+ or have guardian consent.</p>
          </Section>

          <Section title="12. Modifications">
            <p>These Terms may be amended at any time. Continued use after posting constitutes acceptance.</p>
          </Section>

          <Section title="13. Governing Law">
            <p>These Terms are governed by the laws of the Republic of the Philippines. Disputes are subject to the exclusive jurisdiction of Philippine courts.</p>
          </Section>

          <Section title="14. Contact">
            <p><strong>Abot Kamay Digital Inc.</strong><br />Email: support@abotkamay.net</p>
          </Section>

          <p className="text-xs text-[var(--color-text-muted)] mt-12 pt-6 border-t border-[#e8e4de]">
            Abot Kamay Digital Inc. | Governed by the laws of the Republic of the Philippines
          </p>
        </article>
      </div>
    </main>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-8">
      <h2 className="text-xl font-bold mb-3 text-[var(--color-text-primary)]">{title}</h2>
      <div className="text-[var(--color-text-secondary)] leading-relaxed space-y-2">{children}</div>
    </section>
  );
}
