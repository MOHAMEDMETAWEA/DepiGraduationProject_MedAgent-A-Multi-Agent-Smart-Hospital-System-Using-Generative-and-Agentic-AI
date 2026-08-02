import { LandingNav } from "@/components/landing/landing-nav";
import { Hero } from "@/components/landing/hero";
import { SocialProof } from "@/components/landing/social-proof";
import { HowItWorks } from "@/components/landing/how-it-works";
import { TriageLevels } from "@/components/landing/triage-levels";
import { FeatureGrid } from "@/components/landing/feature-grid";
import { SafetySection } from "@/components/landing/safety-section";
import { FinalCta } from "@/components/landing/final-cta";
import { LandingFooter } from "@/components/landing/landing-footer";

export default function HomePage() {
  return (
    <div className="relative flex min-h-screen flex-col">
      <LandingNav />
      <main className="flex-1">
        <Hero />
        <SocialProof />
        <HowItWorks />
        <TriageLevels />
        <FeatureGrid />
        <SafetySection />
        <FinalCta />
      </main>
      <LandingFooter />
    </div>
  );
}
