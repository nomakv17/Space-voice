"use client";

import { useState, useMemo } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Calculator,
  Phone,
  Clock,
  DollarSign,
  TrendingDown,
  Users,
  CheckCircle2,
  Sparkles,
} from "lucide-react";

// Pricing tiers (final prices - what customers pay)
const PRICING_TIERS = {
  budget: {
    name: "Budget",
    pricePerMinute: 0.12,
    description: "Cost-effective for high volume",
    features: ["Basic voice quality", "Standard response time", "Email support"],
  },
  balanced: {
    name: "Balanced",
    pricePerMinute: 0.18,
    description: "Best value for most businesses",
    features: ["HD voice quality", "Fast response time", "Priority support", "Call recording"],
    recommended: true,
  },
  premium: {
    name: "Premium",
    pricePerMinute: 0.25,
    description: "Maximum quality & features",
    features: [
      "Ultra-HD voice",
      "Instant response",
      "24/7 dedicated support",
      "Advanced analytics",
      "Custom integrations",
    ],
  },
};

// Industry benchmarks for comparison
const INDUSTRY_COSTS = {
  humanAgent: {
    hourlyRate: 25, // $25/hour for a human agent
    callsPerHour: 8, // Average calls handled per hour
    costPerMinute: 25 / 60, // ~$0.42/min
  },
  callCenter: {
    costPerMinute: 0.75, // Outsourced call center
  },
};

