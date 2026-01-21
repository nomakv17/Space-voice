"use client";

import { useRef } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Loader2,
  CheckCircle,
  Rocket,
  Bot,
  Users,
  Phone,
  ArrowRight,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";

export default function OnboardingCompletePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { refetchUser } = useAuth();
  const isNavigatingRef = useRef(false);

  const completeOnboarding = useMutation({
    mutationFn: async () => {
      const response = await api.post("/api/v1/onboarding/complete");
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["onboarding-status"] });
      // Refetch user to update onboarding status in auth context
      void refetchUser();
    },
    onError: (error: Error) => {
      // Still navigate even on error - user can continue to dashboard
      toast.error(error.message || "Failed to complete onboarding");
    },
  });

  // Complete onboarding and navigate - called when user clicks any navigation button
  const handleNavigate = (destination: string) => {
    // Prevent double navigation
    if (isNavigatingRef.current) return;
    isNavigatingRef.current = true;

    // Fire the complete API call (let it complete in background)
    if (!completeOnboarding.isSuccess && !completeOnboarding.isPending) {
      completeOnboarding.mutate();
    }

    // Navigate immediately so user sees instant feedback
    router.push(destination);
  };

  return (
    <Card className="border-white/10 bg-white/[0.02]">
      <CardHeader className="text-center">
        {/* Celebration Animation */}
        <div className="relative mx-auto mb-6">
          <div className="absolute -inset-4 animate-pulse rounded-full bg-gradient-to-r from-emerald-500/20 via-blue-500/20 to-violet-500/20 blur-xl" />
          <div className="relative flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-emerald-500 to-emerald-600">
            <CheckCircle className="h-10 w-10 text-white" />
          </div>
        </div>

        <CardTitle className="text-3xl">
          <span className="bg-gradient-to-r from-emerald-400 via-blue-400 to-violet-400 bg-clip-text text-transparent">
            You&apos;re All Set!
          </span>
        </CardTitle>
        <CardDescription className="text-base">
          Welcome to SpaceVoice. Your AI voice agents are ready to go.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Completion Summary */}
        <div className="space-y-3 rounded-xl border border-white/10 bg-white/[0.02] p-4">
          <h3 className="font-medium">What&apos;s been set up:</h3>
          <div className="space-y-2">
            <div className="flex items-center gap-3 text-sm">
              <CheckCircle className="h-4 w-4 text-emerald-500" />
              <span>Your profile is configured</span>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <CheckCircle className="h-4 w-4 text-emerald-500" />
              <span>Telephony provider connected</span>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <CheckCircle className="h-4 w-4 text-emerald-500" />
              <span>AI configuration set up</span>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <CheckCircle className="h-4 w-4 text-emerald-500" />
              <span>Your workspace is ready</span>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="space-y-3">
          <h3 className="font-medium">Get started:</h3>
          <div className="grid gap-3">
            <button
              onClick={() => handleNavigate("/dashboard/agents")}
              className="flex items-center gap-4 rounded-xl border border-white/10 bg-white/[0.02] p-4 text-left transition-all hover:border-violet-500/50 hover:bg-violet-500/5"
            >
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-violet-500/20">
                <Bot className="h-5 w-5 text-violet-400" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium">Create Your First Agent</span>
                  <span className="rounded-full bg-violet-500/20 px-2 py-0.5 text-xs text-violet-400">
                    Recommended
                  </span>
                </div>
                <p className="text-sm text-muted-foreground">
                  Build an AI voice agent for sales, support, or scheduling
                </p>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </button>

            <button
              onClick={() => handleNavigate("/dashboard/crm")}
              className="flex items-center gap-4 rounded-xl border border-white/10 bg-white/[0.02] p-4 text-left transition-all hover:border-blue-500/50 hover:bg-blue-500/5"
            >
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-500/20">
                <Users className="h-5 w-5 text-blue-400" />
              </div>
              <div className="flex-1">
                <span className="font-medium">Import Contacts</span>
                <p className="text-sm text-muted-foreground">
                  Add your contacts to start making calls
                </p>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </button>

            <button
              onClick={() => handleNavigate("/dashboard/calls")}
              className="flex items-center gap-4 rounded-xl border border-white/10 bg-white/[0.02] p-4 text-left transition-all hover:border-emerald-500/50 hover:bg-emerald-500/5"
            >
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-500/20">
                <Phone className="h-5 w-5 text-emerald-400" />
              </div>
              <div className="flex-1">
                <span className="font-medium">Test a Call</span>
                <p className="text-sm text-muted-foreground">
                  Try out a demo call to see how it works
                </p>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </button>
          </div>
        </div>

        {/* Help Section */}
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4">
          <h4 className="mb-2 flex items-center gap-2 text-sm font-medium text-amber-400">
            <Sparkles className="h-4 w-4" />
            Need help getting started?
          </h4>
          <p className="text-xs text-muted-foreground">
            Check out our documentation or contact support at{" "}
            <a href="mailto:support@spacevoice.ai" className="text-amber-400 hover:underline">
              support@spacevoice.ai
            </a>
          </p>
        </div>

        {/* Go to Dashboard Button */}
        <Button
          onClick={() => handleNavigate("/dashboard")}
          size="lg"
          disabled={completeOnboarding.isPending}
          className="w-full gap-2 bg-gradient-to-r from-violet-600 to-blue-600 text-white hover:from-violet-700 hover:to-blue-700"
        >
          {completeOnboarding.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Rocket className="h-4 w-4" />
          )}
          Go to Dashboard
        </Button>
      </CardContent>
    </Card>
  );
}
