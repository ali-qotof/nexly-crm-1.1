import { api } from "./client";
import type {
  Bundle, Customer, Employee, FollowUp, Interaction, ManagerDashboard, Order, Paginated, Product,
  StatusConfig, User, Workspace,
} from "../types";

const qs = (o: Record<string, string | number | boolean | undefined | null>) => {
  const p = new URLSearchParams();
  Object.entries(o).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "") p.set(k, String(v)); });
  const s = p.toString();
  return s ? `?${s}` : "";
};

export const authApi = {
  login: (username: string, password: string) => api<{ user: User }>("/auth/login", { method: "POST", body: { username, password }, noRefresh: true }),
  logout: () => api<void>("/auth/logout", { method: "POST", noRefresh: true }),
  me: (signal?: AbortSignal) => api<User>("/auth/me", { signal, timeoutMs: 6000, noRefresh: true }),
  refresh: (signal?: AbortSignal) => api<{ user: User }>("/auth/refresh", { method: "POST", signal, timeoutMs: 6000, noRefresh: true }),
};

export const customersApi = {
  mine: (p: { q?: string; page?: number; page_size?: number }) => api<Paginated<Customer>>(`/customers/my${qs(p)}`),
  all: (p: { q?: string; page?: number; page_size?: number; unassigned_only?: boolean }) => api<Paginated<Customer>>(`/customers${qs(p)}`),
  timeline: (id: string) => api<Interaction[]>(`/customers/${id}/interactions`),
};

export const interactionsApi = {
  create: (b: { customer_id: string; channel: string; status_code?: string; note?: string }) => api<Interaction>("/interactions", { method: "POST", body: b }),
};
export const followupsApi = {
  list: (bucket?: string) => api<FollowUp[]>(`/followups${qs({ bucket })}`),
  create: (b: { customer_id: string; due_at: string; note?: string }) => api<FollowUp>("/followups", { method: "POST", body: b }),
  done: (id: string) => api<FollowUp>(`/followups/${id}`, { method: "PATCH", body: { is_done: true } }),
};
export const ordersApi = {
  list: (p: { customer_id?: string; page?: number }) => api<Paginated<Order>>(`/orders${qs(p)}`),
  create: (b: unknown) => api<Order>("/orders", { method: "POST", body: b }),
  cancel: (id: string) => api<Order>(`/orders/${id}/cancel`, { method: "POST" }),
};
export const productsApi = {
  list: (q?: string) => api<Product[]>(`/products${qs({ q })}`),
  bundles: () => api<Bundle[]>("/bundles?active_only=true"),
};
export const settingsApi = { statuses: () => api<StatusConfig[]>("/settings/statuses") };
export const employeesApi = {
  list: () => api<Employee[]>("/employees"),
  create: (b: { username: string; full_name: string; password: string }) => api<Employee>("/employees", { method: "POST", body: b }),
  setActive: (id: string, is_active: boolean) => api<Employee>(`/employees/${id}`, { method: "PATCH", body: { is_active } }),
  remove: (id: string, manager_password: string) => api<void>(`/employees/${id}/delete`, { method: "POST", body: { manager_password } }),
};
export const assignmentsApi = {
  assign: (customer_ids: string[], employee_id: string) => api<{ assigned: number; skipped_already_assigned: number }>("/assignments/assign", { method: "POST", body: { customer_ids, employee_id } }),
  unassign: (customer_ids: string[]) => api<{ assigned: number }>("/assignments/unassign", { method: "POST", body: { customer_ids } }),
  importPreview: (file: File) => { const f = new FormData(); f.append("file", file); return api<ImportPreview>("/assignments/import/preview", { method: "POST", form: f, timeoutMs: 60_000 }); },
  importConfirm: (matched_customer_ids: string[], employee_id: string) => api<{ assigned: number }>("/assignments/import/confirm", { method: "POST", body: { matched_customer_ids, employee_id } }),
};
export interface ImportPreview {
  total_rows: number; matched_count: number; missing_count: number; duplicate_count: number; invalid_count: number;
  matched: { matched_customer_id: string }[];
}
export const dashboardApi = {
  manager: () => api<ManagerDashboard>("/dashboard/manager"),
  workspace: () => api<Workspace>("/dashboard/my-workspace"),
};
