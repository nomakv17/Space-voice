"use client";

import { useState } from "react";
import { ChevronDown, MessageCircleQuestion } from "lucide-react";
import { cn } from "@/lib/utils";

const faqs = [
  {
    question: "How natural does the AI sound?",
    answer: "Extremely natural. We use state-of-the-art voice synthesis technology that's indistinguishable from human speech. Our AI adjusts tone, pace, and even uses natural pauses and filler words. Most customers don't realize they're speaking with an AI until told.",
  },
  {
    question: "Can it handle complex scheduling?",
    answer: "Absolutely. SpaceVoice integrates directly with Google Calendar, Calendly, ServiceTitan, Jobber, and more. It checks real-time availability, respects travel time between appointments, and can handle rescheduling and cancellations. No double-bookings ever.",
  },
  {
    question: "What happens if there's a real emergency?",
    answer: "Safety is our top priority. The AI is trained to recognize emergencies like gas leaks, flooding, electrical hazards, and no-heat/no-AC situations. It immediately escalates these to your on-call team via call, text, or your preferred method - while keeping the customer calm and collecting critical information.",
  },
  {
    question: "How long does setup take?",
    answer: "Most businesses are fully operational within 24 hours. Our onboarding team helps you configure your business details, services, and scheduling preferences. We'll train the AI on your specific terminology and workflows. No technical expertise required on your end.",
  },
  {
    question: "What integrations do you support?",
    answer: "We integrate with all major CRMs (HubSpot, Salesforce, Zoho), scheduling tools (Google Calendar, Calendly), field service management software (ServiceTitan, Jobber, Housecall Pro), and communication platforms (Slack, email). Custom integrations available for Enterprise plans.",
  },
  {
    question: "Can I keep my existing phone number?",
    answer: "Yes! You can either forward your existing business line to SpaceVoice (great for after-hours coverage) or get a dedicated local number. Both options work seamlessly with your current phone system.",
  },
  {
    question: "What if the AI can't handle a call?",
    answer: "The AI knows its limits. When it encounters a situation it can't handle confidently, it seamlessly transfers the call to your team with full context - so customers never have to repeat themselves. You can also set custom rules for immediate transfers based on keywords or caller ID.",
  },
  {
    question: "Is my data secure?",
    answer: "Absolutely. We're SOC 2 Type II compliant with end-to-end encryption for all calls and data. Call recordings and transcripts are stored securely and only accessible by you. We never sell or share your data with third parties.",
  },
];

export function FAQSection() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <section className="relative py-24 bg-gray-50">
      <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-gray-200 text-gray-600 text-sm font-medium mb-6 shadow-sm">
            <MessageCircleQuestion className="w-4 h-4" />
            FAQ
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
            Frequently Asked{" "}
            <span className="bg-gradient-to-r from-cyan-600 to-purple-600 bg-clip-text text-transparent">
              Questions
            </span>
          </h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Everything you need to know about SpaceVoice. Can&apos;t find an answer? Contact our team.
          </p>
        </div>

        {/* FAQ accordion */}
        <div className="space-y-4">
          {faqs.map((faq, index) => (
            <div
              key={index}
              className={cn(
                "rounded-xl border transition-all duration-300",
                openIndex === index
                  ? "bg-white border-cyan-300 shadow-lg"
                  : "bg-white border-gray-200 hover:border-gray-300"
              )}
            >
              <button
                onClick={() => setOpenIndex(openIndex === index ? null : index)}
                className="w-full px-6 py-5 flex items-center justify-between text-left"
              >
                <span className="text-lg font-medium text-gray-900 pr-4">{faq.question}</span>
                <ChevronDown
                  className={cn(
                    "w-5 h-5 text-gray-500 flex-shrink-0 transition-transform duration-300",
                    openIndex === index && "rotate-180 text-cyan-600"
                  )}
                />
              </button>

              <div
                className={cn(
                  "overflow-hidden transition-all duration-300",
                  openIndex === index ? "max-h-96" : "max-h-0"
                )}
              >
                <div className="px-6 pb-5">
                  <p className="text-gray-600 leading-relaxed">{faq.answer}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Contact CTA */}
        <div className="mt-12 text-center">
          <p className="text-gray-600 mb-4">Still have questions?</p>
          <a
            href="mailto:support@spacevoice.ai"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl border-2 border-gray-200 text-gray-700 font-medium hover:bg-gray-50 hover:border-gray-300 transition-all duration-300"
          >
            <MessageCircleQuestion className="w-5 h-5" />
            Contact Support
          </a>
        </div>
      </div>
    </section>
  );
}
