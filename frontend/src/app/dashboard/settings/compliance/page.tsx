"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Check,
  AlertTriangle,
  X,
  Download,
  Trash2,
  Shield,
  FileText,
  ExternalLink,
  Loader2,
} from "lucide-react";

interface ComplianceCheck {
  id: string;
  label: string;
  description: string;
  status: "complete" | "incomplete" | "warning";
  action_url?: string;
  action_label?: string;
}

interface ComplianceStatus {
  completed: number;
  total: number;
  percentage: number;
  checks: ComplianceCheck[];
}

interface ComplianceOverview {
  gdpr: ComplianceStatus;
  ccpa: ComplianceStatus;
}

interface PrivacySettings {
  privacy_policy_url: string | null;
  data_retention_days: number;
  openai_dpa_signed: boolean;
  telnyx_dpa_signed: boolean;
  deepgram_dpa_signed: boolean;
  elevenlabs_dpa_signed: boolean;
  ccpa_opt_out: boolean;
  last_data_export_at: string | null;
}

export default function ComplianceSettingsPage() {
  const queryClient = useQueryClient();
  const [privacyPolicyUrl, setPrivacyPolicyUrl] = useState("");
  const [dataRetentionDays, setDataRetentionDays] = useState(365);

  // Fetch compliance status
  const { data: complianceStatus, isLoading: statusLoading } = useQuery<ComplianceOverview>({
    queryKey: ["compliance-status"],
    queryFn: async () => {
      const response = await api.get("/api/v1/compliance/status");
      return response.data;
    },
  });

  // Fetch privacy settings
  const { data: privacySettings, isLoading: settingsLoading } = useQuery<PrivacySettings>({
    queryKey: ["privacy-settings"],
    queryFn: async () => {
      const response = await api.get("/api/v1/compliance/privacy-settings");
      const data = response.data;
      setPrivacyPolicyUrl(data.privacy_policy_url ?? "");
      setDataRetentionDays(data.data_retention_days ?? 365);
      return data;
    },
  });

  // Update privacy settings mutation
  const updateSettingsMutation = useMutation({
    mutationFn: async (data: Partial<PrivacySettings>) => {
      const response = await api.patch("/api/v1/compliance/privacy-settings", data);
      return response.data;
    },
    onSuccess: () => {
      toast.success("Privacy settings updated");
      void queryClient.invalidateQueries({ queryKey: ["privacy-settings"] });
      void queryClient.invalidateQueries({ queryKey: ["compliance-status"] });
    },
    onError: () => {
      toast.error("Failed to update settings");
    },
  });

  // Record consent mutation
  const recordConsentMutation = useMutation({
    mutationFn: async (data: { consent_type: string; granted: boolean }) => {
      const response = await api.post("/api/v1/compliance/consent", data);
      return response.data;
    },
    onSuccess: () => {
      toast.success("Consent recorded");
      void queryClient.invalidateQueries({ queryKey: ["compliance-status"] });
    },
    onError: () => {
      toast.error("Failed to record consent");
    },
  });

  // Export data mutation
  const exportDataMutation = useMutation({
    mutationFn: async () => {
      const response = await api.get("/api/v1/compliance/export");
      return response.data;
    },
    onSuccess: (data) => {
      // Download as JSON file
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `spacevoice-data-export-${new Date().toISOString().split("T")[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success("Data exported successfully");
      void queryClient.invalidateQueries({ queryKey: ["privacy-settings"] });
    },
    onError: () => {
      toast.error("Failed to export data");
    },
  });

  // Delete data mutation
  const deleteDataMutation = useMutation({
    mutationFn: async () => {
      const response = await api.delete("/api/v1/compliance/data");
      return response.data;
    },
    onSuccess: () => {
      toast.success("All data deleted successfully");
      void queryClient.invalidateQueries({ queryKey: ["compliance-status"] });
      void queryClient.invalidateQueries({ queryKey: ["privacy-settings"] });
    },
    onError: () => {
      toast.error("Failed to delete data");
    },
  });

  // CCPA opt-out mutation
  const ccpaOptOutMutation = useMutation({
    mutationFn: async (optOut: boolean) => {
      const endpoint = optOut ? "/api/v1/compliance/ccpa/opt-out" : "/api/v1/compliance/ccpa/opt-in";
      const response = await api.post(endpoint);
      return response.data;
    },
    onSuccess: () => {
      toast.success("CCPA preference updated");
      void queryClient.invalidateQueries({ queryKey: ["privacy-settings"] });
      void queryClient.invalidateQueries({ queryKey: ["compliance-status"] });
    },
    onError: () => {
      toast.error("Failed to update CCPA preference");
    },
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "complete":
        return <Check className="h-4 w-4 text-green-500" />;
      case "warning":
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      default:
        return <X className="h-4 w-4 text-red-500" />;
    }
  };

  if (statusLoading || settingsLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Privacy & Compliance</h1>
        <p className="text-sm text-muted-foreground">
          Manage GDPR and CCPA compliance settings for your account
        </p>
      </div>

      {/* Compliance Overview Cards */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* GDPR Status */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg flex items-center gap-2">
                <Shield className="h-5 w-5" />
                GDPR Compliance
              </CardTitle>
              <Badge variant={complianceStatus?.gdpr.percentage === 100 ? "default" : "secondary"}>
                {complianceStatus?.gdpr.percentage}%
              </Badge>
            </div>
            <CardDescription>
              General Data Protection Regulation (EU)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Progress value={complianceStatus?.gdpr.percentage} className="mb-4" />
            <p className="text-sm text-muted-foreground mb-4">
              {complianceStatus?.gdpr.completed} of {complianceStatus?.gdpr.total} requirements met
            </p>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {complianceStatus?.gdpr.checks.map((check) => (
                <div
                  key={check.id}
                  className="flex items-start gap-2 p-2 rounded-lg bg-muted/50 text-sm"
                >
                  {getStatusIcon(check.status)}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{check.label}</p>
                    <p className="text-xs text-muted-foreground truncate">{check.description}</p>
                  </div>
                  {check.action_url && check.status !== "complete" && (
                    <Button variant="ghost" size="sm" asChild>
                      <a href={check.action_url} target="_blank" rel="noopener noreferrer">
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* CCPA Status */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg flex items-center gap-2">
                <FileText className="h-5 w-5" />
                CCPA Compliance
              </CardTitle>
              <Badge variant={complianceStatus?.ccpa.percentage === 100 ? "default" : "secondary"}>
                {complianceStatus?.ccpa.percentage}%
              </Badge>
            </div>
            <CardDescription>
              California Consumer Privacy Act (US)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Progress value={complianceStatus?.ccpa.percentage} className="mb-4" />
            <p className="text-sm text-muted-foreground mb-4">
              {complianceStatus?.ccpa.completed} of {complianceStatus?.ccpa.total} requirements met
            </p>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {complianceStatus?.ccpa.checks.map((check) => (
                <div
                  key={check.id}
                  className="flex items-start gap-2 p-2 rounded-lg bg-muted/50 text-sm"
                >
                  {getStatusIcon(check.status)}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{check.label}</p>
                    <p className="text-xs text-muted-foreground truncate">{check.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Consent Management */}
      <Card>
        <CardHeader>
          <CardTitle>Consent Management</CardTitle>
          <CardDescription>
            Record your consent for data processing activities
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <p className="font-medium">Data Processing Consent</p>
              <p className="text-sm text-muted-foreground">
                Allow SpaceVoice to process your data for service delivery
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => recordConsentMutation.mutate({ consent_type: "data_processing", granted: true })}
              disabled={recordConsentMutation.isPending}
            >
              {recordConsentMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Record Consent"
              )}
            </Button>
          </div>

          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <p className="font-medium">Call Recording Consent</p>
              <p className="text-sm text-muted-foreground">
                Allow recording and transcription of voice calls
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => recordConsentMutation.mutate({ consent_type: "call_recording", granted: true })}
              disabled={recordConsentMutation.isPending}
            >
              {recordConsentMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Record Consent"
              )}
            </Button>
          </div>

          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <p className="font-medium">CCPA: Do Not Sell My Information</p>
              <p className="text-sm text-muted-foreground">
                Opt out of data sale/sharing under CCPA
              </p>
            </div>
            <Switch
              checked={privacySettings?.ccpa_opt_out ?? false}
              onCheckedChange={(checked) => ccpaOptOutMutation.mutate(checked)}
              disabled={ccpaOptOutMutation.isPending}
            />
          </div>
        </CardContent>
      </Card>

      {/* Privacy Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Privacy Settings</CardTitle>
          <CardDescription>
            Configure your privacy preferences and policies
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="privacy-policy">Privacy Policy URL</Label>
              <Input
                id="privacy-policy"
                type="url"
                placeholder="https://example.com/privacy"
                value={privacyPolicyUrl}
                onChange={(e) => setPrivacyPolicyUrl(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Link to your company&apos;s privacy policy
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="retention">Data Retention (days)</Label>
              <Input
                id="retention"
                type="number"
                min={30}
                max={365}
                value={dataRetentionDays}
                onChange={(e) => setDataRetentionDays(parseInt(e.target.value) || 365)}
              />
              <p className="text-xs text-muted-foreground">
                How long to keep call data (30-365 days)
              </p>
            </div>
          </div>
          <Button
            onClick={() =>
              updateSettingsMutation.mutate({
                privacy_policy_url: privacyPolicyUrl || null,
                data_retention_days: dataRetentionDays,
              })
            }
            disabled={updateSettingsMutation.isPending}
          >
            {updateSettingsMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save Settings
          </Button>
        </CardContent>
      </Card>

      {/* DPA Agreements */}
      <Card>
        <CardHeader>
          <CardTitle>Data Processing Agreements (DPAs)</CardTitle>
          <CardDescription>
            Acknowledge DPAs with third-party service providers
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[
              { key: "openai_dpa_signed", name: "OpenAI", url: "https://openai.com/policies/data-processing-addendum" },
              { key: "telnyx_dpa_signed", name: "Telnyx", url: "https://telnyx.com/legal/data-processing-addendum" },
              { key: "deepgram_dpa_signed", name: "Deepgram", url: "https://developers.deepgram.com/docs/data-privacy-compliance" },
              { key: "elevenlabs_dpa_signed", name: "ElevenLabs", url: "https://elevenlabs.io/dpa" },
            ].map((dpa) => (
              <div key={dpa.key} className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex items-center gap-3">
                  {privacySettings?.[dpa.key as keyof PrivacySettings] ? (
                    <Check className="h-5 w-5 text-green-500" />
                  ) : (
                    <AlertTriangle className="h-5 w-5 text-yellow-500" />
                  )}
                  <div>
                    <p className="font-medium">{dpa.name} DPA</p>
                    <a
                      href={dpa.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-primary hover:underline flex items-center gap-1"
                    >
                      View DPA <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                </div>
                <Switch
                  checked={!!privacySettings?.[dpa.key as keyof PrivacySettings]}
                  onCheckedChange={(checked) =>
                    updateSettingsMutation.mutate({ [dpa.key]: checked })
                  }
                  disabled={updateSettingsMutation.isPending}
                />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Data Rights */}
      <Card>
        <CardHeader>
          <CardTitle>Your Data Rights</CardTitle>
          <CardDescription>
            Exercise your rights under GDPR and CCPA
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <Button
              variant="outline"
              onClick={() => exportDataMutation.mutate()}
              disabled={exportDataMutation.isPending}
              className="flex-1"
            >
              {exportDataMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Download className="mr-2 h-4 w-4" />
              )}
              Export My Data
            </Button>

            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" className="flex-1">
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete All My Data
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This action cannot be undone. This will permanently delete all your data
                    including agents, contacts, call records, and settings. Your account will
                    remain active but empty.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={() => deleteDataMutation.mutate()}
                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  >
                    {deleteDataMutation.isPending && (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    )}
                    Yes, Delete Everything
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>

          {privacySettings?.last_data_export_at && (
            <p className="text-xs text-muted-foreground">
              Last export: {new Date(privacySettings.last_data_export_at).toLocaleString()}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
