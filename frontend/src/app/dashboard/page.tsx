"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Bot,
  Phone,
  Clock,
  CheckCircle,
  Plus,
  ArrowRight,
  Calendar,
  Users,
  PhoneCall,
  Settings,
  DollarSign,
} from "lucide-react";
import { fetchAgents } from "@/lib/api/agents";
import { listCalls } from "@/lib/api/calls";
import { getRevenueSummary } from "@/lib/api/revenue";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";

interface Workspace {
  id: string;
  name: string;
  contact_count: number;
  agent_count: number;
}

interface Appointment {
  id: number;
  status: string;
  scheduled_at: string;
  contact_name: string | null;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const isAdmin = user?.is_superuser ?? false;

  // Fetch agents
  const { data: agents = [] } = useQuery({
    queryKey: ["agents"],
    queryFn: fetchAgents,
  });

  // Fetch recent calls (for non-admin or recent calls list)
  const { data: callsData } = useQuery({
    queryKey: ["calls", 1],
    queryFn: () => listCalls({ page: 1, page_size: 5 }),
  });

  // Fetch platform-wide revenue stats (admin only)
  const { data: revenueData } = useQuery({
    queryKey: ["revenue-summary"],
    queryFn: () => getRevenueSummary(),
    enabled: isAdmin,
  });

  // Fetch workspaces
  const { data: workspaces = [] } = useQuery<Workspace[]>({
    queryKey: ["workspaces"],
    queryFn: async () => {
      const response = await api.get("/api/v1/workspaces");
      return response.data;
    },
  });

  // Fetch upcoming appointments
  const { data: appointments = [] } = useQuery<Appointment[]>({
    queryKey: ["appointments", "scheduled"],
    queryFn: async () => {
      const response = await api.get("/api/v1/crm/appointments?status=scheduled");
      return response.data;
    },
  });

  const activeAgents = agents.filter((a) => a.is_active).length;

  // For admins, use platform-wide stats from revenue API
  // For regular users, use their own call data
  const totalCalls = isAdmin && revenueData ? revenueData.total_calls : (callsData?.total ?? 0);
  const completedCalls = isAdmin && revenueData
    ? revenueData.completed_calls
    : (callsData?.calls?.filter((c) => c.status === "completed").length ?? 0);
  const avgDuration = isAdmin && revenueData
    ? Math.round(revenueData.avg_call_duration_secs)
    : (callsData?.calls && callsData.calls.length > 0
        ? Math.round(
            callsData.calls.reduce((sum, c) => sum + c.duration_seconds, 0) / callsData.calls.length
          )
        : 0);
  const totalContacts = workspaces.reduce((sum, w) => sum + w.contact_count, 0);
  const upcomingAppointments = appointments.filter(
    (a) => new Date(a.scheduled_at) > new Date()
  ).length;

  // Additional admin stats
  const totalRevenue = isAdmin && revenueData ? revenueData.total_revenue : null;
  const activeUsers = isAdmin && revenueData ? revenueData.unique_users : null;

  const formatDuration = (seconds: number) => {
    if (seconds === 0) return "0s";
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (mins === 0) return `${secs}s`;
    return `${mins}m ${secs}s`;
  };

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">Overview of your voice agent platform</p>
        </div>
        {workspaces.length > 0 ? (
          <Button size="sm" className="shadow-lg shadow-primary/20" asChild>
            <Link href="/dashboard/agents/create-agent">
              <Plus className="mr-2 h-4 w-4" />
              Create Agent
            </Link>
          </Button>
        ) : (
          <Button size="sm" className="shadow-lg shadow-primary/20" asChild>
            <Link href="/dashboard/workspaces">
              <Plus className="mr-2 h-4 w-4" />
              Create Workspace
            </Link>
          </Button>
        )}
      </div>

