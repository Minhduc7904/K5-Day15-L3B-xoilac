import { Footer } from '@/components/layout/footer';
import { Navbar } from '@/components/layout/navbar';
import { UserMenu } from '@/features/auth/components/user-menu';
import { landingLinks } from './content';
import { Hero } from './hero';
import { ChapterMarquee, Faq, Features, HowItWorks, Problems, Promises } from './sections';

export function LandingPage() {
  return (
    <>
      <Navbar links={landingLinks} actions={<UserMenu />} />
      <main id="noi-dung">
        <Hero />
        <ChapterMarquee />
        <Problems />
        <HowItWorks />
        <Features />
        <Promises />
        <Faq />
      </main>
      <Footer links={landingLinks} />
    </>
  );
}
