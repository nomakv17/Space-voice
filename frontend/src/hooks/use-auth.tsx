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
  const router = useRouter();
  const pathname = usePathname();

  // HARD PROTECTION: Prevent any navigation for 2 seconds after a redirect
  const lastNavigationRef = useRef<number>(0);
  const hasNavigatedRef = useRef<boolean>(false);

  // Check for existing token on mount
  useEffect(() => {
    const storedToken = localStorage.getItem("access_token");
    if (storedToken) {
      setToken(storedToken);
      void fetchUser(storedToken);
    } else {
      setIsLoading(false);
    }
  }, []);

  // SIMPLIFIED redirect logic - only handle: no token → login, login page with token → dashboard
  useEffect(() => {
    if (isLoading) return;

    // HARD PROTECTION: Only allow one navigation per 3 seconds
    const now = Date.now();
    if (hasNavigatedRef.current && now - lastNavigationRef.current < 3000) {
      return;
    }

    const isAuthPage = pathname === "/login";
    const isLandingPage = pathname === "/";
    const isPublicPage = pathname.startsWith("/embed");

    if (!token && !isAuthPage && !isLandingPage && !isPublicPage) {
      // No token and not on login/public page → go to login
      hasNavigatedRef.current = true;
      lastNavigationRef.current = now;
      router.push("/login");
    } else if (token && isAuthPage) {
      // Has token and on login page → go to dashboard
      hasNavigatedRef.current = true;
      lastNavigationRef.current = now;
      router.push("/dashboard");
    }
    // REMOVED: Force redirect to onboarding - users can navigate where they want
    // NOTE: router is intentionally excluded from deps - it's stable in Next.js but
    // including it causes unnecessary re-renders that trigger excessive History API calls
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, isLoading, pathname]);

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
      try {
        const response = await fetch(`${API_BASE}/api/v1/auth/me`, {
          headers: {
            Authorization: `Bearer ${storedToken}`,
          },
        });
        if (response.ok) {
          const userData = await response.json();
          setUser(userData);
        } else {
          console.warn("Failed to refetch user:", response.status);
        }
      } catch (error) {
        console.warn("Network error during refetch:", error);
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
