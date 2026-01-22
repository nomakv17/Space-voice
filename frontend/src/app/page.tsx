"use client";

import {
  Navbar,
  HeroSection,
  SocialProofBar,
  ProblemSolutionSection,
  HowItWorksSection,
  FeaturesGrid,
  UseCasesSection,
  ROICalculator,
  PricingPreview,
  TestimonialsSection,
  FAQSection,
  FooterSection,
} from "@/components/landing";

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-white">
      <Navbar />
      <HeroSection />
      <SocialProofBar />
      <ProblemSolutionSection />
      <HowItWorksSection />
      <section id="features">
        <FeaturesGrid />
      </section>
      <section id="use-cases">
        <UseCasesSection />
      </section>
      <ROICalculator />
      <PricingPreview />
      <TestimonialsSection />
      <section id="faq">
        <FAQSection />
      </section>
      <FooterSection />
    </main>
  );
}
