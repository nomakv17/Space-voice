# SpaceVoice AI: World-Class Agency Specification

## 1. Project Identity & Goal
- **Name:** SpaceVoice AI
- **Primary Vertical:** Home Services (HVAC focus).
- **Core Mission:** Mirroring $100k+ agencies (MedVoice, Assort, SpiderX) to deliver enterprise-grade conversion and zero-latency triage.

## 2. The Solid Stack (Step-by-Step)
- **Voice Orchestration:** Retell AI (for 140ms response and proprietary barge-in logic).
- **The Brain (Logic):** Claude 4.5 Sonnet (for perfect tool-calling and vertical reasoning).
- **Telephony:** Telnyx (for private-backbone audio transport and sub-200ms latency).

## 3. Agency Mirroring (The 'World Class' Framework)
SpaceVoice will combine the winning strategies from 5 successful verticals:
- **Medical Pattern (Assort/MedVoice):** Implement 'Emergency Triage Logic'. Distinguish between routine and high-value urgent jobs (e.g., HVAC safety hazards vs. maintenance).
- **Real Estate Pattern (SpiderX):** Use 'VIP Intake' tone. Capture high-intent data (budget, urgency) to suggest 'curated solutions' during the call.
- **HVAC Pattern (JustCall/TechWize):** Instant 24/7 dispatcher logic. Direct injection of bookings into field management software (e.g., ServiceTitan).
- **IT Pattern (Intellectyx):** Scalable tool-calling for technical troubleshooting before dispatching a tech.

## 4. Competitive Advantage
- **Zero-Detection:** By pairing Telnyx with Retell, we eliminate the 3-second 'AI pause' that kills conversion.
- **Outcome-Based Reporting:** Post-call analysis must extract: (1) Urgent dispatch needs, (2) Potential job value, (3) Customer sentiment.

## 5. Landing Page Implementation (Phase 8 - COMPLETE ✅)
World-class landing page at spacevoice.ai mirroring top agency patterns:

### Competitors Mirrored
| Agency | Source | Key Pattern Adopted |
|--------|--------|---------------------|
| MedVoice | medvoiceinc.com | ROI Calculator, quantified metrics |
| Assort Health | assorthealth.com | Testimonials with specific results |
| SpiderX AI | spiderx.ai/realestate | Interactive phone demo CTA |
| Intellectyx | intellectyx.com | Modern gradient palette, segment targeting |
| TechWize | techwize.com | Trust badges, glassmorphism effects |
| JustCall HVAC | justcall.io/product/ai-voice-agent/hvac/ | Problem→Solution framework, HVAC terminology |

### Landing Page Sections (12 Total)
1. **Hero** - Headline, phone demo form, floating metrics
2. **Social Proof Bar** - Client logos, key statistics
3. **Problem/Solution** - Before/After comparison (red/cyan coding)
4. **How It Works** - 3-step process with feature lists
5. **Features Grid** - 6 capability cards with color-coded highlights
6. **Use Cases** - Tabbed industry verticals (HVAC, Plumbing, Electrical, Contractors)
7. **ROI Calculator** - Interactive savings estimator
8. **Pricing Preview** - 3-tier cards (Starter $99, Growth $249, Enterprise)
9. **Testimonials** - Quote cards with specific metrics
10. **FAQ** - Accordion with 8 common questions
11. **Final CTA** - Conversion section with dual CTAs
12. **Footer** - Navigation, compliance badges

### Design System
- **Theme:** Dark premium (#0a0a0a → #1a1a1a)
- **Primary CTA:** Cyan (#00d8ff) - maximum conversion
- **Accent:** Purple gradient (#8b5cf6 → #a855f7)
- **Effects:** Glassmorphism, gradient orbs, scroll animations

### Files Created
```
frontend/src/components/landing/
├── index.ts          # Barrel export
├── navbar.tsx        # Fixed marketing nav
├── hero.tsx          # Above-fold with phone demo
├── social-proof.tsx  # Logo marquee + stats
├── problem-solution.tsx  # Before/After comparison
├── how-it-works.tsx  # 3-step process
├── features-grid.tsx # 6 feature cards
├── use-cases.tsx     # Industry verticals
├── roi-calculator.tsx # Interactive calculator
├── pricing-preview.tsx # 3 pricing tiers
├── testimonials.tsx  # Customer quotes
├── faq.tsx           # Accordion FAQ
└── footer.tsx        # Final CTA + footer
```
