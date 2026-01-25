"use client";

import { Star, Quote, TrendingUp } from "lucide-react";

const testimonials = [
  {
    quote: "We were losing 40% of after-hours calls to voicemail. Now SpaceVoice handles them all, and we've recovered over $8,500/month in previously missed revenue.",
    author: "Mike Rodriguez",
    title: "Owner",
    company: "CoolAir HVAC Solutions",
    location: "Ontario, CA",
    metric: "$8,500/mo",
    metricLabel: "Revenue Recovered",
    rating: 5,
    avatar: "MR",
  },
  {
    quote: "The emergency triage feature is incredible. Last week it detected a gas leak situation and immediately got a tech dispatched while keeping the customer calm. That's priceless.",
    author: "Sarah Chen",
    title: "Operations Manager",
    company: "SafeHome Plumbing",
    location: "Ontario, CA",
    metric: "100%",
    metricLabel: "Emergency Detection",
    rating: 5,
    avatar: "SC",
  },
  {
    quote: "I was skeptical about AI handling calls, but customers genuinely can't tell the difference. Our booking rate increased 73% since implementing SpaceVoice.",
    author: "James Thompson",
    title: "CEO",
    company: "Thompson Electric",
    location: "FL, US",
    metric: "73%",
    metricLabel: "Booking Rate Increase",
    rating: 5,
    avatar: "JT",
  },
  {
    quote: "Setup took less than a day. The AI learned our services, pricing, and scheduling preferences immediately. Best investment we've made this year.",
    author: "Lisa Martinez",
    title: "Owner",
    company: "Comfort Zone HVAC",
    location: "Alberta, CA",
    metric: "< 24hrs",
    metricLabel: "Setup Time",
    rating: 5,
    avatar: "LM",
  },
];

export function TestimonialsSection() {
  return (
    <section className="relative py-24 bg-white">
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gray-100 border border-gray-200 text-gray-600 text-sm font-medium mb-6">
            Customer Stories
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
            Real Results from{" "}
            <span className="bg-gradient-to-r from-cyan-600 to-purple-600 bg-clip-text text-transparent">
              Real Businesses
            </span>
          </h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Don&apos;t just take our word for it. Here&apos;s what home service professionals are saying.
          </p>
        </div>

        {/* Testimonials grid */}
        <div className="grid md:grid-cols-2 gap-8">
          {testimonials.map((testimonial, index) => (
            <div
              key={index}
              className="relative p-8 rounded-2xl bg-gray-50 border border-gray-200 hover:border-cyan-300 hover:shadow-lg transition-all duration-300 group"
            >
              {/* Quote icon */}
              <Quote className="absolute top-6 right-6 w-8 h-8 text-cyan-200 group-hover:text-cyan-300 transition-colors" />

              {/* Rating */}
              <div className="flex gap-1 mb-4">
                {[...Array(testimonial.rating)].map((_, i) => (
                  <Star key={i} className="w-5 h-5 fill-yellow-400 text-yellow-400" />
                ))}
              </div>

              {/* Quote */}
              <blockquote className="text-lg text-gray-700 mb-6 leading-relaxed">
                &quot;{testimonial.quote}&quot;
              </blockquote>

              {/* Author info */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  {/* Avatar */}
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-cyan-100 to-purple-100 border border-cyan-200 flex items-center justify-center text-cyan-700 font-semibold">
                    {testimonial.avatar}
                  </div>
                  <div>
                    <div className="font-semibold text-gray-900">{testimonial.author}</div>
                    <div className="text-sm text-gray-600">
                      {testimonial.title}, {testimonial.company}
                    </div>
                    <div className="text-xs text-gray-500">{testimonial.location}</div>
                  </div>
                </div>

                {/* Metric badge */}
                <div className="text-right">
                  <div className="flex items-center gap-1 text-green-600">
                    <TrendingUp className="w-4 h-4" />
                    <span className="font-bold text-lg">{testimonial.metric}</span>
                  </div>
                  <div className="text-xs text-gray-500">{testimonial.metricLabel}</div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Trust indicators */}
        <div className="mt-16 p-8 rounded-2xl bg-gradient-to-r from-gray-50 via-white to-gray-50 border border-gray-200">
          <div className="grid md:grid-cols-4 gap-8 text-center">
            <div>
              <div className="text-3xl font-bold text-gray-900 mb-1">4.9/5</div>
              <div className="flex justify-center gap-1 mb-2">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                ))}
              </div>
              <div className="text-sm text-gray-600">Average Rating</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-gray-900 mb-1">50+</div>
              <div className="text-sm text-gray-600 mt-3">Active Businesses</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-gray-900 mb-1">10,000+</div>
              <div className="text-sm text-gray-600 mt-3">Calls Handled</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-gray-900 mb-1">$500K+</div>
              <div className="text-sm text-gray-600 mt-3">Revenue Recovered</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
