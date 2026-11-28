import { Footer } from '@/components/layout/footer';
import { Navbar } from '@/components/layout/navbar';
import { UserMenu } from '@/features/auth/components/user-menu';
import { AgentCapabilities } from './agent-capabilities';
import { AnalyticsPreview } from './analytics-preview';
import { landingLinks } from './content';
import { Hero } from './hero';
import { QuestionBank } from './question-bank';
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
        <AgentCapabilities />
        <QuestionBank />
        <AnalyticsPreview />
        <Features />
        <Promises />
        <Faq />
      </main>
      <Footer links={landingLinks} />
    </>
  );
}
