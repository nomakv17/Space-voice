"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { SimClientListItem } from "@/lib/api/income";

interface ClientTableProps {
  clients: SimClientListItem[];
  isLoading: boolean;
  onSelectClient: (clientId: string) => void;
}

type StatusFilter = "all" | "active" | "churned" | "paused";
type SizeFilter = "all" | "enterprise" | "medium";

export function ClientTable({ clients, isLoading, onSelectClient }: ClientTableProps) {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [sizeFilter, setSizeFilter] = useState<SizeFilter>("all");
  const [sortBy, setSortBy] = useState<"mrr" | "net_revenue" | "calls">("mrr");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  // Filter and sort clients
  const filteredClients = clients
    .filter((client) => {
      if (statusFilter !== "all" && client.status !== statusFilter) return false;
      if (sizeFilter !== "all" && client.client_size !== sizeFilter) return false;
      return true;
    })
    .sort((a, b) => {
      let aVal: number, bVal: number;
      switch (sortBy) {
        case "mrr":
          aVal = a.mrr;
          bVal = b.mrr;
          break;
        case "net_revenue":
          aVal = a.net_revenue;
          bVal = b.net_revenue;
          break;
        case "calls":
          aVal = a.calls_handled_30d;
          bVal = b.calls_handled_30d;
          break;
        default:
          aVal = a.mrr;
          bVal = b.mrr;
      }
      return sortDir === "desc" ? bVal - aVal : aVal - bVal;
    });

  const handleSort = (column: "mrr" | "net_revenue" | "calls") => {
    if (sortBy === column) {
      setSortDir(sortDir === "desc" ? "asc" : "desc");
    } else {
      setSortBy(column);
      setSortDir("desc");
    }
  };

  const statusColors: Record<string, string> = {
    active: "bg-emerald-400/10 text-emerald-400",
    churned: "bg-red-400/10 text-red-400",
    paused: "bg-amber-400/10 text-amber-400",
  };

  const chargeStatusColors: Record<string, string> = {
    succeeded: "text-emerald-400",
    failed: "text-red-400",
    pending: "text-amber-400",
  };

  if (isLoading) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (clients.length === 0) {
    return (
      <div className="flex h-[400px] items-center justify-center text-muted-foreground">
        No clients found. Click &quot;Seed Data&quot; to generate sample data.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <div className="flex gap-1 rounded-lg bg-muted/50 p-1">
          {(["all", "active", "churned", "paused"] as const).map((status) => (
            <Button
              key={status}
              variant="ghost"
              size="sm"
              className={cn(
                "h-7 px-3 text-xs capitalize",
                statusFilter === status && "bg-background shadow-sm"
              )}
              onClick={() => setStatusFilter(status)}
            >
              {status}
            </Button>
          ))}
        </div>
        <div className="flex gap-1 rounded-lg bg-muted/50 p-1">
          {(["all", "enterprise", "medium"] as const).map((size) => (
            <Button
              key={size}
              variant="ghost"
              size="sm"
              className={cn(
                "h-7 px-3 text-xs capitalize",
                sizeFilter === size && "bg-background shadow-sm"
              )}
              onClick={() => setSizeFilter(size)}
            >
              {size}
            </Button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-border/50">
        <table className="w-full">
          <thead className="bg-muted/30">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                Client
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                Size
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                Tier
              </th>
              <th
                className="cursor-pointer px-4 py-3 text-right text-xs font-medium text-muted-foreground hover:text-foreground"
                onClick={() => handleSort("mrr")}
              >
                MRR {sortBy === "mrr" && (sortDir === "desc" ? "↓" : "↑")}
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground">
                Setup Fee
              </th>
              <th
                className="cursor-pointer px-4 py-3 text-right text-xs font-medium text-muted-foreground hover:text-foreground"
                onClick={() => handleSort("net_revenue")}
              >
                Net Revenue {sortBy === "net_revenue" && (sortDir === "desc" ? "↓" : "↑")}
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                Status
              </th>
              <th
                className="cursor-pointer px-4 py-3 text-right text-xs font-medium text-muted-foreground hover:text-foreground"
                onClick={() => handleSort("calls")}
              >
                Calls (30d) {sortBy === "calls" && (sortDir === "desc" ? "↓" : "↑")}
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                Last Charge
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {filteredClients.map((client) => (
              <tr
                key={client.id}
                className="cursor-pointer transition-colors hover:bg-muted/30"
                onClick={() => onSelectClient(client.id)}
              >
                <td className="px-4 py-3">
                  <div>
                    <p className="font-mono text-sm font-medium">{client.masked_id}</p>
                    <p className="text-xs text-muted-foreground">{client.descriptor}</p>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className="text-sm capitalize">{client.client_size}</span>
                </td>
                <td className="px-4 py-3">
                  <span className="text-sm capitalize">{client.pricing_tier}</span>
                </td>
                <td className="px-4 py-3 text-right font-mono text-sm">
                  {formatCurrency(client.mrr)}
                </td>
                <td className="px-4 py-3 text-right font-mono text-sm text-muted-foreground">
                  {formatCurrency(client.setup_fee)}
                </td>
                <td className="px-4 py-3 text-right font-mono text-sm">
                  {formatCurrency(client.net_revenue)}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={cn(
                      "inline-flex rounded-full px-2 py-0.5 text-xs font-medium capitalize",
                      statusColors[client.status]
                    )}
                  >
                    {client.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-right font-mono text-sm">
                  {client.calls_handled_30d.toLocaleString()}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={cn(
                      "text-sm capitalize",
                      chargeStatusColors[client.last_charge_status]
                    )}
                  >
                    {client.last_charge_status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Summary */}
      <div className="text-xs text-muted-foreground">
        Showing {filteredClients.length} of {clients.length} clients
      </div>
    </div>
  );
}
