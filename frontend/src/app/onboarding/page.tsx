"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, User, Building2, Users, Briefcase } from "lucide-react";
import { toast } from "sonner";

const COMPANY_SIZES = [
  { value: "solo", label: "Solo / Freelancer" },
  { value: "2-10", label: "2-10 employees" },
  { value: "11-50", label: "11-50 employees" },
  { value: "51-200", label: "51-200 employees" },
  { value: "200+", label: "200+ employees" },
];

const INDUSTRIES = [
  { value: "real-estate", label: "Real Estate" },
  { value: "healthcare", label: "Healthcare" },
  { value: "legal", label: "Legal Services" },
  { value: "hvac", label: "HVAC / Home Services" },
  { value: "automotive", label: "Automotive" },
  { value: "insurance", label: "Insurance" },
  { value: "finance", label: "Finance" },
  { value: "retail", label: "Retail / E-commerce" },
  { value: "hospitality", label: "Hospitality" },
  { value: "technology", label: "Technology" },
  { value: "other", label: "Other" },
];

export default function OnboardingProfilePage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [formData, setFormData] = useState({
    full_name: "",
    company_name: "",
    company_size: "",
    industry: "",
    phone_number: "",
  });

  const updateProfile = useMutation({
    mutationFn: async (data: typeof formData) => {
      const response = await api.post("/api/v1/onboarding/profile", data);
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["onboarding-status"] });
      toast.success("Profile saved!");
      router.push("/onboarding/telephony");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to save profile");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateProfile.mutate(formData);
  };

  const isValid =
    formData.full_name.trim() !== "" &&
    formData.company_name.trim() !== "" &&
    formData.company_size !== "" &&
    formData.industry !== "";

  return (
    <Card className="border-white/10 bg-white/[0.02]">
      <CardHeader className="text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-500/10">
          <User className="h-8 w-8 text-indigo-400" />
        </div>
        <CardTitle className="text-2xl">Welcome to SpaceVoice</CardTitle>
        <CardDescription>
          Let&apos;s set up your profile to get started with AI voice agents
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="full_name" className="flex items-center gap-2">
              <User className="h-4 w-4 text-muted-foreground" />
              Full Name
            </Label>
            <Input
              id="full_name"
              placeholder="John Smith"
              value={formData.full_name}
              onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="company_name" className="flex items-center gap-2">
              <Building2 className="h-4 w-4 text-muted-foreground" />
              Company Name
            </Label>
            <Input
              id="company_name"
              placeholder="Acme Corporation"
              value={formData.company_name}
              onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="company_size" className="flex items-center gap-2">
              <Users className="h-4 w-4 text-muted-foreground" />
              Company Size
            </Label>
            <Select
              value={formData.company_size}
              onValueChange={(value) => setFormData({ ...formData, company_size: value })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select company size" />
              </SelectTrigger>
              <SelectContent>
                {COMPANY_SIZES.map((size) => (
                  <SelectItem key={size.value} value={size.value}>
                    {size.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="industry" className="flex items-center gap-2">
              <Briefcase className="h-4 w-4 text-muted-foreground" />
              Industry
            </Label>
            <Select
              value={formData.industry}
              onValueChange={(value) => setFormData({ ...formData, industry: value })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select your industry" />
              </SelectTrigger>
              <SelectContent>
                {INDUSTRIES.map((industry) => (
                  <SelectItem key={industry.value} value={industry.value}>
                    {industry.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="phone_number" className="flex items-center gap-2 text-muted-foreground">
              Phone Number (Optional)
            </Label>
            <Input
              id="phone_number"
              type="tel"
              placeholder="+1 (555) 123-4567"
              value={formData.phone_number}
              onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
            />
          </div>

          <Button
            type="submit"
            className="w-full"
            disabled={!isValid || updateProfile.isPending}
          >
            {updateProfile.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              "Continue"
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
