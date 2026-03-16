import { getDictionary, type Locale, locales } from "./dictionaries";
import Header from "./components/Header";
import Hero from "./components/Hero";
import HowItWorks from "./components/HowItWorks";
import WhyItMatters from "./components/WhyItMatters";
import Stories from "./components/Stories";
import Coverage from "./components/Coverage";
import Advertising from "./components/Advertising";
import Vision from "./components/Vision";
import Contact from "./components/Contact";
import Footer from "./components/Footer";
import SectionDivider from "./components/SectionDivider";

export async function generateStaticParams() {
  return locales.map((lang) => ({ lang }));
}

export default async function LandingPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  const dict = await getDictionary(lang as Locale);

  return (
    <>
      <Header dict={dict} lang={lang} />
      <main>
        <Hero dict={dict} />
        <SectionDivider />
        <HowItWorks dict={dict} />
        <SectionDivider flip />
        <WhyItMatters dict={dict} />
        <Stories dict={dict} />
        <Coverage dict={dict} lang={lang} />
        <Advertising dict={dict} />
        <Vision dict={dict} />
        <Contact dict={dict} />
      </main>
      <Footer dict={dict} lang={lang} />
    </>
  );
}
