"use client";

import { Navbar } from "@/components/landing/navbar";
import { Phone, ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function PrivacyPolicyPage() {
  return (
    <main className="min-h-screen bg-white">
      <Navbar />

      <div className="pt-24 pb-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-gray-600 hover:text-cyan-600 transition-colors mb-8"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Home
          </Link>

          <h1 className="text-4xl font-bold text-gray-900 mb-4">Privacy Policy</h1>
          <p className="text-gray-500 mb-8">Last updated: January 2026</p>

          <div className="prose prose-gray max-w-none">
            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">1. Introduction</h2>
              <p className="text-gray-600 mb-4">
                SpaceVoice (&quot;we&quot;, &quot;our&quot;, or &quot;us&quot;) is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our AI-powered voice agent platform.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">2. Information We Collect</h2>
              <h3 className="text-xl font-medium text-gray-800 mb-3">Personal Information</h3>
              <ul className="list-disc pl-6 text-gray-600 mb-4 space-y-2">
                <li>Contact information (name, email address, phone number)</li>
                <li>Business information (company name, industry)</li>
                <li>Account credentials</li>
                <li>Payment information (processed securely through our payment providers)</li>
              </ul>

              <h3 className="text-xl font-medium text-gray-800 mb-3">Call Data</h3>
              <ul className="list-disc pl-6 text-gray-600 mb-4 space-y-2">
                <li>Call recordings and transcripts (with consent)</li>
                <li>Call metadata (duration, time, caller information)</li>
                <li>AI interaction logs</li>
              </ul>

              <h3 className="text-xl font-medium text-gray-800 mb-3">Usage Data</h3>
              <ul className="list-disc pl-6 text-gray-600 mb-4 space-y-2">
                <li>Device and browser information</li>
                <li>IP address and location data</li>
                <li>Platform usage analytics</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">3. How We Use Your Information</h2>
              <ul className="list-disc pl-6 text-gray-600 mb-4 space-y-2">
                <li>To provide and maintain our voice agent services</li>
                <li>To process appointments and customer interactions</li>
                <li>To improve our AI models and service quality</li>
                <li>To communicate with you about your account and services</li>
                <li>To detect and prevent fraud or abuse</li>
                <li>To comply with legal obligations</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">4. Data Security</h2>
              <p className="text-gray-600 mb-4">
                We implement industry-standard security measures to protect your data:
              </p>
              <ul className="list-disc pl-6 text-gray-600 mb-4 space-y-2">
                <li>256-bit AES encryption for data at rest and in transit</li>
                <li>SOC 2 Type II compliant infrastructure</li>
                <li>Regular security audits and penetration testing</li>
                <li>Access controls and employee training</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">5. Data Retention</h2>
              <p className="text-gray-600 mb-4">
                We retain your data for as long as necessary to provide our services and comply with legal obligations. Call recordings are retained for 90 days by default, unless you configure a different retention period.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">6. Your Rights</h2>
              <p className="text-gray-600 mb-4">You have the right to:</p>
              <ul className="list-disc pl-6 text-gray-600 mb-4 space-y-2">
                <li>Access your personal data</li>
                <li>Correct inaccurate data</li>
                <li>Request deletion of your data</li>
                <li>Export your data in a portable format</li>
                <li>Opt out of marketing communications</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">7. Third-Party Services</h2>
              <p className="text-gray-600 mb-4">
                We use trusted third-party services for telephony, AI processing, and infrastructure. These providers are contractually bound to protect your data and comply with applicable privacy laws.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">8. Contact Us</h2>
              <p className="text-gray-600 mb-4">
                For privacy-related inquiries, please contact us at:
              </p>
              <p className="text-gray-600">
                Email: <a href="mailto:support@spacevoice.ai" className="text-cyan-600 hover:underline">support@spacevoice.ai</a>
              </p>
            </section>
          </div>
        </div>
      </div>

      {/* Simple Footer */}
      <footer className="border-t border-gray-200 py-8">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-600 to-purple-600 flex items-center justify-center">
              <Phone className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold text-gray-900">SpaceVoice</span>
          </div>
          <p className="text-sm text-gray-500">
            © {new Date().getFullYear()} SpaceVoice. All rights reserved.
          </p>
        </div>
      </footer>
    </main>
  );
}
