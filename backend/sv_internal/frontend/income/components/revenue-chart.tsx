"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { IncomeHistoryItem } from "@/lib/api/income";

interface RevenueChartProps {
  data: IncomeHistoryItem[];
  isLoading: boolean;
}

export function RevenueChart({ data, isLoading }: RevenueChartProps) {
  if (isLoading) {
    return (
      <div className="flex h-[300px] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="flex h-[300px] items-center justify-center text-muted-foreground">
        No data available. Click &quot;Seed Data&quot; to generate sample data.
      </div>
    );
  }

  // Sort by month ascending and format for chart
  const chartData = [...data]
    .sort((a, b) => a.month.localeCompare(b.month))
    .map((item) => ({
      month: new Date(item.month).toLocaleDateString("en-US", {
        month: "short",
        year: "2-digit",
      }),
      revenue: item.total_revenue,
      refunds: -item.total_refunds, // Negative to show as reduction
      chargebacks: -item.total_chargebacks, // Negative to show as reduction
      net: item.total_net_revenue,
    }));

  const formatCurrency = (value: number) => {
    const absValue = Math.abs(value);
    if (absValue >= 1000000) {
      return `$${(value / 1000000).toFixed(1)}M`;
    }
    if (absValue >= 1000) {
      return `$${(value / 1000).toFixed(0)}K`;
    }
    return `$${value}`;
  };

  return (
    <div className="h-[300px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-border/50" />
          <XAxis
            dataKey="month"
            tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tickFormatter={formatCurrency}
            tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            width={60}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "hsl(var(--card))",
              border: "1px solid hsl(var(--border))",
              borderRadius: "8px",
            }}
            labelStyle={{ color: "hsl(var(--foreground))" }}
            formatter={(value: number, name: string) => {
              const labels: Record<string, string> = {
                revenue: "Revenue",
                refunds: "Refunds",
                chargebacks: "Chargebacks",
                net: "Net Revenue",
              };
              return [formatCurrency(Math.abs(value)), labels[name] || name];
            }}
          />
          <Legend
            wrapperStyle={{ paddingTop: "10px" }}
            formatter={(value: string) => {
              const labels: Record<string, string> = {
                revenue: "Revenue",
                refunds: "Refunds",
                chargebacks: "Chargebacks",
              };
              return labels[value] || value;
            }}
          />
          <Bar dataKey="revenue" fill="#10b981" radius={[4, 4, 0, 0]} />
          <Bar dataKey="refunds" fill="#f59e0b" radius={[4, 4, 0, 0]} />
          <Bar dataKey="chargebacks" fill="#ef4444" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
