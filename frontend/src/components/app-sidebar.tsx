"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Bot,
  Phone,
  PhoneOutgoing,
  History,
  Settings,
  LayoutDashboard,
  Mic,
  Zap,
  Users,
  UserPlus,
  Calendar,
  FolderOpen,
  PanelLeftClose,
  PanelLeft,
  LogOut,
  Key,
  DollarSign,
} from "lucide-react";
import { useSidebarStore } from "@/lib/sidebar-store";
import { useAuth } from "@/hooks/use-auth";

const navigation = [
  {
    name: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
    color: "text-blue-400",
  },
  {
    name: "Voice Agents",
    href: "/dashboard/agents",
    icon: Bot,
    color: "text-violet-400",
  },
  {
    name: "Workspaces",
    href: "/dashboard/workspaces",
    icon: FolderOpen,
    color: "text-amber-400",
  },
  {
    name: "CRM",
    href: "/dashboard/crm",
    icon: Users,
    color: "text-emerald-400",
  },
  {
    name: "Campaigns",
    href: "/dashboard/campaigns",
    icon: PhoneOutgoing,
    color: "text-orange-400",
  },
  {
    name: "Appointments",
    href: "/dashboard/appointments",
    icon: Calendar,
    color: "text-pink-400",
  },
  {
    name: "Integrations",
    href: "/dashboard/integrations",
    icon: Zap,
    color: "text-yellow-400",
  },
  {
    name: "Phone Numbers",
    href: "/dashboard/phone-numbers",
    icon: Phone,
    color: "text-cyan-400",
  },
  {
    name: "Call History",
    href: "/dashboard/calls",
    icon: History,
    color: "text-orange-400",
  },
  {
    name: "Test Agent",
    href: "/dashboard/test",
    icon: Mic,
    color: "text-rose-400",
  },
];

// Admin-only navigation items
const adminNavigation = [
  {
    name: "Clients",
    href: "/dashboard/clients",
    icon: UserPlus,
    color: "text-indigo-400",
  },
  {
    name: "Pricing",
    href: "/dashboard/pricing",
    icon: DollarSign,
    color: "text-emerald-400",
  },
];

