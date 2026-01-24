"use client";

import { useState } from "react";
import { Thermometer, Droplets, Zap, Hammer, Check, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

const useCases = [
  {
    id: "hvac",
    icon: Thermometer,
    title: "HVAC Contractors",
    tagline: "Keep customers cool when it matters most",
    description: "Handle AC emergencies, schedule maintenance calls, and qualify leads - all automatically. Your AI knows the difference between 'AC not working' and 'my house is 95 degrees.'",
    features: [
      "Emergency triage for no-AC situations",
      "Seasonal maintenance reminders",
      "Equipment age qualification",
      "Service plan upselling",
      "After-hours emergency dispatch",
    ],
    stats: {
      metric: "73%",
      label: "reduction in missed after-hours calls",
    },
    color: "cyan",
  },
  {
    id: "plumbing",
    icon: Droplets,
    title: "Plumbers",
    tagline: "Turn water emergencies into loyal customers",
    description: "Burst pipes can't wait. Your AI immediately identifies flooding situations, dispatches emergency crews, and handles routine scheduling for non-urgent work.",
    features: [
      "Flood/burst pipe emergency detection",
      "Water heater troubleshooting",
      "Drain cleaning scheduling",
      "Permit requirement guidance",
      "Insurance claim assistance",
    ],
    stats: {
      metric: "$8,500",
      label: "average monthly revenue recovered",
    },
    color: "blue",
  },
  {
    id: "electrical",
    icon: Zap,
    title: "Electricians",
    tagline: "Safety-first conversations, every time",
    description: "Electrical issues require careful screening. Your AI asks the right safety questions, identifies dangerous situations, and schedules routine work appropriately.",
    features: [
      "Safety hazard screening",
      "Panel upgrade qualification",
      "Generator installation inquiries",
      "EV charger consultations",
      "Emergency power outage response",
    ],
    stats: {
      metric: "45%",
      label: "increase in qualified leads",
    },
    color: "amber",
  },
  {
    id: "general",
    icon: Hammer,
    title: "General Contractors",
    tagline: "Qualify projects before you arrive",
    description: "Stop wasting time on tire-kickers. Your AI gathers project scope, budget expectations, and timeline requirements before you ever pick up the phone.",
    features: [
      "Project scope collection",
      "Budget qualification",
      "Timeline assessment",
      "Photo/document collection",
      "Estimate request processing",
    ],
    stats: {
      metric: "60%",
      label: "reduction in unqualified site visits",
    },
    color: "purple",
  },
];

const colorVariants = {
  cyan: {
    bg: "bg-cyan-50",
    border: "border-cyan-300",
    text: "text-cyan-600",
    activeBg: "bg-cyan-100",
  },
  blue: {
    bg: "bg-blue-50",
    border: "border-blue-300",
    text: "text-blue-600",
    activeBg: "bg-blue-100",
  },
  amber: {
    bg: "bg-amber-50",
    border: "border-amber-300",
    text: "text-amber-600",
    activeBg: "bg-amber-100",
  },
  purple: {
    bg: "bg-purple-50",
    border: "border-purple-300",
    text: "text-purple-600",
    activeBg: "bg-purple-100",
  },
};

const defaultUseCase = useCases[0] ?? {
  id: "hvac",
  icon: Thermometer,
  title: "HVAC Contractors",
  tagline: "",
  description: "",
  features: [],
  stats: { metric: "", label: "" },
  color: "cyan",
};

export function UseCasesSection() {
  const [activeCase, setActiveCase] = useState(defaultUseCase.id);

  const currentCase = useCases.find((c) => c.id === activeCase) ?? defaultUseCase;
  const colors = colorVariants[currentCase.color as keyof typeof colorVariants];
  const Icon = currentCase.icon;

  return (
    <section className="relative py-24 bg-gray-50">
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-gray-200 text-gray-600 text-sm font-medium mb-6 shadow-sm">
            Industry Solutions
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
            Built for{" "}
            <span className="bg-gradient-to-r from-cyan-600 to-purple-600 bg-clip-text text-transparent">
              Home Services
            </span>
          </h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Not a generic chatbot. SpaceVoice is trained specifically for HVAC, plumbing, electrical, and contracting businesses.
          </p>
        </div>

        {/* Tab navigation */}
        <div className="flex flex-wrap justify-center gap-4 mb-12">
          {useCases.map((useCase) => {
            const TabIcon = useCase.icon;
            const tabColors = colorVariants[useCase.color as keyof typeof colorVariants];
            const isActive = activeCase === useCase.id;

            return (
              <button
                key={useCase.id}
                onClick={() => setActiveCase(useCase.id)}
                className={cn(
                  "flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-all duration-300",
                  isActive
                    ? `${tabColors.activeBg} ${tabColors.text} ${tabColors.border} border`
                    : "bg-white text-gray-600 border border-gray-200 hover:border-gray-300"
                )}
              >
                <TabIcon className="w-5 h-5" />
                {useCase.title}
              </button>
            );
          })}
        </div>

        {/* Content area */}
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Left - Details */}
          <div className="order-2 lg:order-1">
            <div className={`inline-flex items-center justify-center w-16 h-16 rounded-2xl ${colors.bg} mb-6`}>
              <Icon className={`w-8 h-8 ${colors.text}`} />
            </div>

            <h3 className="text-3xl font-bold text-gray-900 mb-2">{currentCase.title}</h3>
            <p className={`text-lg ${colors.text} mb-4`}>{currentCase.tagline}</p>
            <p className="text-gray-600 mb-8 text-lg">{currentCase.description}</p>

            {/* Features */}
            <ul className="space-y-3 mb-8">
              {currentCase.features.map((feature, index) => (
                <li key={index} className="flex items-center gap-3">
                  <div className={`flex-shrink-0 w-6 h-6 rounded-full ${colors.bg} flex items-center justify-center`}>
                    <Check className={`w-4 h-4 ${colors.text}`} />
                  </div>
                  <span className="text-gray-700">{feature}</span>
                </li>
              ))}
            </ul>

            <a
              href="#demo-form"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-600 to-cyan-500 text-white font-semibold hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300"
            >
              See It In Action
              <ArrowRight className="w-5 h-5" />
            </a>
          </div>

          {/* Right - Stats Card */}
          <div className="order-1 lg:order-2">
            <div className={`p-8 rounded-2xl bg-white border ${colors.border} shadow-xl`}>
              {/* Visual representation */}
              <div className="mb-8 p-6 rounded-xl bg-gray-50 border border-gray-200">
                <div className="flex items-center gap-4 mb-4">
                  <div className={`w-12 h-12 rounded-full ${colors.bg} flex items-center justify-center`}>
                    <Icon className={`w-6 h-6 ${colors.text}`} />
                  </div>
                  <div>
                    <div className="text-gray-900 font-medium">Incoming Call</div>
                    <div className="text-sm text-gray-500">SpaceVoice AI handling...</div>
                  </div>
                </div>

                {/* Simulated conversation */}
                <div className="space-y-3 text-sm">
                  <div className="flex gap-2">
                    <span className="text-gray-500">Caller:</span>
                    <span className="text-gray-700">&quot;My AC isn&apos;t working and it&apos;s 95 degrees!&quot;</span>
                  </div>
                  <div className="flex gap-2">
                    <span className={colors.text}>AI:</span>
                    <span className="text-gray-700">&quot;I understand this is urgent. Let me get a technician to you within 2 hours...&quot;</span>
                  </div>
                </div>
              </div>

              {/* Stat highlight */}
              <div className="text-center">
                <div className={`text-5xl font-bold ${colors.text} mb-2`}>
                  {currentCase.stats.metric}
                </div>
                <div className="text-gray-600">{currentCase.stats.label}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
