"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import {
  getClient,
  getClientHistory,
  type SimClientDetail,
  type ClientHistoryItem,
} from "@/lib/api/income";
import {
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface ClientDetailDialogProps {
  clientId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ClientDetailDialog({
  clientId,
  open,
  onOpenChange,
}: ClientDetailDialogProps) {
  // Fetch client details
  const { data: client, isLoading: clientLoading } = useQuery<SimClientDetail>({
    queryKey: ["internal-client", clientId],
    queryFn: () => getClient(clientId as string),
    enabled: !!clientId,
  });

  // Fetch client history
  const { data: history = [], isLoading: historyLoading } = useQuery<ClientHistoryItem[]>({
    queryKey: ["internal-client-history", clientId],
    queryFn: () => getClientHistory(clientId as string),
    enabled: !!clientId,
  });

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "N/A";
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const statusColors: Record<string, string> = {
    active: "bg-emerald-400/10 text-emerald-400",
    churned: "bg-red-400/10 text-red-400",
    paused: "bg-amber-400/10 text-amber-400",
  };

  const isLoading = clientLoading || historyLoading;

  // Chart data
  const chartData = [...history]
    .sort((a, b) => a.month.localeCompare(b.month))
    .map((item) => ({
      month: new Date(item.month).toLocaleDateString("en-US", {
        month: "short",
      }),
      mrr: item.mrr,
      calls: item.calls_handled,
    }));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
        {isLoading ? (
          <div className="flex h-[400px] items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : client ? (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-3">
                <span className="font-mono">{client.masked_id}</span>
                <span className="text-muted-foreground">·</span>
                <span>{client.descriptor}</span>
                <span
                  className={cn(
                    "ml-2 inline-flex rounded-full px-2 py-0.5 text-xs font-medium capitalize",
                    statusColors[client.status]
                  )}
                >
                  {client.status}
                </span>
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-6">
              {/* Identity Section */}
              <div>
                <h4 className="mb-3 text-sm font-medium text-muted-foreground">Identity</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Full Client ID</p>
                    <p className="font-mono font-medium">{client.client_id}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Industry</p>
                    <p className="font-medium">{client.industry}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Size</p>
                    <p className="font-medium capitalize">{client.client_size}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Onboarded</p>
                    <p className="font-medium">{formatDate(client.onboarded_at)}</p>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Payment Section */}
              <div>
                <h4 className="mb-3 text-sm font-medium text-muted-foreground">Payment</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Processor</p>
                    <p className="font-medium capitalize">{client.processor}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Billing Cycle</p>
                    <p className="font-medium capitalize">{client.billing_cycle}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Payment Method</p>
                    <p className="font-medium uppercase">{client.payment_method_type}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Last Charge</p>
                    <p className="font-medium">
                      {formatDate(client.last_charge_date)} -{" "}
                      <span
                        className={cn(
                          "capitalize",
                          client.last_charge_status === "succeeded"
                            ? "text-emerald-400"
                            : "text-red-400"
                        )}
                      >
                        {client.last_charge_status}
                      </span>
                    </p>
                  </div>
                  <div className="col-span-2">
                    <p className="text-muted-foreground">Customer ID</p>
                    <p className="font-mono text-xs">{client.customer_id}</p>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Revenue Section */}
              <div>
                <h4 className="mb-3 text-sm font-medium text-muted-foreground">Revenue</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">MRR</p>
                    <p className="text-lg font-semibold text-emerald-400">
                      {formatCurrency(client.mrr)}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">ARR</p>
                    <p className="text-lg font-semibold text-blue-400">
                      {formatCurrency(client.arr)}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Setup Fee (one-time)</p>
                    <p className="font-medium text-cyan-400">
                      {formatCurrency(client.setup_fee)}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">First Month Total</p>
                    <p className="font-medium">{formatCurrency(client.total_first_month)}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Total Paid</p>
                    <p className="font-medium">{formatCurrency(client.paid_amount)}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Net Revenue</p>
                    <p className="font-semibold text-violet-400">
                      {formatCurrency(client.net_revenue)}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Refunds</p>
                    <p className="font-medium text-amber-400">
                      {formatCurrency(client.refunded_amount)}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Chargebacks</p>
                    <p className="font-medium text-red-400">
                      {formatCurrency(client.chargebacks_amount)}
                    </p>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Payment Counts */}
              <div>
                <h4 className="mb-3 text-sm font-medium text-muted-foreground">
                  Payment History
                </h4>
                <div className="grid grid-cols-4 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Invoices</p>
                    <p className="font-medium">{client.invoice_count}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Payments</p>
                    <p className="font-medium">{client.payment_count}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Successful</p>
                    <p className="font-medium text-emerald-400">
                      {client.successful_payments}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Failed</p>
                    <p className="font-medium text-red-400">{client.failed_payments}</p>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Usage Section */}
              <div>
                <h4 className="mb-3 text-sm font-medium text-muted-foreground">
                  Usage (30 days)
                </h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Calls Received</p>
                    <p className="font-medium">{client.calls_received_30d.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Calls Handled</p>
                    <p className="font-medium">{client.calls_handled_30d.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Avg Duration</p>
                    <p className="font-medium">
                      {Math.round(client.avg_call_duration / 60)}m{" "}
                      {Math.round(client.avg_call_duration % 60)}s
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Total Minutes</p>
                    <p className="font-medium">
                      {Math.round(client.total_minutes_30d).toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>

              {/* History Chart */}
              {chartData.length > 0 && (
                <>
                  <Separator />
                  <div>
                    <h4 className="mb-3 text-sm font-medium text-muted-foreground">
                      6-Month Trend
                    </h4>
                    <div className="h-[200px] w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart
                          data={chartData}
                          margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" className="stroke-border/50" />
                          <XAxis
                            dataKey="month"
                            tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                            tickLine={false}
                            axisLine={false}
                          />
                          <YAxis
                            yAxisId="mrr"
                            tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                            tickLine={false}
                            axisLine={false}
                            width={50}
                            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                          />
                          <YAxis
                            yAxisId="calls"
                            orientation="right"
                            tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                            tickLine={false}
                            axisLine={false}
                            width={40}
                          />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: "hsl(var(--card))",
                              border: "1px solid hsl(var(--border))",
                              borderRadius: "8px",
                            }}
                          />
                          <Legend wrapperStyle={{ paddingTop: "10px" }} />
                          <Line
                            yAxisId="mrr"
                            type="monotone"
                            dataKey="mrr"
                            stroke="#10b981"
                            strokeWidth={2}
                            name="MRR"
                            dot={false}
                          />
                          <Bar
                            yAxisId="calls"
                            dataKey="calls"
                            fill="#6366f1"
                            opacity={0.6}
                            name="Calls"
                            radius={[2, 2, 0, 0]}
                          />
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </>
              )}
            </div>
          </>
        ) : (
          <div className="flex h-[200px] items-center justify-center text-muted-foreground">
            Client not found
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
