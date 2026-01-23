"use client";

import { Navbar } from "@/components/landing/navbar";
import { Phone, ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function TermsOfServicePage() {
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

          <h1 className="text-4xl font-bold text-gray-900 mb-4">Terms of Service</h1>
          <p className="text-gray-500 mb-8">Last updated: January 2026</p>

          <div className="prose prose-gray max-w-none">
            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">1. Acceptance of Terms</h2>
              <p className="text-gray-600 mb-4">
                By accessing or using SpaceVoice&apos;s AI voice agent platform (&quot;Service&quot;), you agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use our Service.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">2. Description of Service</h2>
              <p className="text-gray-600 mb-4">
                SpaceVoice provides AI-powered voice agents for businesses, including but not limited to:
              </p>
              <ul className="list-disc pl-6 text-gray-600 mb-4 space-y-2">
                <li>Automated call answering and routing</li>
                <li>Appointment scheduling and management</li>
                <li>Customer inquiry handling</li>
                <li>CRM integrations and call analytics</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">3. Account Registration</h2>
              <p className="text-gray-600 mb-4">
                To use our Service, you must create an account and provide accurate, complete information. You are responsible for maintaining the confidentiality of your account credentials and for all activities under your account.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">4. Acceptable Use</h2>
              <p className="text-gray-600 mb-4">You agree not to use the Service to:</p>
              <ul className="list-disc pl-6 text-gray-600 mb-4 space-y-2">
                <li>Violate any applicable laws or regulations</li>
                <li>Harass, abuse, or harm others</li>
                <li>Send unsolicited communications (spam)</li>
                <li>Impersonate any person or entity</li>
                <li>Interfere with the Service&apos;s operation</li>
                <li>Attempt to gain unauthorized access to systems</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">5. Pricing and Payment</h2>
              <p className="text-gray-600 mb-4">
                Subscription fees are billed in advance on a monthly or annual basis. Usage-based charges (call minutes, additional features) are billed monthly in arrears. All fees are non-refundable except as required by law.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">6. Intellectual Property</h2>
              <p className="text-gray-600 mb-4">
                SpaceVoice retains all rights to the Service, including software, algorithms, and documentation. You retain ownership of your data and content. By using the Service, you grant us a license to process your data as necessary to provide the Service.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">7. Service Level Agreement</h2>
              <p className="text-gray-600 mb-4">
                We strive for 99.9% uptime for our core services. Scheduled maintenance will be communicated in advance. Service credits may be available for extended outages as specified in your subscription plan.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">8. Limitation of Liability</h2>
              <p className="text-gray-600 mb-4">
                To the maximum extent permitted by law, SpaceVoice shall not be liable for any indirect, incidental, special, consequential, or punitive damages, including loss of profits, data, or business opportunities.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">9. Termination</h2>
              <p className="text-gray-600 mb-4">
                Either party may terminate this agreement with 30 days written notice. We may suspend or terminate your access immediately for violations of these terms. Upon termination, you may export your data within 30 days.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">10. Changes to Terms</h2>
              <p className="text-gray-600 mb-4">
                We may update these terms from time to time. We will notify you of material changes via email or through the Service. Continued use after changes constitutes acceptance of the new terms.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">11. Contact</h2>
              <p className="text-gray-600 mb-4">
                For questions about these terms, please contact us at:
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
