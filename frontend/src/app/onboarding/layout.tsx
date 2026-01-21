"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Loader2 } from "lucide-react";

interface OnboardingStatus {
  onboarding_completed: boolean;
  onboarding_step: number;
  company_name: string | null;
  company_size: string | null;
  industry: string | null;
  phone_number: string | null;
  has_workspace: boolean;
  has_telephony: boolean;
}

export default function OnboardingLayout({ children }: { children: React.ReactNode }) {
  const { data: status, isLoading } = useQuery<OnboardingStatus>({
    queryKey: ["onboarding-status"],
    queryFn: async () => {
      const response = await api.get("/api/v1/onboarding/status");
      return response.data;
    },
  });

  // NOTE: Removed auto-redirect here to prevent competing with explicit navigation
  // from the complete page. User will click "Go to Dashboard" button instead.

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-black">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const currentStep = status?.onboarding_step ?? 1;

  return (
    <div className="flex min-h-screen flex-col bg-black">
      {/* Progress indicator */}
      <div className="border-b border-white/10 bg-black/50 backdrop-blur-sm">
        <div className="mx-auto max-w-3xl px-6 py-4">
          <div className="flex items-center justify-between">
            <span
              className="animate-gradient-flow bg-clip-text text-xl font-bold tracking-tight text-transparent"
              style={{
                backgroundImage: "linear-gradient(90deg, #e2e8f0, #94a3b8, #e2e8f0, #94a3b8, #e2e8f0)",
                backgroundSize: "200% 100%",
              }}
            >
              SpaceVoice
            </span>
            <div className="flex items-center gap-2">
              {[1, 2, 3, 4, 5].map((step) => (
                <div
                  key={step}
                  className={`h-2 w-8 rounded-full transition-colors ${
                    step < currentStep
                      ? "bg-emerald-500"
                      : step === currentStep
                        ? "bg-primary"
                        : "bg-white/20"
                  }`}
                />
              ))}
            </div>
            <span className="text-sm text-muted-foreground">
              Step {currentStep} of 5
            </span>
          </div>
        </div>
      </div>

      {/* Main content */}
      <main className="flex flex-1 flex-col items-center justify-center p-6">
        <div className="w-full max-w-xl">{children}</div>
      </main>
    </div>
  );
}
