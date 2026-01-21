"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, FolderOpen, ArrowRight, ChevronLeft, Lightbulb } from "lucide-react";
import { toast } from "sonner";

export default function OnboardingWorkspacePage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [formData, setFormData] = useState({
    name: "",
    description: "",
  });

  const createWorkspace = useMutation({
    mutationFn: async (data: typeof formData) => {
      const response = await api.post("/api/v1/onboarding/workspace", data);
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["onboarding-status"] });
      void queryClient.invalidateQueries({ queryKey: ["workspaces"] });
      toast.success("Workspace created!");
      router.push("/onboarding/complete");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to create workspace");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createWorkspace.mutate(formData);
  };

  const isValid = formData.name.trim() !== "";

  return (
    <Card className="border-white/10 bg-white/[0.02]">
      <CardHeader className="text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/20 to-cyan-500/10">
          <FolderOpen className="h-8 w-8 text-blue-400" />
        </div>
        <CardTitle className="text-2xl">Create Your Workspace</CardTitle>
        <CardDescription>
          Workspaces help you organize your AI agents, contacts, and campaigns
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="name">Workspace Name *</Label>
            <Input
              id="name"
              placeholder="My Company"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              autoFocus
            />
            <p className="text-xs text-muted-foreground">
              This is usually your company or team name
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description (Optional)</Label>
            <Textarea
              id="description"
              placeholder="A brief description of what this workspace is for..."
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={3}
            />
          </div>

          {/* Tips */}
          <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-4">
            <h4 className="mb-2 flex items-center gap-2 text-sm font-medium text-blue-400">
              <Lightbulb className="h-4 w-4" />
              What&apos;s a Workspace?
            </h4>
            <ul className="space-y-1 text-xs text-muted-foreground">
              <li>• <strong>Agents:</strong> Create AI voice agents for different use cases</li>
              <li>• <strong>Contacts:</strong> Manage your CRM contacts and call history</li>
              <li>• <strong>Campaigns:</strong> Run outbound calling campaigns</li>
              <li>• <strong>Team:</strong> Invite team members to collaborate (coming soon)</li>
            </ul>
          </div>

          {/* Quick Start Suggestions */}
          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Quick suggestions:</Label>
            <div className="flex flex-wrap gap-2">
              {["Sales Team", "Support", "Marketing", "Operations"].map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => setFormData({ ...formData, name: suggestion })}
                  className="rounded-full border border-white/10 bg-white/[0.02] px-3 py-1 text-xs transition-colors hover:border-white/20 hover:bg-white/5"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <Button
              type="button"
              variant="ghost"
              onClick={() => router.push("/onboarding/ai-providers")}
              className="gap-2"
            >
              <ChevronLeft className="h-4 w-4" />
              Back
            </Button>

            <Button
              type="submit"
              disabled={!isValid || createWorkspace.isPending}
              className="flex-1 gap-2"
            >
              {createWorkspace.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <>
                  Create Workspace
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
