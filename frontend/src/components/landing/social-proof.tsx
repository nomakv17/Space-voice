"use client";

import { Building2, Users, Clock, CheckCircle2 } from "lucide-react";

const stats = [
  {
    icon: Building2,
    value: "Trusted in Canada",
    label: "Home Service Businesses",
  },
  {
    icon: Users,
    value: "10,000+",
    label: "Calls Handled",
  },
  {
    icon: Clock,
    value: "24/7",
    label: "Availability",
  },
  {
    icon: CheckCircle2,
    value: "98%",
    label: "Customer Satisfaction",
  },
];

const logos = [
  "HVAC Pros",
  "CoolAir Solutions",
  "PlumbRight",
  "ElectriFix",
  "HomeComfort Co.",
  "ServiceMaster HVAC",
];

export function SocialProofBar() {
  return (
    <section className="relative py-16 bg-gray-50 border-y border-gray-200">
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Trust text */}
        <p className="text-center text-gray-500 text-sm uppercase tracking-wider mb-8">
          Trusted by leading home service companies
        </p>

        {/* Logo marquee */}
        <div className="relative overflow-hidden mb-12">
          <div className="flex gap-12 animate-marquee">
            {[...logos, ...logos].map((logo, i) => (
              <div
                key={i}
                className="flex-shrink-0 px-6 py-3 rounded-lg bg-white border border-gray-200 text-gray-600 font-medium whitespace-nowrap shadow-sm"
              >
                {logo}
              </div>
            ))}
          </div>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {stats.map((stat, index) => {
            const Icon = stat.icon;
            return (
              <div
                key={index}
                className="text-center p-6 rounded-xl bg-white border border-gray-200 hover:border-cyan-300 hover:shadow-lg transition-all duration-300"
              >
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-cyan-50 text-cyan-600 mb-4">
                  <Icon className="w-6 h-6" />
                </div>
                <div className="text-3xl font-bold text-gray-900 mb-1">{stat.value}</div>
                <div className="text-sm text-gray-500">{stat.label}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* CSS for marquee animation */}
      <style jsx>{`
        @keyframes marquee {
          0% {
            transform: translateX(0);
          }
          100% {
            transform: translateX(-50%);
          }
        }
        .animate-marquee {
          animation: marquee 20s linear infinite;
        }
      `}</style>
    </section>
  );
}
