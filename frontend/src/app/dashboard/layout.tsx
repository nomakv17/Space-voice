"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AppSidebar } from "@/components/app-sidebar";
import { TopBar } from "@/components/top-bar";
import { useAuth } from "@/hooks/use-auth";
import { Loader2 } from "lucide-react";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { token, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // Redirect to login if not authenticated and not loading
    if (!isLoading && !token) {
      router.push("/login");
    }
  }, [isLoading, token, router]);

  // Show loading state while checking auth
  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-sidebar">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  // Don't render dashboard if not authenticated
  if (!token) {
    return (
      <div className="flex h-screen items-center justify-center bg-sidebar">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-sidebar">
      <AppSidebar />
      <div className="relative flex flex-1 flex-col overflow-hidden">
        <TopBar />
        <div className="flex-1 overflow-y-auto px-2.5 pb-2.5">
          <main className="flex min-h-full flex-col rounded-lg bg-background">
            <div className="flex flex-1 flex-col gap-4 p-4 md:p-6 lg:p-8">{children}</div>
          </main>
        </div>
      </div>
    </div>
  );
}
