import uuid

from pydantic import BaseModel


class ManagerDashboardOut(BaseModel):
    total_customers: int
    assigned_customers: int
    unassigned_customers: int
    total_employees: int
    orders_today: int
    orders_this_week: int
    orders_this_month: int
    sales_total_period: float
    customers_not_contacted: int
    followups_due: int
    customers_needing_retry: int


class EmployeePerformanceRow(BaseModel):
    employee_id: uuid.UUID
    employee_name: str
    assigned_customers: int
    contacted: int
    not_contacted: int
    orders_count: int
    sales_total: float
    conversion_rate: float
    followups_pending: int


class EmployeeWorkspaceOut(BaseModel):
    assigned_customers: int
    contacted_today: int
    not_contacted_today: int
    followups_due_today: int
    orders_today: int
    sales_today: float
