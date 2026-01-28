"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  DollarSign,
  TrendingUp,
  Banknote,
  Building2,
  ArrowUpRight,
  ArrowDownRight,
  Receipt,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import {
  getIncomeSummary,
  getIncomeHistory,
  listClients,
  seedData,
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

  // Fetch income summary
  const { data: summary, isLoading: summaryLoading } = useQuery<IncomeSummary>({
    queryKey: ["income-summary"],
    queryFn: getIncomeSummary,
  });

  // Fetch income history
  const { data: history = [], isLoading: historyLoading } = useQuery<IncomeHistoryItem[]>({
    queryKey: ["income-history"],
    queryFn: getIncomeHistory,
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

  const isLoading = summaryLoading || historyLoading || clientsLoading;
  const hasData = clients.length > 0;

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
        <Button
          onClick={() => seedMutation.mutate()}
          disabled={seedMutation.isPending || hasData}
          variant={hasData ? "outline" : "default"}
        >
          <RefreshCw
            className={cn("mr-2 h-4 w-4", seedMutation.isPending && "animate-spin")}
          />
          {hasData ? "Data Seeded" : "Seed Data"}
        </Button>
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
