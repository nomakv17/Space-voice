"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  Loader2,
  DollarSign,
  Percent,
  TrendingUp,
  Sparkles,
  Edit,
} from "lucide-react";
import { toast } from "sonner";

interface PricingConfig {
  id: number;
  tier_id: string;
  tier_name: string;
  description: string | null;
  base_llm_cost_per_minute: number;
  base_stt_cost_per_minute: number;
  base_tts_cost_per_minute: number;
  base_telephony_cost_per_minute: number;
  total_base_cost_per_minute: number;
  ai_markup_percentage: number;
  telephony_markup_percentage: number;
  final_ai_price_per_minute: number;
  final_telephony_price_per_minute: number;
  final_total_price_per_minute: number;
  profit_per_minute: number;
  profit_margin_percentage: number;
  updated_at: string;
}

interface PricingUpdateForm {
  ai_markup_percentage: string;
  telephony_markup_percentage: string;
  base_llm_cost_per_minute: string;
  base_stt_cost_per_minute: string;
  base_tts_cost_per_minute: string;
  base_telephony_cost_per_minute: string;
}

export default function PricingPage() {
  const queryClient = useQueryClient();
  const [editingConfig, setEditingConfig] = useState<PricingConfig | null>(null);
  const [editForm, setEditForm] = useState<PricingUpdateForm>({
    ai_markup_percentage: "",
    telephony_markup_percentage: "",
    base_llm_cost_per_minute: "",
    base_stt_cost_per_minute: "",
    base_tts_cost_per_minute: "",
    base_telephony_cost_per_minute: "",
  });

  const { data: pricingConfigs, isLoading } = useQuery<PricingConfig[]>({
    queryKey: ["pricing-configs"],
    queryFn: async () => {
      const response = await api.get("/api/v1/admin/pricing");
      return response.data;
    },
  });

  const seedDefaults = useMutation({
    mutationFn: async () => {
      const response = await api.post("/api/v1/admin/pricing/seed-defaults");
      return response.data;
    },
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ["pricing-configs"] });
      toast.success(data.message);
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to seed pricing configs");
    },
  });

  const updatePricing = useMutation({
    mutationFn: async ({
      tier_id,
      data,
    }: {
      tier_id: string;
      data: Partial<PricingUpdateForm>;
    }) => {
      // Convert string values to numbers
      const payload: Record<string, number> = {};
      if (data.ai_markup_percentage)
        payload.ai_markup_percentage = parseFloat(data.ai_markup_percentage);
      if (data.telephony_markup_percentage)
        payload.telephony_markup_percentage = parseFloat(data.telephony_markup_percentage);
      if (data.base_llm_cost_per_minute)
        payload.base_llm_cost_per_minute = parseFloat(data.base_llm_cost_per_minute);
      if (data.base_stt_cost_per_minute)
        payload.base_stt_cost_per_minute = parseFloat(data.base_stt_cost_per_minute);
      if (data.base_tts_cost_per_minute)
        payload.base_tts_cost_per_minute = parseFloat(data.base_tts_cost_per_minute);
      if (data.base_telephony_cost_per_minute)
        payload.base_telephony_cost_per_minute = parseFloat(data.base_telephony_cost_per_minute);

      const response = await api.put(`/api/v1/admin/pricing/${tier_id}`, payload);
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["pricing-configs"] });
      setEditingConfig(null);
      toast.success("Pricing updated successfully!");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to update pricing");
    },
  });

  const openEditDialog = (config: PricingConfig) => {
    setEditingConfig(config);
    setEditForm({
      ai_markup_percentage: config.ai_markup_percentage.toString(),
      telephony_markup_percentage: config.telephony_markup_percentage.toString(),
      base_llm_cost_per_minute: config.base_llm_cost_per_minute.toString(),
      base_stt_cost_per_minute: config.base_stt_cost_per_minute.toString(),
      base_tts_cost_per_minute: config.base_tts_cost_per_minute.toString(),
      base_telephony_cost_per_minute: config.base_telephony_cost_per_minute.toString(),
    });
  };

  const handleUpdate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingConfig) return;
    updatePricing.mutate({ tier_id: editingConfig.tier_id, data: editForm });
  };

  const formatCurrency = (value: number) => {
    return `$${value.toFixed(4)}`;
  };

  const formatPercent = (value: number) => {
    return `${value.toFixed(1)}%`;
  };

  // Calculate totals
  const averageMargin =
    pricingConfigs && pricingConfigs.length > 0
      ? pricingConfigs.reduce((sum, c) => sum + c.profit_margin_percentage, 0) /
        pricingConfigs.length
      : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Pricing Configuration</h1>
          <p className="text-muted-foreground">
            Manage AI and telephony pricing tiers with configurable margins
          </p>
        </div>
        {(!pricingConfigs || pricingConfigs.length === 0) && (
          <Button
            onClick={() => seedDefaults.mutate()}
            disabled={seedDefaults.isPending}
            className="gap-2"
          >
            {seedDefaults.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            Seed Default Pricing
          </Button>
        )}
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg. Profit Margin</CardTitle>
            <TrendingUp className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-500">
              {formatPercent(averageMargin)}
            </div>
            <p className="text-xs text-muted-foreground">Across all tiers</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Tiers</CardTitle>
            <DollarSign className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{pricingConfigs?.length ?? 0}</div>
            <p className="text-xs text-muted-foreground">Pricing configurations</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Default AI Markup</CardTitle>
            <Percent className="h-4 w-4 text-violet-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">30%</div>
            <p className="text-xs text-muted-foreground">Suggested margin</p>
          </CardContent>
        </Card>
      </div>

      {/* Pricing Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Pricing Tiers
          </CardTitle>
          <CardDescription>
            Configure base costs and markups for each pricing tier
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : pricingConfigs && pricingConfigs.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tier</TableHead>
                  <TableHead className="text-right">Base Cost</TableHead>
                  <TableHead className="text-right">AI Markup</TableHead>
                  <TableHead className="text-right">Tel. Markup</TableHead>
                  <TableHead className="text-right">Final Price</TableHead>
                  <TableHead className="text-right">Profit/Min</TableHead>
                  <TableHead className="text-right">Margin</TableHead>
                  <TableHead className="w-[80px]">Edit</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pricingConfigs.map((config) => (
                  <TableRow key={config.id}>
                    <TableCell>
                      <div>
                        <p className="font-medium">{config.tier_name}</p>
                        <p className="text-xs text-muted-foreground">{config.tier_id}</p>
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm">
                      {formatCurrency(config.total_base_cost_per_minute)}
                    </TableCell>
                    <TableCell className="text-right">
                      <Badge variant="outline" className="font-mono">
                        {formatPercent(config.ai_markup_percentage)}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Badge variant="outline" className="font-mono">
                        {formatPercent(config.telephony_markup_percentage)}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm font-semibold">
                      {formatCurrency(config.final_total_price_per_minute)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm text-emerald-500">
                      +{formatCurrency(config.profit_per_minute)}
                    </TableCell>
                    <TableCell className="text-right">
                      <Badge
                        className={
                          config.profit_margin_percentage >= 25
                            ? "bg-emerald-500/20 text-emerald-500"
                            : config.profit_margin_percentage >= 15
                              ? "bg-amber-500/20 text-amber-500"
                              : "bg-red-500/20 text-red-500"
                        }
                      >
                        {formatPercent(config.profit_margin_percentage)}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => openEditDialog(config)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <DollarSign className="mb-4 h-12 w-12 text-muted-foreground/50" />
              <h3 className="mb-2 text-lg font-medium">No pricing configured</h3>
              <p className="mb-4 text-sm text-muted-foreground">
                Seed the default pricing configurations to get started
              </p>
              <Button
                onClick={() => seedDefaults.mutate()}
                disabled={seedDefaults.isPending}
                className="gap-2"
              >
                {seedDefaults.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4" />
                )}
                Seed Default Pricing
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Cost Breakdown Info */}
      {pricingConfigs && pricingConfigs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Cost Breakdown</CardTitle>
            <CardDescription>
              Detailed view of what goes into each price tier
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {pricingConfigs.map((config) => (
                <div
                  key={config.id}
                  className="rounded-lg border border-white/10 bg-white/[0.02] p-4"
                >
                  <div className="mb-3 flex items-center justify-between">
                    <h4 className="font-semibold">{config.tier_name}</h4>
                    <span className="text-sm text-muted-foreground">
                      {config.description}
                    </span>
                  </div>
                  <div className="grid gap-4 md:grid-cols-4">
                    <div>
                      <p className="text-xs text-muted-foreground">LLM Cost</p>
                      <p className="font-mono text-sm">
                        {formatCurrency(config.base_llm_cost_per_minute)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">STT Cost</p>
                      <p className="font-mono text-sm">
                        {formatCurrency(config.base_stt_cost_per_minute)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">TTS Cost</p>
                      <p className="font-mono text-sm">
                        {formatCurrency(config.base_tts_cost_per_minute)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Telephony Cost</p>
                      <p className="font-mono text-sm">
                        {formatCurrency(config.base_telephony_cost_per_minute)}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Edit Dialog */}
      <Dialog open={!!editingConfig} onOpenChange={(open) => !open && setEditingConfig(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Edit {editingConfig?.tier_name} Pricing</DialogTitle>
            <DialogDescription>
              Adjust base costs and markup percentages. Final prices will be recalculated
              automatically.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleUpdate} className="space-y-4">
            <div className="space-y-3 rounded-lg border border-white/10 bg-white/[0.02] p-4">
              <h4 className="text-sm font-medium">Markup Percentages</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="ai_markup">AI Markup %</Label>
                  <Input
                    id="ai_markup"
                    type="number"
                    step="0.1"
                    min="0"
                    max="500"
                    value={editForm.ai_markup_percentage}
                    onChange={(e) =>
                      setEditForm({ ...editForm, ai_markup_percentage: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="telephony_markup">Telephony Markup %</Label>
                  <Input
                    id="telephony_markup"
                    type="number"
                    step="0.1"
                    min="0"
                    max="500"
                    value={editForm.telephony_markup_percentage}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        telephony_markup_percentage: e.target.value,
                      })
                    }
                  />
                </div>
              </div>
            </div>

            <div className="space-y-3 rounded-lg border border-white/10 bg-white/[0.02] p-4">
              <h4 className="text-sm font-medium">Base Costs (per minute)</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="llm_cost">LLM Cost $</Label>
                  <Input
                    id="llm_cost"
                    type="number"
                    step="0.0001"
                    min="0"
                    value={editForm.base_llm_cost_per_minute}
                    onChange={(e) =>
                      setEditForm({ ...editForm, base_llm_cost_per_minute: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="stt_cost">STT Cost $</Label>
                  <Input
                    id="stt_cost"
                    type="number"
                    step="0.0001"
                    min="0"
                    value={editForm.base_stt_cost_per_minute}
                    onChange={(e) =>
                      setEditForm({ ...editForm, base_stt_cost_per_minute: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tts_cost">TTS Cost $</Label>
                  <Input
                    id="tts_cost"
                    type="number"
                    step="0.0001"
                    min="0"
                    value={editForm.base_tts_cost_per_minute}
                    onChange={(e) =>
                      setEditForm({ ...editForm, base_tts_cost_per_minute: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="telephony_cost">Telephony Cost $</Label>
                  <Input
                    id="telephony_cost"
                    type="number"
                    step="0.0001"
                    min="0"
                    value={editForm.base_telephony_cost_per_minute}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        base_telephony_cost_per_minute: e.target.value,
                      })
                    }
                  />
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setEditingConfig(null)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={updatePricing.isPending}>
                {updatePricing.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Save Changes
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
