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
import type { MonthlyRevenue } from "@/lib/api/revenue";

interface CallsRevenueChartProps {
  data: MonthlyRevenue[];
  isLoading: boolean;
}

export function CallsRevenueChart({ data, isLoading }: CallsRevenueChartProps) {
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

  // Sort by date ascending and format for chart
  const chartData = [...data]
    .sort((a, b) => {
      if (a.year !== b.year) return a.year - b.year;
      return a.month - b.month;
    })
    .map((item) => ({
      month: `${item.month_name.slice(0, 3)} '${String(item.year).slice(-2)}`,
      calls: item.total_calls,
      completed: item.completed_calls,
      profit: item.total_profit,
    }));

  const formatNumber = (value: number) => {
    if (value >= 1000) {
      return `${(value / 1000).toFixed(1)}K`;
    }
    return String(value);
  };

  const formatCurrency = (value: number) => {
    if (value >= 1000) {
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
            yAxisId="left"
            tickFormatter={formatNumber}
            tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            width={50}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
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
            formatter={(value, name) => {
              const labels: Record<string, string> = {
                calls: "Total Calls",
                completed: "Completed",
                profit: "Profit",
              };
              const formatted = name === "profit"
                ? formatCurrency(Number(value ?? 0))
                : formatNumber(Number(value ?? 0));
              return [formatted, labels[String(name)] ?? String(name)];
            }}
          />
          <Legend
            wrapperStyle={{ paddingTop: "10px" }}
            formatter={(value: string) => {
              const labels: Record<string, string> = {
                calls: "Total Calls",
                completed: "Completed",
                profit: "Profit",
              };
              return labels[value] ?? value;
            }}
          />
          <Bar yAxisId="left" dataKey="calls" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
          <Bar yAxisId="left" dataKey="completed" fill="#10b981" radius={[4, 4, 0, 0]} />
          <Bar yAxisId="right" dataKey="profit" fill="#3b82f6" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
