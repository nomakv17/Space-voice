"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { Loader2 } from "lucide-react";

export default function Home() {
  const router = useRouter();
  const { user, token, isLoading } = useAuth();

  useEffect(() => {
    if (isLoading) return;

    if (!token) {
      router.push("/login");
    } else if (user?.is_superuser || user?.onboarding_completed) {
      // Admins always go to dashboard, clients who completed onboarding go to dashboard
      router.push("/dashboard");
    } else if (user) {
      // Clients who haven't completed onboarding
      router.push("/onboarding");
    } else {
      // Default: go to dashboard (user data might still be loading)
      router.push("/dashboard");
    }
  }, [token, user, isLoading, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-black">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  );
}
