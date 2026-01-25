"use client";

import { X, Check, PhoneOff, PhoneMissed, DollarSign, Clock, Phone, Calendar, AlertTriangle, Bot } from "lucide-react";

const problems = [
  {
    icon: PhoneOff,
    stat: "62%",
    text: "of calls go to voicemail after hours",
  },
  {
    icon: PhoneMissed,
    stat: "60 sec",
    text: "before customers call your competitor",
  },
  {
    icon: DollarSign,
    stat: "$50K+",
    text: "lost annually to missed calls",
  },
  {
    icon: Clock,
    stat: "$4K+/mo",
    text: "cost of 24/7 receptionist staff",
  },
];

const solutions = [
  {
    icon: Phone,
    title: "Every Call Answered",
    description: "Never miss a call again, even at 3 AM on holidays",
  },
  {
    icon: Calendar,
    title: "Instant Booking",
    description: "AI books appointments directly to your calendar",
  },
  {
    icon: AlertTriangle,
    title: "Emergency Triage",
    description: "Gas leaks & urgent issues escalated immediately",
  },
  {
    icon: Bot,
    title: "Natural Conversations",
    description: "Customers can't tell it's AI - sounds like your best receptionist",
  },
];

export function ProblemSolutionSection() {
  return (
    <section className="relative py-24 bg-white">
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
            The Problem with{" "}
            <span className="text-red-500">Traditional Phone Systems</span>
          </h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Home service businesses are bleeding revenue from missed calls and outdated communication systems.
          </p>
        </div>

        {/* Two column comparison */}
        <div className="grid lg:grid-cols-2 gap-8 lg:gap-12">
          {/* Problem column */}
          <div className="relative">
            <div className="absolute -top-4 left-4 px-4 py-2 rounded-full bg-red-50 border border-red-200 text-red-600 text-sm font-medium">
              <span className="flex items-center gap-2">
                <X className="w-4 h-4" />
                Without SpaceVoice
              </span>
            </div>

            <div className="pt-8 p-8 rounded-2xl bg-gradient-to-br from-red-50 to-white border border-red-200">
              <div className="space-y-6">
                {problems.map((problem, index) => {
                  const Icon = problem.icon;
                  return (
                    <div
                      key={index}
                      className="flex items-start gap-4 p-4 rounded-xl bg-white border border-gray-200 shadow-sm"
                    >
                      <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-red-50 flex items-center justify-center">
                        <Icon className="w-6 h-6 text-red-500" />
                      </div>
                      <div>
                        <div className="text-2xl font-bold text-red-500 mb-1">{problem.stat}</div>
                        <div className="text-gray-600">{problem.text}</div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Visual indicator of loss */}
              <div className="mt-8 p-6 rounded-xl bg-red-50 border border-red-200 text-center">
                <p className="text-red-600 font-medium">
                  Home service businesses lose an average of
                </p>
                <p className="text-4xl font-bold text-red-500 mt-2">$50,000+ / year</p>
                <p className="text-gray-500 mt-2">to missed and mishandled calls</p>
              </div>
            </div>
          </div>

          {/* Solution column */}
          <div className="relative">
            <div className="absolute -top-4 left-4 px-4 py-2 rounded-full bg-cyan-50 border border-cyan-200 text-cyan-700 text-sm font-medium">
              <span className="flex items-center gap-2">
                <Check className="w-4 h-4" />
                With SpaceVoice
              </span>
            </div>

            <div className="pt-8 p-8 rounded-2xl bg-gradient-to-br from-cyan-50 to-white border border-cyan-200">
              <div className="space-y-6">
                {solutions.map((solution, index) => {
                  const Icon = solution.icon;
                  return (
                    <div
                      key={index}
                      className="flex items-start gap-4 p-4 rounded-xl bg-white border border-gray-200 shadow-sm hover:border-cyan-300 hover:shadow-md transition-all duration-300"
                    >
                      <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-cyan-50 flex items-center justify-center">
                        <Icon className="w-6 h-6 text-cyan-600" />
                      </div>
                      <div>
                        <div className="text-lg font-semibold text-gray-900 mb-1">{solution.title}</div>
                        <div className="text-gray-600">{solution.description}</div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Visual indicator of gain */}
              <div className="mt-8 p-6 rounded-xl bg-cyan-50 border border-cyan-200 text-center">
                <p className="text-cyan-700 font-medium">
                  SpaceVoice customers recover an average of
                </p>
                <p className="text-4xl font-bold text-cyan-600 mt-2">73%</p>
                <p className="text-gray-500 mt-2">of previously missed revenue</p>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom CTA */}
        <div className="mt-16 text-center">
          <a
            href="#pricing"
            className="inline-flex items-center gap-2 px-8 py-4 rounded-xl bg-gradient-to-r from-cyan-600 to-cyan-500 text-white font-semibold text-lg hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300"
          >
            Stop Losing Calls Today
            <Check className="w-5 h-5" />
          </a>
        </div>
      </div>
    </section>
  );
}
