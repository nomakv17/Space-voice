"use client";

import { useState, useMemo } from "react";
import { Calculator, DollarSign, Phone, TrendingUp, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

export function ROICalculator() {
  const [callsPerDay, setCallsPerDay] = useState(15);
  const [missedPercent, setMissedPercent] = useState(30);
  const [avgJobValue, setAvgJobValue] = useState(350);
  const [currentCost, setCurrentCost] = useState(0);

  const calculations = useMemo(() => {
    const monthlyMissedCalls = callsPerDay * 30 * (missedPercent / 100);
    const monthlyLostRevenue = monthlyMissedCalls * avgJobValue * 0.3; // 30% would have converted
    const yearlyLostRevenue = monthlyLostRevenue * 12;

    const recoveryRate = 0.73; // 73% recovery rate
    const monthlyRecovery = monthlyLostRevenue * recoveryRate;
    const yearlyRecovery = yearlyLostRevenue * recoveryRate;

    const spacevoiceCost = 249; // Growth plan
    const netMonthlyGain = monthlyRecovery - spacevoiceCost - currentCost;
    const roi = spacevoiceCost > 0 ? ((monthlyRecovery - spacevoiceCost) / spacevoiceCost) * 100 : 0;

    return {
      monthlyMissedCalls: Math.round(monthlyMissedCalls),
      monthlyLostRevenue: Math.round(monthlyLostRevenue),
      yearlyLostRevenue: Math.round(yearlyLostRevenue),
      monthlyRecovery: Math.round(monthlyRecovery),
      yearlyRecovery: Math.round(yearlyRecovery),
      netMonthlyGain: Math.round(netMonthlyGain),
      roi: Math.round(roi),
    };
  }, [callsPerDay, missedPercent, avgJobValue, currentCost]);

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);

  return (
    <section id="roi" className="relative py-24 bg-white">
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-green-50 border border-green-200 text-green-700 text-sm font-medium mb-6">
            <Calculator className="w-4 h-4" />
            ROI Calculator
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
            See How Much You&apos;re{" "}
            <span className="text-red-500">Losing</span> to Missed Calls
          </h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Enter your numbers below to see your potential revenue recovery with SpaceVoice.
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-12">
          {/* Left - Inputs */}
          <div className="space-y-8">
            {/* Calls per day */}
            <div className="p-6 rounded-xl bg-gray-50 border border-gray-200">
              <div className="flex justify-between items-center mb-4">
                <label className="text-gray-900 font-medium flex items-center gap-2">
                  <Phone className="w-5 h-5 text-cyan-600" />
                  Average calls per day
                </label>
                <span className="text-2xl font-bold text-cyan-600">{callsPerDay}</span>
              </div>
              <input
                type="range"
                min="5"
                max="100"
                value={callsPerDay}
                onChange={(e) => setCallsPerDay(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-cyan-600"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-2">
                <span>5</span>
                <span>100</span>
              </div>
            </div>

            {/* Missed percent */}
            <div className="p-6 rounded-xl bg-gray-50 border border-gray-200">
              <div className="flex justify-between items-center mb-4">
                <label className="text-gray-900 font-medium">
                  % of calls missed/voicemail
                </label>
                <span className="text-2xl font-bold text-red-500">{missedPercent}%</span>
              </div>
              <input
                type="range"
                min="10"
                max="70"
                value={missedPercent}
                onChange={(e) => setMissedPercent(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-red-500"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-2">
                <span>10%</span>
                <span>70%</span>
              </div>
            </div>

            {/* Average job value */}
            <div className="p-6 rounded-xl bg-gray-50 border border-gray-200">
              <div className="flex justify-between items-center mb-4">
                <label className="text-gray-900 font-medium flex items-center gap-2">
                  <DollarSign className="w-5 h-5 text-green-600" />
                  Average job value
                </label>
                <span className="text-2xl font-bold text-green-600">{formatCurrency(avgJobValue)}</span>
              </div>
              <input
                type="range"
                min="100"
                max="2000"
                step="50"
                value={avgJobValue}
                onChange={(e) => setAvgJobValue(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-green-600"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-2">
                <span>$100</span>
                <span>$2,000</span>
              </div>
            </div>

            {/* Current answering service cost */}
            <div className="p-6 rounded-xl bg-gray-50 border border-gray-200">
              <div className="flex justify-between items-center mb-4">
                <label className="text-gray-900 font-medium">
                  Current answering service cost/mo
                </label>
                <span className="text-2xl font-bold text-gray-600">{formatCurrency(currentCost)}</span>
              </div>
              <input
                type="range"
                min="0"
                max="5000"
                step="100"
                value={currentCost}
                onChange={(e) => setCurrentCost(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-gray-600"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-2">
                <span>$0</span>
                <span>$5,000</span>
              </div>
            </div>
          </div>

          {/* Right - Results */}
          <div className="space-y-6">
            {/* Current loss */}
            <div className="p-8 rounded-2xl bg-gradient-to-br from-red-50 to-white border border-red-200">
              <h3 className="text-lg font-medium text-red-600 mb-4">You&apos;re Currently Losing</h3>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Missed calls/month</span>
                  <span className="text-xl font-bold text-red-500">{calculations.monthlyMissedCalls}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Lost revenue/month</span>
                  <span className="text-xl font-bold text-red-500">{formatCurrency(calculations.monthlyLostRevenue)}</span>
                </div>
                <div className="h-px bg-red-200" />
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 font-medium">Lost revenue/year</span>
                  <span className="text-3xl font-bold text-red-500">{formatCurrency(calculations.yearlyLostRevenue)}</span>
                </div>
              </div>
            </div>

            {/* With SpaceVoice */}
            <div className="p-8 rounded-2xl bg-gradient-to-br from-green-50 to-white border border-green-200">
              <h3 className="text-lg font-medium text-green-700 mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5" />
                With SpaceVoice
              </h3>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Revenue recovered/month</span>
                  <span className="text-xl font-bold text-green-600">{formatCurrency(calculations.monthlyRecovery)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">SpaceVoice cost</span>
                  <span className="text-xl font-bold text-gray-600">-$249/mo</span>
                </div>
                <div className="h-px bg-green-200" />
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 font-medium">Net monthly gain</span>
                  <span className={cn(
                    "text-3xl font-bold",
                    calculations.netMonthlyGain > 0 ? "text-green-600" : "text-gray-600"
                  )}>
                    {formatCurrency(calculations.netMonthlyGain)}
                  </span>
                </div>
              </div>
            </div>

            {/* ROI highlight */}
            <div className="p-6 rounded-xl bg-gradient-to-r from-cyan-50 via-purple-50 to-cyan-50 border border-cyan-200 text-center">
              <div className="text-sm text-gray-600 mb-2">Estimated ROI</div>
              <div className="text-5xl font-bold bg-gradient-to-r from-cyan-600 to-purple-600 bg-clip-text text-transparent">
                {calculations.roi}%
              </div>
              <div className="text-sm text-gray-500 mt-2">
                Yearly recovery: {formatCurrency(calculations.yearlyRecovery)}
              </div>
            </div>

            {/* CTA */}
            <a
              href="#demo"
              className="flex items-center justify-center gap-2 w-full py-4 rounded-xl bg-gradient-to-r from-cyan-600 to-cyan-500 text-white font-semibold text-lg hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300"
            >
              Start Recovering Revenue
              <ArrowRight className="w-5 h-5" />
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
