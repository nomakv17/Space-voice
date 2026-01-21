import { AppSidebar } from "@/components/app-sidebar";
import { TopBar } from "@/components/top-bar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
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
