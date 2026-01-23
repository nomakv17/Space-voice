"use client";

import {
  Navbar,
  HeroSection,
  SocialProofBar,
  ProblemSolutionSection,
  HowItWorksSection,
  DifferentiationSection,
  FeaturesGrid,
  UseCasesSection,
  ROICalculator,
  PricingPreview,
  CaseStudiesSection,
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
      <ROICalculator />
      <ProblemSolutionSection />
      <DifferentiationSection />
      <HowItWorksSection />
      <section id="features">
        <FeaturesGrid />
      </section>
      <section id="use-cases">
        <UseCasesSection />
      </section>
      <CaseStudiesSection />
      <PricingPreview />
      <TestimonialsSection />
      <section id="faq">
        <FAQSection />
      </section>
      <FooterSection />
    </main>
  );
}
