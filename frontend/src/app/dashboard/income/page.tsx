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
import { RefreshCw, RotateCcw } from "lucide-react";
import { cn, formatMonthYear } from "@/lib/utils";
import { toast } from "sonner";
import {
  getIncomeSummary,
  getIncomeHistory,
  listClients,
  seedData,
  reseedData,
  type IncomeSummary,
  type IncomeHistoryItem,
  type SimClientListItem,
} from "@/lib/api/income";
import { IncomeStatsCards } from "./components/income-stats-cards";
import { MrrChart } from "./components/mrr-chart";
import { RevenueChart } from "./components/revenue-chart";
import { ClientTable } from "./components/client-table";
import { ClientDetailDialog } from "./components/client-detail";

export default function IncomePage() {
  const queryClient = useQueryClient();
  const [selectedClientId, setSelectedClientId] = useState<string | null>(null);
  const [selectedMonth, setSelectedMonth] = useState<string>("current");

  // Fetch income history first (to get available months)
  const { data: history = [], isLoading: historyLoading } = useQuery<IncomeHistoryItem[]>({
    queryKey: ["income-history"],
    queryFn: getIncomeHistory,
  });

  // Compute available months from history, sorted newest first
  const availableMonths = useMemo(() => {
    if (history.length === 0) return [];
    return [...history]
      .sort((a, b) => b.month.localeCompare(a.month))
      .map((item) => ({
        value: item.month,
        label: formatMonthYear(item.month),
      }));
  }, [history]);

  // Set default to most recent month when history loads
  const effectiveMonth = selectedMonth === "current" && availableMonths.length > 0
    ? (availableMonths[0]?.value ?? "current")
    : selectedMonth;

  // Fetch income summary with optional month filter
  const { data: summary, isLoading: summaryLoading } = useQuery<IncomeSummary>({
    queryKey: ["income-summary", effectiveMonth],
    queryFn: () => getIncomeSummary(effectiveMonth !== "current" ? effectiveMonth : undefined),
    enabled: effectiveMonth === "current" || availableMonths.length > 0,
  });

  // Fetch clients
  const { data: clients = [], isLoading: clientsLoading } = useQuery<SimClientListItem[]>({
    queryKey: ["internal-clients"],
    queryFn: () => listClients(),
  });

  // Seed mutation
  const seedMutation = useMutation({
    mutationFn: seedData,
    onSuccess: (data) => {
      toast.success(data.message);
      // Invalidate all queries to refresh data
      void queryClient.invalidateQueries({ queryKey: ["income-summary"] });
      void queryClient.invalidateQueries({ queryKey: ["income-history"] });
      void queryClient.invalidateQueries({ queryKey: ["internal-clients"] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to seed data: ${error.message}`);
    },
  });

  // Reseed mutation
  const reseedMutation = useMutation({
    mutationFn: reseedData,
    onSuccess: (data) => {
      toast.success(data.message);
      setSelectedMonth("current"); // Reset to current month
      // Invalidate all queries to refresh data
      void queryClient.invalidateQueries({ queryKey: ["income-summary"] });
      void queryClient.invalidateQueries({ queryKey: ["income-history"] });
      void queryClient.invalidateQueries({ queryKey: ["internal-clients"] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to reseed data: ${error.message}`);
    },
  });

  const isLoading = summaryLoading || historyLoading || clientsLoading;
  const hasData = clients.length > 0;
  const isPending = seedMutation.isPending || reseedMutation.isPending;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Income</h1>
          <p className="text-sm text-muted-foreground">
            Revenue analytics and client performance metrics
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
                <SelectItem value="current">Current (Live)</SelectItem>
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
      <IncomeStatsCards summary={summary} isLoading={isLoading} />

      {/* Charts Row */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* MRR Over Time */}
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardHeader>
            <CardTitle className="text-base font-medium">MRR Over Time</CardTitle>
          </CardHeader>
          <CardContent>
            <MrrChart data={history} isLoading={historyLoading} />
          </CardContent>
        </Card>

        {/* Revenue Breakdown */}
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardHeader>
            <CardTitle className="text-base font-medium">Revenue Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <RevenueChart data={history} isLoading={historyLoading} />
          </CardContent>
        </Card>
      </div>

      {/* Client Table */}
      <Card className="border-border/50 bg-card/50 backdrop-blur">
        <CardHeader>
          <CardTitle className="text-base font-medium">Clients</CardTitle>
        </CardHeader>
        <CardContent>
          <ClientTable
            clients={clients}
            isLoading={clientsLoading}
            onSelectClient={setSelectedClientId}
          />
        </CardContent>
      </Card>

      {/* Client Detail Dialog */}
      <ClientDetailDialog
        clientId={selectedClientId}
        open={!!selectedClientId}
        onOpenChange={(open) => !open && setSelectedClientId(null)}
      />
    </div>
  );
}