      {/* Stats Cards - Premium glass style */}
      <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-6">
        <Card className="group hover:-translate-y-0.5 hover:border-indigo-500/20 hover:shadow-card-hover">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-xs font-medium text-muted-foreground">Active Agents</p>
                <p className="text-2xl font-bold tracking-tight">{activeAgents}</p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/10 shadow-inner-glow">
                <Bot className="h-5 w-5 text-indigo-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="group hover:-translate-y-0.5 hover:border-blue-500/20 hover:shadow-card-hover">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-xs font-medium text-muted-foreground">Total Calls</p>
                <p className="text-2xl font-bold tracking-tight">{totalCalls}</p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/10 shadow-inner-glow">
                <Phone className="h-5 w-5 text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="group hover:-translate-y-0.5 hover:border-emerald-500/20 hover:shadow-card-hover">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-xs font-medium text-muted-foreground">Completed</p>
                <p className="text-2xl font-bold tracking-tight">{completedCalls}</p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500/20 to-green-500/10 shadow-inner-glow">
                <CheckCircle className="h-5 w-5 text-emerald-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="group hover:-translate-y-0.5 hover:border-amber-500/20 hover:shadow-card-hover">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-xs font-medium text-muted-foreground">Avg Duration</p>
                <p className="text-2xl font-bold tracking-tight">{formatDuration(avgDuration)}</p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500/20 to-orange-500/10 shadow-inner-glow">
                <Clock className="h-5 w-5 text-amber-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        {isAdmin && totalRevenue !== null ? (
          <Card className="group hover:-translate-y-0.5 hover:border-green-500/20 hover:shadow-card-hover">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground">Total Revenue</p>
                  <p className="text-2xl font-bold tracking-tight">
                    ${totalRevenue.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </p>
                </div>
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-green-500/20 to-emerald-500/10 shadow-inner-glow">
                  <DollarSign className="h-5 w-5 text-green-400" />
                </div>
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card className="group hover:-translate-y-0.5 hover:border-violet-500/20 hover:shadow-card-hover">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground">Contacts</p>
                  <p className="text-2xl font-bold tracking-tight">{totalContacts}</p>
                </div>
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500/20 to-purple-500/10 shadow-inner-glow">
                  <Users className="h-5 w-5 text-violet-400" />
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {isAdmin && activeUsers !== null ? (
          <Card className="group hover:-translate-y-0.5 hover:border-violet-500/20 hover:shadow-card-hover">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground">Active Users</p>
                  <p className="text-2xl font-bold tracking-tight">{activeUsers}</p>
                </div>
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500/20 to-purple-500/10 shadow-inner-glow">
                  <Users className="h-5 w-5 text-violet-400" />
                </div>
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card className="group hover:-translate-y-0.5 hover:border-rose-500/20 hover:shadow-card-hover">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground">Upcoming</p>
                  <p className="text-2xl font-bold tracking-tight">{upcomingAppointments}</p>
                </div>
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-rose-500/20 to-pink-500/10 shadow-inner-glow">
                  <Calendar className="h-5 w-5 text-rose-400" />
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recent Calls */}
        <Card className="lg:col-span-2">
          <CardContent className="p-5">
            <div className="mb-5 flex items-center justify-between">
              <h3 className="text-base font-semibold tracking-tight">Recent Calls</h3>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 text-xs text-muted-foreground hover:text-foreground"
                asChild
              >
                <Link href="/dashboard/calls">
                  View all
                  <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
                </Link>
              </Button>
            </div>
            {callsData?.calls && callsData.calls.length > 0 ? (
              <div className="space-y-2.5">
                {callsData.calls.slice(0, 5).map((call, index) => (
                  <Link
                    key={call.id}
                    href={`/dashboard/calls/${call.id}`}
                    className="group flex items-center justify-between rounded-xl border border-white/[0.06] bg-white/[0.02] p-3.5 transition-all duration-200 hover:border-white/[0.12] hover:bg-white/[0.04]"
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    <div className="flex items-center gap-3.5">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500/20 to-indigo-500/10 shadow-inner-glow transition-transform group-hover:scale-105">
                        <PhoneCall className="h-4.5 w-4.5 text-blue-400" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">
                          {call.contact_name ?? call.from_number}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {call.agent_name ?? "Unknown Agent"} &middot;{" "}
                          {formatDuration(call.duration_seconds)}
                        </p>
                      </div>
                    </div>
                    <span
                      className={`inline-flex h-6 items-center rounded-lg px-2.5 text-[11px] font-medium transition-all ${
                        call.status === "completed"
                          ? "status-completed"
                          : call.status === "failed"
                            ? "status-failed"
                            : "status-pending"
                      }`}
                    >
                      {call.status}
                    </span>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-white/[0.08] bg-white/[0.01] py-12 text-center">
                <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-gray-500/20 to-gray-600/10">
                  <Phone className="h-6 w-6 text-gray-500" />
                </div>
                <p className="text-sm font-medium text-muted-foreground">No calls yet</p>
                <p className="mt-1 max-w-[200px] text-xs text-muted-foreground/70">
                  Calls will appear here once your agents start handling them
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardContent className="p-5">
            <h3 className="mb-5 text-base font-semibold tracking-tight">Quick Actions</h3>
            <div className="space-y-2.5">
              {workspaces.length > 0 ? (
                <Link
                  href="/dashboard/agents/create-agent"
                  className="group flex items-center gap-3.5 rounded-xl border border-white/[0.06] bg-white/[0.02] p-3.5 transition-all duration-200 hover:border-indigo-500/30 hover:bg-indigo-500/[0.05]"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/10 shadow-inner-glow transition-transform group-hover:scale-105">
                    <Bot className="h-4.5 w-4.5 text-indigo-400" />
                  </div>
                  <div>
                    <p className="text-sm font-medium">Create Agent</p>
                    <p className="text-xs text-muted-foreground">Configure a new voice agent</p>
                  </div>
                </Link>
              ) : (
                <Link
                  href="/dashboard/workspaces"
                  className="group flex items-center gap-3.5 rounded-xl border border-dashed border-white/[0.1] bg-white/[0.01] p-3.5 transition-all duration-200 hover:border-white/[0.15] hover:bg-white/[0.03]"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-gray-500/20 to-gray-600/10">
                    <Bot className="h-4.5 w-4.5 text-gray-500" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">
                      Create Workspace First
                    </p>
                    <p className="text-xs text-muted-foreground/70">
                      Required before creating agents
                    </p>
                  </div>
                </Link>
              )}
              <Link
                href="/dashboard/phone-numbers"
                className="group flex items-center gap-3.5 rounded-xl border border-white/[0.06] bg-white/[0.02] p-3.5 transition-all duration-200 hover:border-emerald-500/30 hover:bg-emerald-500/[0.05]"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500/20 to-green-500/10 shadow-inner-glow transition-transform group-hover:scale-105">
                  <Phone className="h-4.5 w-4.5 text-emerald-400" />
                </div>
                <div>
                  <p className="text-sm font-medium">Get Phone Number</p>
                  <p className="text-xs text-muted-foreground">Purchase a number</p>
                </div>
              </Link>
              <Link
                href="/dashboard/crm"
                className="group flex items-center gap-3.5 rounded-xl border border-white/[0.06] bg-white/[0.02] p-3.5 transition-all duration-200 hover:border-violet-500/30 hover:bg-violet-500/[0.05]"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500/20 to-purple-500/10 shadow-inner-glow transition-transform group-hover:scale-105">
                  <Users className="h-4.5 w-4.5 text-violet-400" />
                </div>
                <div>
                  <p className="text-sm font-medium">Manage Contacts</p>
                  <p className="text-xs text-muted-foreground">Add or import contacts</p>
                </div>
              </Link>
              <Link
                href="/dashboard/settings"
                className="group flex items-center gap-3.5 rounded-xl border border-white/[0.06] bg-white/[0.02] p-3.5 transition-all duration-200 hover:border-amber-500/30 hover:bg-amber-500/[0.05]"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500/20 to-orange-500/10 shadow-inner-glow transition-transform group-hover:scale-105">
                  <Settings className="h-4.5 w-4.5 text-amber-400" />
                </div>
                <div>
                  <p className="text-sm font-medium">Configure API Keys</p>
                  <p className="text-xs text-muted-foreground">OpenAI, Deepgram, ElevenLabs</p>
                </div>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Agents Grid */}
      {agents.length > 0 && (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-base font-semibold tracking-tight">Your Agents</h3>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 text-xs text-muted-foreground hover:text-foreground"
              asChild
            >
              <Link href="/dashboard/agents">
                View all
                <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
              </Link>
            </Button>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {agents.slice(0, 4).map((agent, index) => (
              <Link key={agent.id} href={`/dashboard/agents/${agent.id}`} prefetch={false}>
                <Card
                  className="group cursor-pointer hover:-translate-y-0.5 hover:border-indigo-500/20 hover:shadow-card-hover"
                  style={{ animationDelay: `${index * 75}ms` }}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/10 shadow-inner-glow transition-transform group-hover:scale-105">
                        <Bot className="h-5 w-5 text-indigo-400" />
                      </div>
                      <div className="min-w-0">
                        <h3 className="truncate text-sm font-semibold">{agent.name}</h3>
                        <p className="text-xs text-muted-foreground">
                          {agent.pricing_tier.charAt(0).toUpperCase() + agent.pricing_tier.slice(1)}{" "}
                          &middot; {agent.total_calls} calls
                        </p>
                      </div>
                    </div>
                    {/* Status indicator */}
                    <div className="mt-3 flex items-center gap-2">
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-lg px-2 py-0.5 text-[11px] font-medium ${agent.is_active ? "status-active" : "status-inactive"}`}
                      >
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${agent.is_active ? "bg-emerald-400" : "bg-gray-500"}`}
                        />
                        {agent.is_active ? "Active" : "Inactive"}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
