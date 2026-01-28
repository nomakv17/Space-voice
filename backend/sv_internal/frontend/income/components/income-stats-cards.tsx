"use client";

import { Card, CardContent } from "@/components/ui/card";
import {
  DollarSign,
  TrendingUp,
  Banknote,
  Building2,
  ArrowUpRight,
  ArrowDownRight,
  Receipt,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { IncomeSummary } from "@/lib/api/income";

interface IncomeStatsCardsProps {
  summary: IncomeSummary | undefined;
  isLoading: boolean;
}

export function IncomeStatsCards({ summary, isLoading }: IncomeStatsCardsProps) {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const stats = [
    {
      name: "Total MRR",
      value: summary ? formatCurrency(summary.total_mrr) : "$0",
      icon: DollarSign,
      color: "text-emerald-400",
      bgColor: "bg-emerald-400/10",
      description: "Monthly recurring revenue",
    },
    {
      name: "Total ARR",
      value: summary ? formatCurrency(summary.total_arr) : "$0",
      icon: TrendingUp,
      color: "text-blue-400",
      bgColor: "bg-blue-400/10",
      description: "Annual recurring revenue",
    },
    {
      name: "Net Revenue",
      value: summary ? formatCurrency(summary.total_net_revenue) : "$0",
      icon: Banknote,
      color: "text-violet-400",
      bgColor: "bg-violet-400/10",
      description: "Lifetime net revenue",
    },
    {
      name: "Active Clients",
      value: summary?.active_clients ?? 0,
      icon: Building2,
      color: "text-amber-400",
      bgColor: "bg-amber-400/10",
      description: "Currently active",
    },
    {
      name: "MRR Growth",
      value: summary ? `${summary.mrr_growth_pct >= 0 ? "+" : ""}${summary.mrr_growth_pct}%` : "0%",
      icon: summary?.mrr_growth_pct && summary.mrr_growth_pct >= 0 ? ArrowUpRight : ArrowDownRight,
      color: summary?.mrr_growth_pct && summary.mrr_growth_pct >= 0 ? "text-emerald-400" : "text-red-400",
      bgColor: summary?.mrr_growth_pct && summary.mrr_growth_pct >= 0 ? "bg-emerald-400/10" : "bg-red-400/10",
      description: "Month over month",
    },
    {
      name: "Setup Fees",
      value: summary ? formatCurrency(summary.total_setup_fees) : "$0",
      icon: Receipt,
      color: "text-cyan-400",
      bgColor: "bg-cyan-400/10",
      description: "One-time fees collected",
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      {stats.map((stat) => (
        <Card
          key={stat.name}
          className="border-border/50 bg-card/50 backdrop-blur transition-colors hover:bg-card/80"
        >
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className={cn("rounded-lg p-2", stat.bgColor)}>
                <stat.icon className={cn("h-4 w-4", stat.color)} />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs text-muted-foreground">{stat.name}</p>
                <p className={cn("text-lg font-semibold", isLoading && "animate-pulse")}>
                  {isLoading ? "..." : stat.value}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
