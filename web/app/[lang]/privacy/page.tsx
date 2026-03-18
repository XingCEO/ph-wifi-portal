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
  return { title: `${dict.footer.privacy} — AbotKamay WiFi` };
}

export default async function PrivacyPage({
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
            {dict.footer.privacy}
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mb-8">Last Updated: March 17, 2026</p>

          {lang === "fil" && (
            <div className="bg-[var(--color-warm-gray)] rounded-xl p-4 mb-8 text-sm">
              <strong>Buod sa Filipino:</strong> Kapag ginamit mo ang aming libreng WiFi, nangongolekta kami ng ilang teknikal na impormasyon para mapatakbo ang serbisyo. Hindi namin ibinebenta ang iyong personal na data. Pinapanatili namin ang mga log sa loob ng hanggang 6 na buwan. Mayroon kang mga karapatan sa iyong data.
            </div>
          )}
          {lang === "zh-hant" && (
            <div className="bg-[var(--color-warm-gray)] rounded-xl p-4 mb-8 text-sm">
              <strong>摘要：</strong>使用我們的免費 WiFi 時，我們會收集基本技術資訊（裝置 ID、觀看的廣告）以維運服務。我們不會將您的個人資料出售給第三方。記錄保留最多 6 個月。您對自己的資料擁有權利。
            </div>
          )}

          <Section title="1. Who We Are">
            <p>Abot Kamay Digital Inc. (&ldquo;AKD&rdquo;) is a One Person Corporation registered in the Philippines that operates a free WiFi advertising network at various partner locations across the Philippines.</p>
            <p>AKD is the Personal Information Controller (PIC) responsible for your personal data collected through the Platform, as defined under Republic Act No. 10173 (Data Privacy Act of 2012).</p>
            <p><strong>Data Protection Officer:</strong> privacy@abotkamay.net</p>
          </Section>

          <Section title="2. What Data We Collect">
            <table className="w-full text-sm">
              <thead><tr><th className="text-left">Data Type</th><th className="text-left">When Collected</th></tr></thead>
              <tbody>
                <tr><td>Device MAC Address</td><td>When you connect</td></tr>
                <tr><td>Assigned IP Address</td><td>When you connect</td></tr>
                <tr><td>Session Data (time, duration, data volume)</td><td>During each session</td></tr>
                <tr><td>Ad Interaction Data</td><td>During ad viewing</td></tr>
                <tr><td>Device Type &amp; OS</td><td>When you connect</td></tr>
                <tr><td>Mobile / Email (optional)</td><td>Only if you register</td></tr>
              </tbody>
            </table>
            <p className="mt-3"><strong>We do NOT collect:</strong> your name, national ID, banking information, precise location, browsing history after connection, or app usage data.</p>
          </Section>

          <Section title="3. Why We Collect Your Data">
            <ul>
              <li>Providing WiFi access after ad viewing</li>
              <li>Fraud prevention and security monitoring</li>
              <li>Billing advertisers (anonymized aggregate counts)</li>
              <li>Compliance with Philippine law</li>
            </ul>
          </Section>

          <Section title="4. How Long We Keep Your Data">
            <ul>
              <li><strong>Connection Logs:</strong> 180 days (up to 12 months if required by law)</li>
              <li><strong>Ad Interaction Data:</strong> 24 months</li>
              <li><strong>Registration Data:</strong> Duration of account + 12 months</li>
              <li><strong>Security Incident Records:</strong> 5 years</li>
            </ul>
          </Section>

          <Section title="5. Who We Share Your Data With">
            <p>We do <strong>not</strong> sell personal data to third parties for marketing. We may share limited data with:</p>
            <ul>
              <li><strong>Advertisers:</strong> Aggregate, anonymized data only</li>
              <li><strong>Cloud providers:</strong> Securely stored platform data</li>
              <li><strong>Law enforcement:</strong> When required by lawful order (RA 10175)</li>
              <li><strong>NPC:</strong> Breach notifications, compliance reports</li>
            </ul>
            <p>Venue Partners do <strong>not</strong> receive any personal data from the Platform.</p>
          </Section>

          <Section title="6. Children&rsquo;s Privacy">
            <p>We do not knowingly collect personal data from children under 13 without verifiable parental consent. Contact privacy@abotkamay.net for deletion requests.</p>
          </Section>

          <Section title="7. Your Rights Under RA 10173">
            <ul>
              <li><strong>Right to be Informed</strong> — know what data we collect and why</li>
              <li><strong>Right of Access</strong> — request a copy of your data</li>
              <li><strong>Right to Rectification</strong> — correct inaccurate data</li>
              <li><strong>Right to Erasure</strong> — request deletion (subject to legal retention)</li>
              <li><strong>Right to Object</strong> — object to processing on legitimate grounds</li>
              <li><strong>Right to Data Portability</strong> — receive data in machine-readable format</li>
            </ul>
            <p>Contact: privacy@abotkamay.net — we respond within 15 business days.</p>
            <p>NPC complaints: info@privacy.gov.ph | (02) 8234-2228</p>
          </Section>

          <Section title="8. Data Security">
            <p>We implement encryption in transit (TLS/HTTPS), access controls, regular security assessments, and staff training. No system is 100% secure.</p>
          </Section>

          <Section title="9. Cookies">
            <p>Our portal uses session cookies only to maintain your session and track ad completion. We do not use cross-site tracking or third-party advertising pixels.</p>
          </Section>

          <Section title="10. Changes to This Policy">
            <p>Material changes will be notified via the portal. Continued use constitutes acceptance.</p>
          </Section>

          <Section title="11. Contact">
            <p><strong>Abot Kamay Digital Inc.</strong><br />Email: privacy@abotkamay.net</p>
          </Section>

          <p className="text-xs text-[var(--color-text-muted)] mt-12 pt-6 border-t border-[#e8e4de]">
            AKD-POL-004 Version 1.0 | Abot Kamay Digital Inc. | Compliant with RA 10173 (Data Privacy Act of 2012)
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
