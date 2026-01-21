"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, Phone, CheckCircle2, ExternalLink, ArrowRight, ChevronLeft } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

type Provider = "telnyx" | "twilio" | null;

export default function OnboardingTelephonyPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [selectedProvider, setSelectedProvider] = useState<Provider>(null);
  const [formData, setFormData] = useState({
    telnyx_api_key: "",
    telnyx_public_key: "",
    twilio_account_sid: "",
    twilio_auth_token: "",
  });

  const configureTelephony = useMutation({
    mutationFn: async (data: { provider: Provider } & typeof formData) => {
      const response = await api.post("/api/v1/onboarding/telephony", data);
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["onboarding-status"] });
      toast.success("Telephony configured!");
      router.push("/onboarding/ai-providers");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to configure telephony");
    },
  });

  const skipStep = useMutation({
    mutationFn: async () => {
      const response = await api.post("/api/v1/onboarding/skip-step");
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["onboarding-status"] });
      toast.info("You can configure telephony later in settings");
      router.push("/onboarding/ai-providers");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to skip step");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProvider) return;
    configureTelephony.mutate({
      provider: selectedProvider,
      ...formData,
    });
  };

  const isValid =
    selectedProvider === "telnyx"
      ? formData.telnyx_api_key.trim() !== ""
      : selectedProvider === "twilio"
        ? formData.twilio_account_sid.trim() !== "" && formData.twilio_auth_token.trim() !== ""
        : false;

  return (
    <Card className="border-white/10 bg-white/[0.02]">
      <CardHeader className="text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-500/20 to-teal-500/10">
          <Phone className="h-8 w-8 text-emerald-400" />
        </div>
        <CardTitle className="text-2xl">Connect Your Phone System</CardTitle>
        <CardDescription>
          Choose your telephony provider to enable voice calls for your AI agents
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Provider Selection */}
          <div className="grid grid-cols-2 gap-4">
            <button
              type="button"
              onClick={() => setSelectedProvider("telnyx")}
              className={cn(
                "relative flex flex-col items-center rounded-xl border-2 p-6 text-left transition-all hover:border-emerald-500/50",
                selectedProvider === "telnyx"
                  ? "border-emerald-500 bg-emerald-500/10"
                  : "border-white/10 bg-white/[0.02]"
              )}
            >
              {selectedProvider === "telnyx" && (
                <CheckCircle2 className="absolute right-3 top-3 h-5 w-5 text-emerald-500" />
              )}
              <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-lg bg-emerald-500/20">
                <span className="text-xl font-bold text-emerald-400">T</span>
              </div>
              <span className="font-semibold">Telnyx</span>
              <span className="mt-1 text-xs text-emerald-400">Recommended</span>
              <span className="mt-2 text-center text-xs text-muted-foreground">
                Best rates for voice AI. Easy setup with global coverage.
              </span>
            </button>

            <button
              type="button"
              onClick={() => setSelectedProvider("twilio")}
              className={cn(
                "relative flex flex-col items-center rounded-xl border-2 p-6 text-left transition-all hover:border-red-500/50",
                selectedProvider === "twilio"
                  ? "border-red-500 bg-red-500/10"
                  : "border-white/10 bg-white/[0.02]"
              )}
            >
              {selectedProvider === "twilio" && (
                <CheckCircle2 className="absolute right-3 top-3 h-5 w-5 text-red-500" />
              )}
              <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-lg bg-red-500/20">
                <span className="text-xl font-bold text-red-400">T</span>
              </div>
              <span className="font-semibold">Twilio</span>
              <span className="mt-1 text-xs text-muted-foreground">Already have Twilio?</span>
              <span className="mt-2 text-center text-xs text-muted-foreground">
                Connect your existing Twilio account.
              </span>
            </button>
          </div>

          {/* Telnyx Fields */}
          {selectedProvider === "telnyx" && (
            <div className="space-y-4 rounded-xl border border-white/10 bg-white/[0.02] p-4">
              <div className="flex items-center justify-between">
                <h3 className="font-medium">Telnyx Credentials</h3>
                <a
                  href="https://portal.telnyx.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-xs text-emerald-400 hover:underline"
                >
                  Get API Key <ExternalLink className="h-3 w-3" />
                </a>
              </div>

              <div className="space-y-2">
                <Label htmlFor="telnyx_api_key">API Key *</Label>
                <Input
                  id="telnyx_api_key"
                  type="password"
                  placeholder="KEY..."
                  value={formData.telnyx_api_key}
                  onChange={(e) => setFormData({ ...formData, telnyx_api_key: e.target.value })}
                  required
                />
                <p className="text-xs text-muted-foreground">
                  Found in Telnyx Portal → API Keys
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="telnyx_public_key">Public Key (Optional)</Label>
                <Input
                  id="telnyx_public_key"
                  type="password"
                  placeholder="KEY..."
                  value={formData.telnyx_public_key}
                  onChange={(e) => setFormData({ ...formData, telnyx_public_key: e.target.value })}
                />
                <p className="text-xs text-muted-foreground">
                  Used for webhook verification
                </p>
              </div>
            </div>
          )}

          {/* Twilio Fields */}
          {selectedProvider === "twilio" && (
            <div className="space-y-4 rounded-xl border border-white/10 bg-white/[0.02] p-4">
              <div className="flex items-center justify-between">
                <h3 className="font-medium">Twilio Credentials</h3>
                <a
                  href="https://console.twilio.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-xs text-red-400 hover:underline"
                >
                  Open Console <ExternalLink className="h-3 w-3" />
                </a>
              </div>

              <div className="space-y-2">
                <Label htmlFor="twilio_account_sid">Account SID *</Label>
                <Input
                  id="twilio_account_sid"
                  type="text"
                  placeholder="AC..."
                  value={formData.twilio_account_sid}
                  onChange={(e) => setFormData({ ...formData, twilio_account_sid: e.target.value })}
                  required
                />
                <p className="text-xs text-muted-foreground">
                  Found on your Twilio Console dashboard
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="twilio_auth_token">Auth Token *</Label>
                <Input
                  id="twilio_auth_token"
                  type="password"
                  placeholder="Your auth token"
                  value={formData.twilio_auth_token}
                  onChange={(e) => setFormData({ ...formData, twilio_auth_token: e.target.value })}
                  required
                />
                <p className="text-xs text-muted-foreground">
                  Found on your Twilio Console dashboard
                </p>
              </div>
            </div>
          )}

          {/* Info Box */}
          <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-4">
            <h4 className="mb-2 flex items-center gap-2 text-sm font-medium text-blue-400">
              💡 Why do I need this?
            </h4>
            <p className="text-xs text-muted-foreground">
              SpaceVoice uses your telephony provider account to make and receive calls.
              You only pay for what you use directly to your provider - no markup from us
              on call costs.
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <Button
              type="button"
              variant="ghost"
              onClick={() => router.push("/onboarding")}
              className="gap-2"
            >
              <ChevronLeft className="h-4 w-4" />
              Back
            </Button>

            <Button
              type="button"
              variant="outline"
              onClick={() => skipStep.mutate()}
              disabled={skipStep.isPending}
              className="flex-1"
            >
              {skipStep.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              Skip for now
            </Button>

            <Button
              type="submit"
              disabled={!isValid || configureTelephony.isPending}
              className="flex-1 gap-2"
            >
              {configureTelephony.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <>
                  Continue
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