export default function PricingCalculatorPage() {
  const [tier, setTier] = useState<keyof typeof PRICING_TIERS>("balanced");
  const [callsPerDay, setCallsPerDay] = useState(50);
  const [avgCallDuration, setAvgCallDuration] = useState(4); // minutes

  const calculations = useMemo(() => {
    const selectedTier = PRICING_TIERS[tier];
    const minutesPerDay = callsPerDay * avgCallDuration;
    const minutesPerMonth = minutesPerDay * 30;

    const monthlyCost = minutesPerMonth * selectedTier.pricePerMinute;
    const humanAgentCost = minutesPerMonth * INDUSTRY_COSTS.humanAgent.costPerMinute;
    const callCenterCost = minutesPerMonth * INDUSTRY_COSTS.callCenter.costPerMinute;

    const savingsVsHuman = humanAgentCost - monthlyCost;
    const savingsVsCallCenter = callCenterCost - monthlyCost;
    const savingsPercentVsHuman = ((savingsVsHuman / humanAgentCost) * 100).toFixed(0);

    // ROI calculation (assuming $50 average value per successful call)
    const callValuePerMonth = callsPerDay * 30 * 50 * 0.15; // 15% conversion
    const roi = ((callValuePerMonth - monthlyCost) / monthlyCost * 100).toFixed(0);

    return {
      minutesPerMonth,
      monthlyCost,
      humanAgentCost,
      callCenterCost,
      savingsVsHuman,
      savingsVsCallCenter,
      savingsPercentVsHuman,
      roi,
      costPerCall: selectedTier.pricePerMinute * avgCallDuration,
    };
  }, [tier, callsPerDay, avgCallDuration]);

  const selectedTier = PRICING_TIERS[tier];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <Calculator className="h-8 w-8 text-primary" />
          Pricing Calculator
        </h1>
        <p className="text-muted-foreground mt-1">
          Estimate your monthly costs and see how much you can save with AI voice agents
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Configuration Card */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-lg">Configure Your Usage</CardTitle>
            <CardDescription>Adjust based on your expected call volume</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Tier Selection */}
            <div className="space-y-2">
              <Label>Select Plan</Label>
              <Select value={tier} onValueChange={(v) => setTier(v as keyof typeof PRICING_TIERS)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(PRICING_TIERS).map(([key, t]) => (
                    <SelectItem key={key} value={key}>
                      <div className="flex items-center gap-2">
                        {t.name}
                        {"recommended" in t && t.recommended && (
                          <Badge variant="secondary" className="text-xs">
                            Recommended
                          </Badge>
                        )}
                        <span className="text-muted-foreground">
                          ${t.pricePerMinute.toFixed(2)}/min
                        </span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">{selectedTier.description}</p>
            </div>

            <Separator />

            {/* Calls per Day */}
            <div className="space-y-3">
              <div className="flex justify-between">
                <Label>Calls per Day</Label>
                <span className="text-sm font-medium">{callsPerDay} calls</span>
              </div>
              <Slider
                value={[callsPerDay]}
                onValueChange={([v]) => setCallsPerDay(v)}
                min={10}
                max={500}
                step={10}
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>10</span>
                <span>500</span>
              </div>
            </div>

            {/* Average Call Duration */}
            <div className="space-y-3">
              <div className="flex justify-between">
                <Label>Avg. Call Duration</Label>
                <span className="text-sm font-medium">{avgCallDuration} min</span>
              </div>
              <Slider
                value={[avgCallDuration]}
                onValueChange={([v]) => setAvgCallDuration(v)}
                min={1}
                max={15}
                step={1}
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>1 min</span>
                <span>15 min</span>
              </div>
            </div>

            <Separator />

            {/* Plan Features */}
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">Plan Includes</Label>
              <ul className="space-y-1.5">
                {selectedTier.features.map((feature) => (
                  <li key={feature} className="flex items-center gap-2 text-sm">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                    {feature}
                  </li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>

        {/* Results Cards */}
        <div className="lg:col-span-2 space-y-6">
          {/* Monthly Cost */}
          <Card className="border-primary/50 bg-primary/5">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2">
                <DollarSign className="h-5 w-5" />
                Your Estimated Monthly Cost
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-baseline gap-2">
                <span className="text-5xl font-bold">
                  ${calculations.monthlyCost.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </span>
                <span className="text-muted-foreground">/month</span>
              </div>
              <div className="mt-3 grid grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Minutes/month</p>
                  <p className="font-medium">{calculations.minutesPerMonth.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Cost per call</p>
                  <p className="font-medium">${calculations.costPerCall.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Price per minute</p>
                  <p className="font-medium">${selectedTier.pricePerMinute.toFixed(2)}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Savings Comparison */}
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Users className="h-4 w-4 text-blue-500" />
                  vs. Hiring Staff
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Human agent cost</span>
                    <span className="font-mono">
                      ${calculations.humanAgentCost.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">AI agent cost</span>
                    <span className="font-mono">
                      ${calculations.monthlyCost.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </span>
                  </div>
                  <Separator />
                  <div className="flex items-center justify-between">
                    <span className="font-medium flex items-center gap-1">
                      <TrendingDown className="h-4 w-4 text-emerald-500" />
                      You save
                    </span>
                    <span className="font-bold text-emerald-500">
                      ${calculations.savingsVsHuman.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                      <span className="text-xs ml-1">({calculations.savingsPercentVsHuman}%)</span>
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Phone className="h-4 w-4 text-violet-500" />
                  vs. Call Center
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Call center cost</span>
                    <span className="font-mono">
                      ${calculations.callCenterCost.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">AI agent cost</span>
                    <span className="font-mono">
                      ${calculations.monthlyCost.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </span>
                  </div>
                  <Separator />
                  <div className="flex items-center justify-between">
                    <span className="font-medium flex items-center gap-1">
                      <TrendingDown className="h-4 w-4 text-emerald-500" />
                      You save
                    </span>
                    <span className="font-bold text-emerald-500">
                      ${calculations.savingsVsCallCenter.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* ROI Card */}
          <Card className="bg-gradient-to-r from-emerald-500/10 to-blue-500/10 border-emerald-500/30">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-amber-500" />
                    Estimated ROI
                  </p>
                  <p className="text-3xl font-bold text-emerald-500">{calculations.roi}%</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Based on 15% call-to-booking conversion, $50 avg. booking value
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-muted-foreground">24/7 Availability</p>
                  <p className="text-2xl font-bold">
                    <Clock className="inline h-6 w-6 mr-1" />
                    Always On
                  </p>
                  <p className="text-xs text-muted-foreground">No sick days, no training</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
