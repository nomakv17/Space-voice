"use client";

import { createContext, useContext, useEffect, useState, useRef, type ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";

interface User {
  id: number;
  email: string;
  username: string;
  onboarding_completed: boolean;
  onboarding_step: number;
  is_superuser?: boolean;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string) => Promise<void>;
  logout: () => void;
  refetchUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefetching, setIsRefetching] = useState(false);
  const router = useRouter();
  const pathname = usePathname();

  // Track when we're transitioning from onboarding to prevent redirect loops
  const justCompletedOnboardingRef = useRef(false);
  // Track last redirect time to prevent rapid redirects (navigation flooding)
  const lastRedirectTimeRef = useRef(0);

  // Check for existing token on mount
  useEffect(() => {
    const storedToken = localStorage.getItem("access_token");
    if (storedToken) {
      setToken(storedToken);
      // Validate token by fetching user info
      void fetchUser(storedToken);
    } else {
      setIsLoading(false);
    }
  }, []);

  // Listen for storage changes (e.g., token cleared by axios interceptor or another tab)
  useEffect(() => {
    const handleStorageChange = (event: StorageEvent) => {
      if (event.key === "access_token") {
        if (event.newValue === null && token) {
          // Token was removed - clear state and redirect
          console.warn("Auth token cleared from storage, logging out");
          setToken(null);
          setUser(null);
        } else if (event.newValue && !token) {
          // Token was added - validate it
          void fetchUser(event.newValue);
        }
      }
    };

    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, [token]);

  // Redirect logic with debouncing to prevent navigation flooding
  useEffect(() => {
    // Don't redirect while loading or refetching user data
    if (isLoading || isRefetching) return;

    // Debounce redirects - prevent more than one redirect per second
    const now = Date.now();
    if (now - lastRedirectTimeRef.current < 1000) {
      return;
    }

    const isAuthPage = pathname === "/login";
    const isPublicPage = pathname.startsWith("/embed"); // Embed pages are public, no auth required
    const isOnboardingPage = pathname.startsWith("/onboarding");
    const isDashboardPage = pathname.startsWith("/dashboard");

    // Check sessionStorage for recent onboarding completion (survives state issues)
    const recentlyCompletedOnboarding = sessionStorage.getItem("onboarding_completed_at");
    const completedWithinLastMinute = recentlyCompletedOnboarding &&
      (now - parseInt(recentlyCompletedOnboarding, 10)) < 60000;

    if (!token && !isAuthPage && !isPublicPage) {
      lastRedirectTimeRef.current = now;
      router.push("/login");
    } else if (token && isAuthPage) {
      // Admins always go to dashboard, clients check onboarding
      lastRedirectTimeRef.current = now;
      if (user?.is_superuser || user?.onboarding_completed) {
        router.push("/dashboard");
      } else if (user && !user.onboarding_completed) {
        router.push("/onboarding");
      } else {
        router.push("/dashboard");
      }
    } else if (token && user && !user.is_superuser && !user.onboarding_completed && !isOnboardingPage && !isPublicPage) {
      // Force onboarding for non-admin users who haven't completed it
      // BUT don't redirect if we just completed onboarding OR if on dashboard and completed recently
      const skipRedirect = justCompletedOnboardingRef.current ||
        (isDashboardPage && completedWithinLastMinute);
      if (!skipRedirect) {
        lastRedirectTimeRef.current = now;
        router.push("/onboarding");
      }
    } else if (token && user?.is_superuser && isOnboardingPage) {
      // Admins should never see onboarding - redirect to dashboard
      lastRedirectTimeRef.current = now;
      router.push("/dashboard");
    }
  }, [token, isLoading, isRefetching, pathname, router, user]);

  const fetchUser = async (accessToken: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/auth/me`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        // Token invalid, clear it
        localStorage.removeItem("access_token");
        setToken(null);
      }
    } catch {
      localStorage.removeItem("access_token");
      setToken(null);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    const response = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(error.detail ?? "Login failed");
    }

    const data = await response.json();
    localStorage.setItem("access_token", data.access_token);
    setToken(data.access_token);

    // Fetch user and redirect based on role and onboarding status
    const userResponse = await fetch(`${API_BASE}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${data.access_token}` },
    });

    if (userResponse.ok) {
      const userData = await userResponse.json();
      setUser(userData);

      // Admins always go to dashboard, clients check onboarding
      if (userData.is_superuser || userData.onboarding_completed) {
        router.push("/dashboard");
      } else {
        router.push("/onboarding");
      }
    } else {
      router.push("/dashboard");
    }

    setIsLoading(false);
  };

  const register = async (email: string, username: string, password: string) => {
    const response = await fetch(`${API_BASE}/api/v1/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, username, password }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Registration failed" }));
      throw new Error(error.detail ?? "Registration failed");
    }

    // Auto-login after registration
    await login(email, password);
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    setToken(null);
    setUser(null);
    router.push("/login");
  };

  const refetchUser = async () => {
    const storedToken = localStorage.getItem("access_token");
    if (storedToken) {
      setIsRefetching(true);
      try {
        const response = await fetch(`${API_BASE}/api/v1/auth/me`, {
          headers: {
            Authorization: `Bearer ${storedToken}`,
          },
        });
        if (response.ok) {
          const userData = await response.json();
          // If onboarding just completed, set the flag to prevent redirect loops
          if (userData.onboarding_completed && user && !user.onboarding_completed) {
            justCompletedOnboardingRef.current = true;
            // Clear the flag after a short delay to allow state to settle
            setTimeout(() => {
              justCompletedOnboardingRef.current = false;
            }, 2000);
          }
          setUser(userData);
        } else {
          // Log the error but don't clear the token - let the user retry
          console.warn("Failed to refetch user:", response.status, response.statusText);
        }
      } catch (error) {
        // Network error - log but don't clear token
        console.warn("Network error during refetch:", error);
      } finally {
        setIsRefetching(false);
      }
    }
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, register, logout, refetchUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
