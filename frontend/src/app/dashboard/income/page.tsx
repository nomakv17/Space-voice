"use client";

import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { RefreshCw, RotateCcw, DollarSign, TrendingUp, Phone, Clock, Users, Percent } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import {
  getRevenueSummary,
  getRevenueHistory,
  seedRevenue,
  reseedRevenue,
  type RevenueSummary,
  type MonthlyRevenue,
} from "@/lib/api/revenue";
import { RevenueOverTimeChart } from "./components/revenue-over-time-chart";
import { CallsRevenueChart } from "./components/calls-revenue-chart";

export default function IncomePage() {
  const queryClient = useQueryClient();
  const [selectedMonth, setSelectedMonth] = useState<string>("all");

  // Fetch revenue history (to get available months)
  const { data: history = [], isLoading: historyLoading } = useQuery<MonthlyRevenue[]>({
    queryKey: ["revenue-history"],
    queryFn: () => getRevenueHistory(12),
  });

  // Compute available months from history
  const availableMonths = useMemo(() => {
    return history.map((item) => ({
      value: `${item.year}-${item.month}`,
      label: `${item.month_name} ${item.year}`,
      year: item.year,
      month: item.month,
    }));
  }, [history]);

  // Parse selected month
  const selectedYearMonth = useMemo(() => {
    if (selectedMonth === "all") return { year: undefined, month: undefined };
    const [year, month] = selectedMonth.split("-").map(Number);
    return { year, month };
  }, [selectedMonth]);

  // Fetch revenue summary with optional month filter
  const { data: summary, isLoading: summaryLoading } = useQuery<RevenueSummary>({
    queryKey: ["revenue-summary", selectedYearMonth.year, selectedYearMonth.month],
    queryFn: () => getRevenueSummary(selectedYearMonth.year, selectedYearMonth.month),
  });

  // Seed mutation
  const seedMutation = useMutation({
    mutationFn: seedRevenue,
    onSuccess: (data) => {
      toast.success(data.message);
      void queryClient.invalidateQueries({ queryKey: ["revenue-summary"] });
      void queryClient.invalidateQueries({ queryKey: ["revenue-history"] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to seed data: ${error.message}`);
    },
  });

  // Reseed mutation
  const reseedMutation = useMutation({
    mutationFn: reseedRevenue,
    onSuccess: (data) => {
      toast.success(data.message);
      setSelectedMonth("all");
      void queryClient.invalidateQueries({ queryKey: ["revenue-summary"] });
      void queryClient.invalidateQueries({ queryKey: ["revenue-history"] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to reseed data: ${error.message}`);
    },
  });

  const isLoading = summaryLoading || historyLoading;
  const hasData = history.length > 0;
  const isPending = seedMutation.isPending || reseedMutation.isPending;

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatNumber = (value: number) => {
    return new Intl.NumberFormat("en-US").format(value);
  };

  const stats = [
    {
      name: "Total Revenue",
      value: summary ? formatCurrency(summary.total_revenue) : "$0",
      icon: DollarSign,
      color: "text-emerald-400",
      bgColor: "bg-emerald-400/10",
      description: selectedMonth === "all" ? "All time" : "This month",
    },
    {
      name: "Total Profit",
      value: summary ? formatCurrency(summary.total_profit) : "$0",
      icon: TrendingUp,
      color: "text-blue-400",
      bgColor: "bg-blue-400/10",
      description: `${summary?.profit_margin_pct ?? 0}% margin`,
    },
    {
      name: "Total Calls",
      value: summary ? formatNumber(summary.total_calls) : "0",
      icon: Phone,
      color: "text-violet-400",
      bgColor: "bg-violet-400/10",
      description: `${summary?.completed_calls ?? 0} completed`,
    },
    {
      name: "Total Minutes",
      value: summary ? formatNumber(summary.total_minutes) : "0",
      icon: Clock,
      color: "text-amber-400",
      bgColor: "bg-amber-400/10",
      description: `${Math.round(summary?.avg_call_duration_secs ?? 0)}s avg`,
    },
    {
      name: "Active Users",
      value: summary ? formatNumber(summary.unique_users) : "0",
      icon: Users,
      color: "text-cyan-400",
      bgColor: "bg-cyan-400/10",
      description: "With calls",
    },
    {
      name: "Avg Revenue/Call",
      value: summary ? `$${(summary.avg_revenue_per_call ?? 0).toFixed(2)}` : "$0",
      icon: Percent,
      color: "text-pink-400",
      bgColor: "bg-pink-400/10",
      description: "Per completed call",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Revenue</h1>
          <p className="text-sm text-muted-foreground">
            Revenue analytics from call records
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Month Selector */}
          {availableMonths.length > 0 && (
            <Select value={selectedMonth} onValueChange={setSelectedMonth}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Select month" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Time</SelectItem>
                {availableMonths.map((month) => (
                  <SelectItem key={month.value} value={month.value}>
                    {month.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          {/* Reseed Button */}
          {hasData && (
            <Button
              onClick={() => reseedMutation.mutate()}
              disabled={isPending}
              variant="outline"
              size="icon"
              title="Reseed with fresh data"
            >
              <RotateCcw
                className={cn("h-4 w-4", reseedMutation.isPending && "animate-spin")}
              />
            </Button>
          )}

          {/* Seed Button */}
          <Button
            onClick={() => seedMutation.mutate()}
            disabled={isPending || hasData}
            variant={hasData ? "outline" : "default"}
          >
            <RefreshCw
              className={cn("mr-2 h-4 w-4", seedMutation.isPending && "animate-spin")}
            />
            {hasData ? "Data Seeded" : "Seed Data"}
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
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
                  <p className="text-xs text-muted-foreground">{stat.description}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Revenue Over Time */}
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardHeader>
            <CardTitle className="text-base font-medium">Revenue Over Time</CardTitle>
          </CardHeader>
          <CardContent>
            <RevenueOverTimeChart data={history} isLoading={historyLoading} />
          </CardContent>
        </Card>

        {/* Calls & Revenue */}
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardHeader>
            <CardTitle className="text-base font-medium">Calls & Profit</CardTitle>
          </CardHeader>
          <CardContent>
            <CallsRevenueChart data={history} isLoading={historyLoading} />
          </CardContent>
        </Card>
      </div>

      {/* Monthly Breakdown Table */}
      {hasData && (
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardHeader>
            <CardTitle className="text-base font-medium">Monthly Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/50">
                    <th className="py-3 text-left font-medium text-muted-foreground">Month</th>
                    <th className="py-3 text-right font-medium text-muted-foreground">Revenue</th>
                    <th className="py-3 text-right font-medium text-muted-foreground">Cost</th>
                    <th className="py-3 text-right font-medium text-muted-foreground">Profit</th>
                    <th className="py-3 text-right font-medium text-muted-foreground">Calls</th>
                    <th className="py-3 text-right font-medium text-muted-foreground">Minutes</th>
                    <th className="py-3 text-right font-medium text-muted-foreground">Users</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((month) => (
                    <tr key={`${month.year}-${month.month}`} className="border-b border-border/30 hover:bg-muted/20">
                      <td className="py-3 font-medium">{month.month_name} {month.year}</td>
                      <td className="py-3 text-right text-emerald-400">{formatCurrency(month.total_revenue)}</td>
                      <td className="py-3 text-right text-red-400">{formatCurrency(month.total_cost)}</td>
                      <td className="py-3 text-right text-blue-400">{formatCurrency(month.total_profit)}</td>
                      <td className="py-3 text-right">{formatNumber(month.total_calls)}</td>
                      <td className="py-3 text-right">{formatNumber(month.total_minutes)}</td>
                      <td className="py-3 text-right">{formatNumber(month.unique_users)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