export function AppSidebar() {
  const pathname = usePathname();
  const { sidebarOpen, setSidebarOpen, hasHydrated } = useSidebarStore();
  const { user, logout } = useAuth();

  // Use default width until hydrated to prevent layout shift
  const effectiveSidebarOpen = hasHydrated ? sidebarOpen : true;

  // Only show user info when authenticated - never show placeholders
  const displayName = user?.username ?? user?.email?.split("@")[0] ?? "";
  const displayEmail = user?.email ?? "";
  const initials = displayName ? displayName.slice(0, 2).toUpperCase() : "?";

  const isActive = (href: string) => {
    if (href === "/dashboard") {
      return pathname === "/dashboard";
    }
    return pathname === href || pathname.startsWith(href + "/");
  };

  return (
    <div
      className="relative flex h-screen flex-col bg-sidebar"
      style={{
        width: effectiveSidebarOpen ? 220 : 64,
        transition: hasHydrated ? "width 0.2s ease" : "none",
      }}
    >
      {/* Logo */}
      <div
        className={cn("flex h-12 items-center", effectiveSidebarOpen ? "px-4" : "justify-center")}
      >
        <Link href="/dashboard" className="relative block overflow-hidden">
          <motion.span
            className="animate-gradient-flow block whitespace-nowrap bg-clip-text text-lg font-bold tracking-tight text-transparent"
            style={{
              backgroundImage:
                "linear-gradient(90deg, #e2e8f0, #94a3b8, #e2e8f0, #94a3b8, #e2e8f0)",
              backgroundSize: "200% 100%",
            }}
            initial={false}
            animate={{ width: effectiveSidebarOpen ? 100 : 11 }}
            transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
          >
            SpaceVoice
          </motion.span>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-2">
        <div className="flex flex-col gap-1">
          {/* Admin-only navigation */}
          {user?.is_superuser &&
            adminNavigation.map((item) => {
              const active = isActive(item.href);
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  prefetch={true}
                  className={cn(
                    "relative inline-flex h-9 w-full items-center justify-start gap-3 rounded-md px-3 text-sm font-normal transition-colors",
                    !effectiveSidebarOpen && "justify-center gap-0 px-0",
                    active
                      ? "bg-sidebar-accent text-sidebar-foreground"
                      : "text-sidebar-foreground/60 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                  )}
                >
                  {active && (
                    <div className="absolute inset-y-0 left-0 my-auto h-5 w-0.5 rounded-r-full bg-indigo-400" />
                  )}
                  <item.icon className={cn("h-[18px] w-[18px] shrink-0", active && item.color)} />
                  <AnimatePresence>
                    {effectiveSidebarOpen && (
                      <motion.span
                        initial={{ opacity: 0, width: 0 }}
                        animate={{ opacity: 1, width: "auto" }}
                        exit={{ opacity: 0, width: 0 }}
                        transition={{ duration: 0.15 }}
                        className="truncate"
                      >
                        {item.name}
                      </motion.span>
                    )}
                  </AnimatePresence>
                </Link>
              );
            })}

          {/* Divider for admin section */}
          {user?.is_superuser && <div className="my-2 border-t border-sidebar-border" />}

          {/* Regular navigation */}
          {navigation.map((item) => {
            const active = isActive(item.href);
            return (
              <Link
                key={item.name}
                href={item.href}
                prefetch={true}
                className={cn(
                  "relative inline-flex h-9 w-full items-center justify-start gap-3 rounded-md px-3 text-sm font-normal transition-colors",
                  !effectiveSidebarOpen && "justify-center gap-0 px-0",
                  active
                    ? "bg-sidebar-accent text-sidebar-foreground"
                    : "text-sidebar-foreground/60 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                )}
              >
                {active && (
                  <div className="absolute inset-y-0 left-0 my-auto h-5 w-0.5 rounded-r-full bg-sidebar-foreground" />
                )}
                <item.icon className={cn("h-[18px] w-[18px] shrink-0", active && item.color)} />
                <AnimatePresence>
                  {effectiveSidebarOpen && (
                    <motion.span
                      initial={{ opacity: 0, width: 0 }}
                      animate={{ opacity: 1, width: "auto" }}
                      exit={{ opacity: 0, width: 0 }}
                      transition={{ duration: 0.15 }}
                      className="truncate"
                    >
                      {item.name}
                    </motion.span>
                  )}
                </AnimatePresence>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Toggle Button */}
      <div className="px-2 py-2">
        <Button
          variant="ghost"
          className={cn(
            "h-10 w-full justify-start gap-3 px-3 font-normal",
            !effectiveSidebarOpen && "justify-center gap-0 px-0",
            "text-sidebar-foreground/60 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
          )}
          onClick={() => setSidebarOpen(!sidebarOpen)}
        >
          {effectiveSidebarOpen ? (
            <PanelLeftClose className="h-[18px] w-[18px] shrink-0" />
          ) : (
            <PanelLeft className="h-[18px] w-[18px] shrink-0" />
          )}
          <AnimatePresence>
            {effectiveSidebarOpen && (
              <motion.span
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: "auto" }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.15 }}
                className="text-sm"
              >
                Hide sidebar
              </motion.span>
            )}
          </AnimatePresence>
        </Button>
      </div>

      {/* User Profile */}
      <div className="border-t border-sidebar-border px-2 py-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              className={cn(
                "relative h-10 w-full justify-start gap-3 px-2 font-normal",
                !effectiveSidebarOpen && "justify-center gap-0 px-0",
                "text-sidebar-foreground/60 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
              )}
            >
              <Avatar className="h-7 w-7 shrink-0">
                <AvatarFallback className="bg-sidebar-accent text-xs text-sidebar-foreground">
                  {initials}
                </AvatarFallback>
              </Avatar>
              <AnimatePresence>
                {effectiveSidebarOpen && (
                  <motion.div
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: "auto" }}
                    exit={{ opacity: 0, width: 0 }}
                    transition={{ duration: 0.15 }}
                    className="flex min-w-0 flex-col items-start text-left"
                  >
                    <span className="truncate text-sm text-sidebar-foreground">{displayName}</span>
                    <span className="truncate text-xs text-sidebar-foreground/50">
                      {displayEmail}
                    </span>
                  </motion.div>
                )}
              </AnimatePresence>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align={effectiveSidebarOpen ? "end" : "center"}
            side="top"
            className="w-56"
          >
            <DropdownMenuLabel>My Account</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link href="/dashboard/settings" prefetch={true} className="flex items-center gap-2">
                <Settings className="h-4 w-4" />
                Settings
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/dashboard/settings" prefetch={true} className="flex items-center gap-2">
                <Key className="h-4 w-4" />
                API Keys
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={logout} className="flex items-center gap-2">
              <LogOut className="h-4 w-4" />
              Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}
