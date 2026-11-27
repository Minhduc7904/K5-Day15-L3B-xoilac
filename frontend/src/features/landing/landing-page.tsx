import { Footer } from '@/components/layout/footer';
import { Navbar } from '@/components/layout/navbar';
import { NavAuthActions } from './auth-actions';
import { landingLinks } from './content';
import { Hero } from './hero';
import { ChapterMarquee, Faq, Features, FinalCta, HowItWorks, Problems, Promises } from './sections';

export function LandingPage() {
  return (
    <>
      <Navbar links={landingLinks} actions={<NavAuthActions />} />
      <main id="noi-dung">
        <Hero />
        <ChapterMarquee />
        <Problems />
        <HowItWorks />
        <Features />
        <Promises />
        <Faq />
        <FinalCta />
      </main>
      <Footer links={landingLinks} />
    </>
  );
}
