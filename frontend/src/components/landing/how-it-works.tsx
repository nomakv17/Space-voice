"use client";

import { Settings, PhoneForwarded, Rocket, ArrowRight, Check } from "lucide-react";

const steps = [
  {
    number: "01",
    icon: Settings,
    title: "Configure Your Agent",
    description: "Set up your business details, services, pricing, and booking preferences. Train your AI on your specific HVAC terminology and workflows.",
    features: ["Custom voice & personality", "Service catalog setup", "Pricing configuration", "Calendar integration"],
    color: "cyan",
  },
  {
    number: "02",
    icon: PhoneForwarded,
    title: "Connect Your Phone",
    description: "Forward your business line to SpaceVoice or get a dedicated local number. Works with any existing phone system.",
    features: ["Keep your existing number", "Get a new local number", "Forward after-hours only", "Instant setup"],
    color: "purple",
  },
  {
    number: "03",
    icon: Rocket,
    title: "Start Converting",
    description: "Your AI agent immediately starts handling calls, booking appointments, and escalating emergencies—24/7/365.",
    features: ["Real-time call handling", "Automatic appointment booking", "Emergency escalation", "Full call transcripts"],
    color: "green",
  },
];

const colorVariants = {
  cyan: {
    bg: "bg-cyan-50",
    border: "border-cyan-200",
    text: "text-cyan-600",
    gradient: "from-cyan-50 to-white",
  },
  purple: {
    bg: "bg-purple-50",
    border: "border-purple-200",
    text: "text-purple-600",
    gradient: "from-purple-50 to-white",
  },
  green: {
    bg: "bg-green-50",
    border: "border-green-200",
    text: "text-green-600",
    gradient: "from-green-50 to-white",
  },
};

export function HowItWorksSection() {
  return (
    <section className="relative py-24 bg-gray-50">
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-gray-200 text-gray-600 text-sm font-medium mb-6 shadow-sm">
            Simple Setup
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
            Get Started in{" "}
            <span className="bg-gradient-to-r from-cyan-600 to-purple-600 bg-clip-text text-transparent">
              3 Easy Steps
            </span>
          </h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Most businesses are up and running within 24 hours. No technical expertise required.
          </p>
        </div>

        {/* Steps */}
        <div className="relative">
          {/* Connection line (desktop only) */}
          <div className="hidden lg:block absolute top-32 left-1/2 -translate-x-1/2 w-[70%] h-0.5 bg-gradient-to-r from-cyan-300 via-purple-300 to-green-300" />

          <div className="grid md:grid-cols-3 gap-8">
            {steps.map((step, index) => {
              const Icon = step.icon;
              const colors = colorVariants[step.color as keyof typeof colorVariants];

              return (
                <div key={index} className="relative group">
                  {/* Step card */}
                  <div className={`h-full p-8 rounded-2xl bg-gradient-to-br ${colors.gradient} border ${colors.border} hover:shadow-xl transition-all duration-300`}>
                    {/* Step number */}
                    <div className={`inline-flex items-center justify-center w-16 h-16 rounded-2xl ${colors.bg} ${colors.text} text-2xl font-bold mb-6`}>
                      {step.number}
                    </div>

                    {/* Icon badge */}
                    <div className={`absolute top-6 right-6 w-12 h-12 rounded-xl ${colors.bg} flex items-center justify-center`}>
                      <Icon className={`w-6 h-6 ${colors.text}`} />
                    </div>

                    {/* Content */}
                    <h3 className="text-xl font-bold text-gray-900 mb-3">{step.title}</h3>
                    <p className="text-gray-600 mb-6">{step.description}</p>

                    {/* Features list */}
                    <ul className="space-y-2">
                      {step.features.map((feature, featureIndex) => (
                        <li key={featureIndex} className="flex items-center gap-2 text-sm text-gray-700">
                          <Check className={`w-4 h-4 ${colors.text}`} />
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Arrow connector (mobile/tablet) */}
                  {index < steps.length - 1 && (
                    <div className="md:hidden flex justify-center my-4">
                      <ArrowRight className="w-6 h-6 text-gray-400 rotate-90" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Bottom CTA */}
        <div className="mt-16 text-center">
          <p className="text-gray-600 mb-6">
            Ready to transform your phone operations?
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a
              href="https://dashboard.spacevoice.ai/signup"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 rounded-xl bg-gradient-to-r from-cyan-600 to-cyan-500 text-white font-semibold text-lg hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300"
            >
              Get Started
              <ArrowRight className="w-5 h-5" />
            </a>
            <a
              href="/dashboard/pricing"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 rounded-xl border-2 border-gray-200 text-gray-700 font-semibold text-lg hover:bg-gray-50 hover:border-gray-300 transition-all duration-300"
            >
              View Pricing
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
