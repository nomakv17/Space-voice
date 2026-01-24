"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2, CheckCircle, XCircle, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type TokenStatus = "loading" | "success" | "error" | "expired" | "used";

export default function AccessTokenPage() {
  const params = useParams();
  const router = useRouter();
  const token = params.token as string;

  const [status, setStatus] = useState<TokenStatus>("loading");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [isReadOnly, setIsReadOnly] = useState<boolean>(false);

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setErrorMessage("No access token provided");
      return;
    }

    const consumeToken = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/v1/auth/access/${token}`);

        if (response.ok) {
          const data = await response.json();

          // Store the JWT token
          localStorage.setItem("access_token", data.access_token);

          // Store read-only flag if applicable
          if (data.is_read_only) {
            localStorage.setItem("is_read_only", "true");
            setIsReadOnly(true);
          }

          setStatus("success");

          // Redirect to dashboard after short delay
          setTimeout(() => {
            router.push("/dashboard");
          }, 2000);
        } else {
          const error = await response.json().catch(() => ({ detail: "Unknown error" }));
          const errorDetail = error.detail ?? "Failed to validate access link";

          // Determine error type
          if (response.status === 410) {
            if (errorDetail.includes("already been used")) {
              setStatus("used");
            } else if (errorDetail.includes("expired")) {
              setStatus("expired");
            } else {
              setStatus("error");
            }
          } else if (response.status === 404) {
            setStatus("error");
          } else {
            setStatus("error");
          }

          setErrorMessage(errorDetail);
        }
      } catch {
        setStatus("error");
        setErrorMessage("Network error. Please check your connection and try again.");
      }
    };

    void consumeToken();
  }, [token, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-gray-50 to-white p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4">
            {status === "loading" && (
              <div className="h-16 w-16 rounded-full bg-blue-100 flex items-center justify-center">
                <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
              </div>
            )}
            {status === "success" && (
              <div className="h-16 w-16 rounded-full bg-emerald-100 flex items-center justify-center">
                <CheckCircle className="h-8 w-8 text-emerald-600" />
              </div>
            )}
            {(status === "error" || status === "used" || status === "expired") && (
              <div className="h-16 w-16 rounded-full bg-red-100 flex items-center justify-center">
                {status === "used" || status === "expired" ? (
                  <AlertTriangle className="h-8 w-8 text-amber-600" />
                ) : (
                  <XCircle className="h-8 w-8 text-red-600" />
                )}
              </div>
            )}
          </div>

          <CardTitle className="text-2xl">
            {status === "loading" && "Validating Access Link..."}
            {status === "success" && "Access Granted!"}
            {status === "used" && "Link Already Used"}
            {status === "expired" && "Link Expired"}
            {status === "error" && "Invalid Link"}
          </CardTitle>

          <CardDescription className="mt-2">
            {status === "loading" && "Please wait while we verify your access link."}
            {status === "success" && (
              <>
                Redirecting you to the dashboard...
                {isReadOnly && (
                  <span className="block mt-2 text-amber-600 font-medium">
                    You have read-only access.
                  </span>
                )}
              </>
            )}
            {status === "used" &&
              "This access link has already been used. Each link can only be used once."}
            {status === "expired" &&
              "This access link has expired. Please request a new link."}
            {status === "error" && (errorMessage || "The access link is invalid.")}
          </CardDescription>
        </CardHeader>

        <CardContent>
          {status === "success" && (
            <div className="flex justify-center">
              <Loader2 className="h-5 w-5 text-muted-foreground animate-spin" />
            </div>
          )}

          {(status === "error" || status === "used" || status === "expired") && (
            <div className="space-y-4">
              <div className="rounded-lg bg-muted p-4 text-sm text-muted-foreground">
                <p>If you believe this is an error, please contact the administrator who shared this link with you.</p>
              </div>

              <Button
                variant="outline"
                className="w-full"
                onClick={() => router.push("/login")}
              >
                Go to Login
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
