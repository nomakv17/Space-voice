"use client";

import { Check, Sparkles, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

const pricingPlans = [
  {
    name: "Starter",
    description: "Perfect for small businesses just getting started",
    bestFor: "Best for 1-2 techs and low call volume",
    price: 99,
    minutes: 500,
    features: [
      "500 minutes/month",
      "1 AI voice agent",
      "Basic call analytics",
      "Email support",
      "Google Calendar integration",
    ],
    cta: "Start Free Trial",
    popular: false,
  },
  {
    name: "Growth",
    description: "For growing businesses ready to scale",
    bestFor: "Best for 3-10 techs and steady inbound calls",
    price: 249,
    minutes: 2500,
    features: [
      "2,500 minutes/month",
      "3 AI voice agents",
      "Advanced analytics & transcripts",
      "Priority support",
      "CRM integrations (HubSpot, etc.)",
      "Emergency triage protocols",
      "Human handoff",
    ],
    cta: "Start Free Trial",
    popular: true,
  },
  {
    name: "Enterprise",
    description: "Custom solutions for large operations",
    bestFor: "Best for multi‑location teams and complex workflows",
    price: null,
    minutes: null,
    features: [
      "Unlimited minutes",
      "Unlimited AI agents",
      "Custom AI training",
      "Dedicated account manager",
      "API access",
      "Custom integrations",
      "SLA guarantee",
      "White-labeling available",
    ],
    cta: "Book Demo",
    popular: false,
  },
];

export function PricingPreview() {
  return (
    <section id="pricing" className="relative py-24 bg-gray-50">
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-gray-200 text-gray-600 text-sm font-medium mb-6 shadow-sm">
            Transparent Pricing
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
            Simple Pricing,{" "}
            <span className="bg-gradient-to-r from-cyan-600 to-purple-600 bg-clip-text text-transparent">
              Massive ROI
            </span>
          </h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            No hidden fees. No per-call charges. Just straightforward pricing that scales with your business.
          </p>
        </div>

        {/* Pricing cards */}
        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {pricingPlans.map((plan, index) => (
            <div
              key={index}
              className={cn(
                "relative rounded-2xl p-8 transition-all duration-300",
                plan.popular
                  ? "bg-gradient-to-br from-cyan-50 to-purple-50 border-2 border-cyan-400 shadow-xl shadow-cyan-500/10 md:scale-105"
                  : "bg-white border border-gray-200 hover:border-gray-300 hover:shadow-lg"
              )}
            >
              {/* Popular badge */}
              {plan.popular && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-gradient-to-r from-cyan-600 to-purple-600 text-white text-sm font-semibold flex items-center gap-1">
                  <Sparkles className="w-4 h-4" />
                  Most Popular
                </div>
              )}

              {/* Plan name */}
              <h3 className="text-xl font-bold text-gray-900 mb-2">{plan.name}</h3>
              <p className="text-gray-600 text-sm mb-3">{plan.description}</p>
              <p className="text-xs text-gray-500 mb-6">{plan.bestFor}</p>

              {/* Price */}
              <div className="mb-6">
                {plan.price !== null ? (
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-bold text-gray-900">${plan.price}</span>
                    <span className="text-gray-600">/month</span>
                  </div>
                ) : (
                  <div className="text-4xl font-bold text-gray-900">Custom</div>
                )}
                {plan.minutes && (
                  <p className="text-sm text-gray-500 mt-1">{plan.minutes.toLocaleString()} minutes included</p>
                )}
              </div>

              {/* Features */}
              <ul className="space-y-3 mb-8">
                {plan.features.map((feature, featureIndex) => (
                  <li key={featureIndex} className="flex items-center gap-3">
                    <div className={cn(
                      "flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center",
                      plan.popular ? "bg-cyan-100 text-cyan-600" : "bg-gray-100 text-gray-600"
                    )}>
                      <Check className="w-3 h-3" />
                    </div>
                    <span className="text-gray-700 text-sm">{feature}</span>
                  </li>
                ))}
              </ul>

              {/* CTA */}
              <a
                href={
                  plan.price !== null
                    ? "https://dashboard.spacevoice.ai/signup"
                    : "https://calendly.com/tai-alabi/spacevoice-demo"
                }
                className={cn(
                  "flex items-center justify-center gap-2 w-full py-3 rounded-xl font-semibold transition-all duration-300",
                  plan.popular
                    ? "bg-gradient-to-r from-cyan-600 to-cyan-500 text-white hover:shadow-lg hover:shadow-cyan-500/25"
                    : "bg-gray-100 text-gray-900 hover:bg-gray-200"
                )}
              >
                {plan.cta}
                <ArrowRight className="w-4 h-4" />
              </a>
            </div>
          ))}
        </div>

        {/* Bottom notes */}
        <div className="mt-12 text-center">
          <p className="text-gray-500 text-sm mb-4">
            All plans include 30-day money-back guarantee. Cancel anytime.
          </p>
          <a
            href="https://dashboard.spacevoice.ai/dashboard/pricing"
            className="text-cyan-600 hover:text-cyan-700 text-sm font-medium inline-flex items-center gap-1"
          >
            See detailed pricing comparison
            <ArrowRight className="w-4 h-4" />
          </a>
        </div>
      </div>
    </section>
  );
}
