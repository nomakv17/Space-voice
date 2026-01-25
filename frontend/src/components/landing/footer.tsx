"use client";

import { Phone, ArrowRight, Mail, MapPin, Shield, Lock } from "lucide-react";
import Link from "next/link";

const footerLinks = {
  product: [
    { label: "Features", href: "#features" },
    { label: "Pricing", href: "#pricing" },
    { label: "Use Cases", href: "#use-cases" },
    { label: "FAQ", href: "#faq" },
  ],
  company: [
    { label: "Contact", href: "/contact" },
  ],
  legal: [
    { label: "Privacy Policy", href: "/privacy" },
    { label: "Terms of Service", href: "/terms" },
  ],
};

export function FooterSection() {
  return (
    <>
      {/* Final CTA Section */}
      <section className="relative py-24 bg-gradient-to-b from-white to-gray-50">
        {/* Background effects */}
        <div className="absolute inset-0">
          <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-cyan-100/50 rounded-full blur-[150px]" />
          <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-purple-100/50 rounded-full blur-[120px]" />
        </div>

        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-900 mb-6">
            Ready to{" "}
            <span className="bg-gradient-to-r from-cyan-600 to-purple-600 bg-clip-text text-transparent">
              Never Miss Another Call?
            </span>
          </h2>
          <p className="text-xl text-gray-600 mb-10 max-w-2xl mx-auto">
            Join 50+ home service businesses already using SpaceVoice to capture more leads, book more appointments, and grow their revenue.
          </p>

          <div className="flex justify-center">
            <a
              href="https://calendly.com/tai-alabi/spacevoice-demo"
              className="group w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-4 rounded-xl bg-gradient-to-r from-cyan-600 to-cyan-500 text-white font-semibold text-lg shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 hover:scale-105 transition-all duration-300"
            >
              <Phone className="w-5 h-5" />
              Book Demo
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </a>
          </div>

          <p className="mt-6 text-sm text-gray-500">
            30-day money-back guarantee • Cancel anytime
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-8">
            {/* Brand column */}
            <div className="col-span-2">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-600 to-purple-600 flex items-center justify-center">
                  <Phone className="w-5 h-5 text-white" />
                </div>
                <span className="text-xl font-bold text-gray-900">SpaceVoice</span>
              </div>
              <p className="text-gray-600 text-sm mb-6 max-w-xs">
                AI-powered voice agents for HVAC and home service businesses. Never miss another call.
              </p>

              <div className="space-y-2 text-sm text-gray-600">
                <a href="mailto:hello@spacevoice.ai" className="flex items-center gap-2 hover:text-cyan-600 transition-colors">
                  <Mail className="w-4 h-4" />
                  hello@spacevoice.ai
                </a>
                <div className="flex items-center gap-2">
                  <MapPin className="w-4 h-4" />
                  San Francisco, CA
                </div>
              </div>
            </div>

            {/* Link columns */}
            <div>
              <h4 className="text-gray-900 font-semibold mb-4">Product</h4>
              <ul className="space-y-2">
                {footerLinks.product.map((link) => (
                  <li key={link.label}>
                    <Link href={link.href} className="text-sm text-gray-600 hover:text-cyan-600 transition-colors">
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h4 className="text-gray-900 font-semibold mb-4">Company</h4>
              <ul className="space-y-2">
                {footerLinks.company.map((link) => (
                  <li key={link.label}>
                    <Link href={link.href} className="text-sm text-gray-600 hover:text-cyan-600 transition-colors">
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h4 className="text-gray-900 font-semibold mb-4">Legal</h4>
              <ul className="space-y-2">
                {footerLinks.legal.map((link) => (
                  <li key={link.label}>
                    <Link href={link.href} className="text-sm text-gray-600 hover:text-cyan-600 transition-colors">
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Bottom bar */}
          <div className="mt-12 pt-8 border-t border-gray-200 flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-sm text-gray-500">
              © {new Date().getFullYear()} SpaceVoice. All rights reserved.
            </p>

            {/* Trust badges */}
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <Shield className="w-4 h-4 text-green-600" />
                SOC 2 Compliant
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <Lock className="w-4 h-4 text-cyan-600" />
                256-bit Encryption
              </div>
            </div>
          </div>
        </div>
      </footer>
    </>
  );
}
