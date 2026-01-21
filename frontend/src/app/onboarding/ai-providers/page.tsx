"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, Sparkles, CheckCircle2, ExternalLink, ArrowRight, ChevronLeft, Zap } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

type AIMode = "platform" | "byok";

export default function OnboardingAIProvidersPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [aiMode, setAIMode] = useState<AIMode>("platform");
  const [formData, setFormData] = useState({
    openai_api_key: "",
    anthropic_api_key: "",
  });

  const configureAI = useMutation({
    mutationFn: async (data: { use_platform_ai: boolean } & typeof formData) => {
      const response = await api.post("/api/v1/onboarding/ai-config", data);
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["onboarding-status"] });
      toast.success("AI configuration saved!");
      router.push("/onboarding/workspace");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to configure AI");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    configureAI.mutate({
      use_platform_ai: aiMode === "platform",
      ...formData,
    });
  };

  const isValid = aiMode === "platform" || (
    formData.openai_api_key.trim() !== "" || formData.anthropic_api_key.trim() !== ""
  );

  return (
    <Card className="border-white/10 bg-white/[0.02]">
      <CardHeader className="text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500/20 to-purple-500/10">
          <Sparkles className="h-8 w-8 text-violet-400" />
        </div>
        <CardTitle className="text-2xl">AI Configuration</CardTitle>
        <CardDescription>
          Choose how your AI agents will be powered
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* AI Mode Selection */}
          <div className="space-y-4">
            <button
              type="button"
              onClick={() => setAIMode("platform")}
              className={cn(
                "relative w-full rounded-xl border-2 p-5 text-left transition-all hover:border-violet-500/50",
                aiMode === "platform"
                  ? "border-violet-500 bg-violet-500/10"
                  : "border-white/10 bg-white/[0.02]"
              )}
            >
              {aiMode === "platform" && (
                <CheckCircle2 className="absolute right-4 top-4 h-5 w-5 text-violet-500" />
              )}
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-violet-500/20">
                  <Zap className="h-6 w-6 text-violet-400" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">Use SpaceVoice AI</span>
                    <span className="rounded-full bg-violet-500/20 px-2 py-0.5 text-xs text-violet-400">
                      Recommended
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    No API keys needed. Pay-as-you-go pricing based on usage.
                    We handle everything for you.
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <span className="rounded-full border border-white/10 px-2 py-0.5 text-xs text-muted-foreground">
                      GPT-4o
                    </span>
                    <span className="rounded-full border border-white/10 px-2 py-0.5 text-xs text-muted-foreground">
                      Claude 3.5
                    </span>
                    <span className="rounded-full border border-white/10 px-2 py-0.5 text-xs text-muted-foreground">
                      Deepgram
                    </span>
                    <span className="rounded-full border border-white/10 px-2 py-0.5 text-xs text-muted-foreground">
                      ElevenLabs
                    </span>
                  </div>
                </div>
              </div>
            </button>

            <button
              type="button"
              onClick={() => setAIMode("byok")}
              className={cn(
                "relative w-full rounded-xl border-2 p-5 text-left transition-all hover:border-amber-500/50",
                aiMode === "byok"
                  ? "border-amber-500 bg-amber-500/10"
                  : "border-white/10 bg-white/[0.02]"
              )}
            >
              {aiMode === "byok" && (
                <CheckCircle2 className="absolute right-4 top-4 h-5 w-5 text-amber-500" />
              )}
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-amber-500/20">
                  <span className="text-lg">🔑</span>
                </div>
                <div>
                  <span className="font-semibold">Bring Your Own Keys</span>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Use your own OpenAI or Anthropic API keys. Great for enterprise
                    accounts or custom rate limits.
                  </p>
                </div>
              </div>
            </button>
          </div>

          {/* BYOK Fields */}
          {aiMode === "byok" && (
            <div className="space-y-4 rounded-xl border border-white/10 bg-white/[0.02] p-4">
              <div className="flex items-center justify-between">
                <h3 className="font-medium">Your API Keys</h3>
                <span className="text-xs text-muted-foreground">At least one required</span>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="openai_api_key">OpenAI API Key</Label>
                  <a
                    href="https://platform.openai.com/api-keys"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-xs text-emerald-400 hover:underline"
                  >
                    Get Key <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
                <Input
                  id="openai_api_key"
                  type="password"
                  placeholder="sk-..."
                  value={formData.openai_api_key}
                  onChange={(e) => setFormData({ ...formData, openai_api_key: e.target.value })}
                />
                <p className="text-xs text-muted-foreground">
                  Used for GPT-4o conversations
                </p>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="anthropic_api_key">Anthropic API Key</Label>
                  <a
                    href="https://console.anthropic.com/settings/keys"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-xs text-orange-400 hover:underline"
                  >
                    Get Key <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
                <Input
                  id="anthropic_api_key"
                  type="password"
                  placeholder="sk-ant-..."
                  value={formData.anthropic_api_key}
                  onChange={(e) => setFormData({ ...formData, anthropic_api_key: e.target.value })}
                />
                <p className="text-xs text-muted-foreground">
                  Used for Claude-powered agents
                </p>
              </div>
            </div>
          )}

          {/* Pricing Info */}
          {aiMode === "platform" && (
            <div className="rounded-lg border border-violet-500/20 bg-violet-500/5 p-4">
              <h4 className="mb-2 flex items-center gap-2 text-sm font-medium text-violet-400">
                💰 Simple Pricing
              </h4>
              <p className="text-xs text-muted-foreground">
                Pay only for what you use. AI costs are calculated per minute of conversation
                and billed monthly. No hidden fees, no minimum commitments.
              </p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3">
            <Button
              type="button"
              variant="ghost"
              onClick={() => router.push("/onboarding/telephony")}
              className="gap-2"
            >
              <ChevronLeft className="h-4 w-4" />
              Back
            </Button>

            <Button
              type="submit"
              disabled={!isValid || configureAI.isPending}
              className="flex-1 gap-2"
            >
              {configureAI.isPending ? (
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
