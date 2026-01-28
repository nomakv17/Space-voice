/**
 * API client for internal income analytics
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function getAuthHeaders(): HeadersInit {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface SimClientListItem {
  id: string;
  masked_id: string;
  descriptor: string;
  display_label: string;
  client_size: string;
  status: string;
  mrr: number;
  setup_fee: number;
  net_revenue: number;
  calls_handled_30d: number;
  last_charge_status: string;
  pricing_tier: string;
}

export interface SimClientDetail {
  id: string;
  client_id: string;
  masked_id: string;
  descriptor: string;
  client_size: string;
  industry: string;
  status: string;
  onboarded_at: string;
  processor: string;
  customer_id: string;
  subscription_id: string;
  plan_id: string;
  billing_cycle: string;
  next_charge_date: string | null;
  last_charge_date: string | null;
  last_charge_status: string;
  payment_method_type: string;
  billing_currency: string;
  mrr: number;
  arr: number;
  setup_fee: number;
  total_first_month: number;
  paid_amount: number;
  refunded_amount: number;
  chargebacks_amount: number;
  net_revenue: number;
  invoice_count: number;
  payment_count: number;
  successful_payments: number;
  failed_payments: number;
  calls_received_30d: number;
  calls_handled_30d: number;
  avg_call_duration: number;
  total_minutes_30d: number;
  pricing_tier: string;
}

export interface ClientHistoryItem {
  month: string;
  invoiced_amount: number;
  paid_amount: number;
  mrr: number;
  refunds: number;
  chargebacks: number;
  net_revenue: number;
  calls_handled: number;
  total_minutes: number;
  avg_call_duration: number;
}

export interface IncomeSummary {
  total_mrr: number;
  total_arr: number;
  total_net_revenue: number;
  total_setup_fees: number;
  active_clients: number;
  mrr_growth_pct: number;
  avg_revenue_per_client: number;
}

export interface IncomeHistoryItem {
  month: string;
  total_mrr: number;
  total_arr: number;
  total_revenue: number;
  total_setup_fees: number;
  total_refunds: number;
  total_chargebacks: number;
  total_net_revenue: number;
  active_clients: number;
  new_clients: number;
  churned_clients: number;
}

export async function listClients(filters?: {
  status?: string;
  size?: string;
}): Promise<SimClientListItem[]> {
  const params = new URLSearchParams();
  if (filters?.status) params.set("status", filters.status);
  if (filters?.size) params.set("size", filters.size);

  const url = `${API_BASE}/api/v1/internal/clients${params.toString() ? `?${params}` : ""}`;
  const response = await fetch(url, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail ?? "Failed to fetch clients");
  }

  return response.json();
}

export async function getClient(clientId: string): Promise<SimClientDetail> {
  const response = await fetch(`${API_BASE}/api/v1/internal/clients/${clientId}`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail ?? "Failed to fetch client");
  }

  return response.json();
}

export async function getClientHistory(clientId: string): Promise<ClientHistoryItem[]> {
  const response = await fetch(`${API_BASE}/api/v1/internal/clients/${clientId}/history`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail ?? "Failed to fetch client history");
  }

  return response.json();
}

export async function getIncomeSummary(month?: string): Promise<IncomeSummary> {
  const params = new URLSearchParams();
  if (month) params.set("month", month);

  const url = `${API_BASE}/api/v1/internal/income/summary${params.toString() ? `?${params}` : ""}`;
  const response = await fetch(url, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail ?? "Failed to fetch income summary");
  }

  return response.json();
}

export async function getIncomeHistory(): Promise<IncomeHistoryItem[]> {
  const response = await fetch(`${API_BASE}/api/v1/internal/income/history`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail ?? "Failed to fetch income history");
  }

  return response.json();
}

export async function seedData(): Promise<{ message: string }> {
  const response = await fetch(`${API_BASE}/api/v1/internal/seed`, {
    method: "POST",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail ?? "Failed to seed data");
  }

  return response.json();
}

export async function reseedData(): Promise<{ message: string }> {
  const response = await fetch(`${API_BASE}/api/v1/internal/reseed`, {
    method: "POST",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail ?? "Failed to reseed data");
  }

  return response.json();
}
