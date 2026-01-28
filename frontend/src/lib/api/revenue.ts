/**
 * API client for revenue analytics (from actual call records)
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function getAuthHeaders(): HeadersInit {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface RevenueSummary {
  total_revenue: number;
  total_cost: number;
  total_profit: number;
  profit_margin_pct: number;
  total_calls: number;
  completed_calls: number;
  total_minutes: number;
  avg_call_duration_secs: number;
  avg_revenue_per_call: number;
  unique_users: number;
}

export interface MonthlyRevenue {
  year: number;
  month: number;
  month_name: string;
  total_revenue: number;
  total_cost: number;
  total_profit: number;
  total_calls: number;
  completed_calls: number;
  total_minutes: number;
  unique_users: number;
}

export interface SeedResponse {
  message: string;
  users_created?: number;
  calls_created?: number;
  total_revenue?: number;
}

export async function getRevenueSummary(
  year?: number,
  month?: number
): Promise<RevenueSummary> {
  const params = new URLSearchParams();
  if (year) params.set("year", year.toString());
  if (month) params.set("month", month.toString());

  const url = `${API_BASE}/api/v1/revenue/summary${params.toString() ? `?${params}` : ""}`;
  const response = await fetch(url, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail ?? "Failed to fetch revenue summary");
  }

  return response.json();
}

export async function getRevenueHistory(limit: number = 12): Promise<MonthlyRevenue[]> {
  const url = `${API_BASE}/api/v1/revenue/history?limit=${limit}`;
  const response = await fetch(url, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail ?? "Failed to fetch revenue history");
  }

  return response.json();
}

export async function seedRevenue(): Promise<SeedResponse> {
  const response = await fetch(`${API_BASE}/api/v1/revenue/seed`, {
    method: "POST",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail ?? "Failed to seed revenue data");
  }

  return response.json();
}

export async function reseedRevenue(): Promise<SeedResponse> {
  const response = await fetch(`${API_BASE}/api/v1/revenue/reseed`, {
    method: "POST",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail ?? "Failed to reseed revenue data");
  }

  return response.json();
}
