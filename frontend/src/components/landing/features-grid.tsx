"use client";

import { AlertTriangle, Clock, Calendar, Users, Database, BarChart3, ArrowUpRight } from "lucide-react";

const features = [
  {
    icon: AlertTriangle,
    title: "Emergency Triage",
    description: "AI instantly detects emergencies like gas leaks, flooding, or electrical hazards. Automatically escalates to on-call technicians with full context.",
    highlight: "Safety-First",
    color: "red",
  },
  {
    icon: Clock,
    title: "24/7 Availability",
    description: "Never miss another call - even at 3 AM on Christmas. Your AI agent handles every inquiry with the same professionalism as your best receptionist.",
    highlight: "Always On",
    color: "cyan",
  },
  {
    icon: Calendar,
    title: "Instant Booking",
    description: "Direct integration with Google Calendar, Calendly, ServiceTitan, and more. AI checks availability and books appointments in real-time.",
    highlight: "No Double-Booking",
    color: "purple",
  },
  {
    icon: Users,
    title: "Human Handoff",
    description: "Seamlessly transfer complex calls to your team. AI provides full context so customers never have to repeat themselves.",
    highlight: "Smooth Transitions",
    color: "green",
  },
  {
    icon: Database,
    title: "CRM Integration",
    description: "Automatically sync leads and call notes to HubSpot, Salesforce, Jobber, or your preferred CRM. Keep all customer data in one place.",
    highlight: "Auto-Sync",
    color: "blue",
  },
  {
    icon: BarChart3,
    title: "Call Analytics",
    description: "Full transcripts, sentiment analysis, and conversion tracking. Know exactly what's working and where to improve.",
    highlight: "Actionable Insights",
    color: "amber",
  },
];

const colorVariants = {
  red: {
    bg: "bg-red-50",
    border: "hover:border-red-300",
    text: "text-red-600",
    highlightBg: "bg-red-100",
  },
  cyan: {
    bg: "bg-cyan-50",
    border: "hover:border-cyan-300",
    text: "text-cyan-600",
    highlightBg: "bg-cyan-100",
  },
  purple: {
    bg: "bg-purple-50",
    border: "hover:border-purple-300",
    text: "text-purple-600",
    highlightBg: "bg-purple-100",
  },
  green: {
    bg: "bg-green-50",
    border: "hover:border-green-300",
    text: "text-green-600",
    highlightBg: "bg-green-100",
  },
  blue: {
    bg: "bg-blue-50",
    border: "hover:border-blue-300",
    text: "text-blue-600",
    highlightBg: "bg-blue-100",
  },
  amber: {
    bg: "bg-amber-50",
    border: "hover:border-amber-300",
    text: "text-amber-600",
    highlightBg: "bg-amber-100",
  },
};

export function FeaturesGrid() {
  return (
    <section className="relative py-24 bg-white">
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gray-100 border border-gray-200 text-gray-600 text-sm font-medium mb-6">
            Powerful Features
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
            Everything You Need to{" "}
            <span className="bg-gradient-to-r from-cyan-600 to-purple-600 bg-clip-text text-transparent">
              Dominate Your Market
            </span>
          </h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Built specifically for HVAC and home service businesses. Every feature designed to increase conversions and reduce overhead.
          </p>
        </div>

        {/* Features grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => {
            const Icon = feature.icon;
            const colors = colorVariants[feature.color as keyof typeof colorVariants];

            return (
              <div
                key={index}
                className={`group relative p-8 rounded-2xl bg-white border border-gray-200 ${colors.border} hover:shadow-xl transition-all duration-300`}
              >
                {/* Highlight badge */}
                <div className={`absolute top-4 right-4 px-3 py-1 rounded-full text-xs font-medium ${colors.highlightBg} ${colors.text}`}>
                  {feature.highlight}
                </div>

                {/* Icon */}
                <div className={`inline-flex items-center justify-center w-14 h-14 rounded-xl ${colors.bg} mb-6`}>
                  <Icon className={`w-7 h-7 ${colors.text}`} />
                </div>

                {/* Content */}
                <h3 className="text-xl font-bold text-gray-900 mb-3 flex items-center gap-2">
                  {feature.title}
                  <ArrowUpRight className="w-4 h-4 text-gray-400 group-hover:text-gray-900 transition-colors" />
                </h3>
                <p className="text-gray-600 leading-relaxed">
                  {feature.description}
                </p>
              </div>
            );
          })}
        </div>

        {/* Bottom feature highlight */}
        <div className="mt-12 p-8 rounded-2xl bg-gradient-to-r from-cyan-50 via-purple-50 to-cyan-50 border border-cyan-200">
          <div className="grid md:grid-cols-3 gap-8 text-center">
            <div>
              <div className="text-4xl font-bold text-cyan-600 mb-2">99.9%</div>
              <div className="text-gray-600">Uptime Guarantee</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-purple-600 mb-2">&lt;200ms</div>
              <div className="text-gray-600">Response Latency</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-green-600 mb-2">SOC 2</div>
              <div className="text-gray-600">Type II Compliant</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
