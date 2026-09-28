export type Role = "SYSTEM_MANAGER" | "EMPLOYEE";

export interface User { id: string; username: string; full_name: string; role: Role; is_active: boolean; }

export interface Paginated<T> { items: T[]; total: number; page: number; page_size: number; }

export interface Customer {
  id: string; customer_code: string; name: string; phone: string; whatsapp: string | null;
  address: string | null; governorate: string | null;
  assigned_employee_id?: string | null; assigned_employee_name?: string | null;
  latest_status_code?: string | null; latest_status_label?: string | null;
  latest_interaction_at?: string | null; latest_order_at?: string | null; latest_order_total?: number | null;
}

export interface Employee {
  id: string; username: string; full_name: string; is_active: boolean; deleted_at: string | null;
  assigned_customers_count: number;
}

export interface Variant { id: string; unit_label: string; price: number; is_active: boolean; }
export interface Product { id: string; sku: string; name_ar: string; category: string | null; variants: Variant[]; }
export interface BundleItem { product_variant_id: string; quantity: number; variant_label?: string; product_name?: string; }
export interface Bundle { id: string; name: string; bundle_price: number; regular_total: number | null; is_active: boolean; items: BundleItem[]; }

export interface OrderItem { id: string; name_snapshot: string; unit_price: number; quantity: number; line_total: number; }
export interface Order {
  id: string; order_number: string; customer_id: string; employee_id: string;
  subtotal: number; discount_amount: number; shipping_amount: number; total_amount: number;
  status: string; created_at: string; items: OrderItem[];
}

export interface Interaction { id: string; channel: string; status_code: string | null; note: string | null; created_at: string; }
export interface FollowUp { id: string; customer_id: string; due_at: string; note: string | null; is_done: boolean; }
export interface StatusConfig { id: string; code: string; label_ar: string; color_hex: string; sort_order: number; is_active: boolean; }

export interface ManagerDashboard {
  total_customers: number; assigned_customers: number; unassigned_customers: number; total_employees: number;
  orders_today: number; orders_this_week: number; orders_this_month: number; sales_total_period: number;
  customers_not_contacted: number; followups_due: number; customers_needing_retry: number;
}
export interface Workspace {
  assigned_customers: number; contacted_today: number; not_contacted_today: number;
  followups_due_today: number; orders_today: number; sales_today: number;
}
