import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "../api/endpoints";
import { useAuth } from "../features/auth/AuthContext";
import { ErrorState, Loading } from "../components/States";
import { money, num } from "../utils/format";

const Stat = ({ label, value, tone = "" }: { label: string; value: string; tone?: string }) => (
  <div className="card"><div className="text-sm text-gray-500">{label}</div><div className={`text-2xl font-bold mt-1 ${tone}`}>{value}</div></div>
);

function ManagerHome() {
  const q = useQuery({ queryKey: ["dash-manager"], queryFn: dashboardApi.manager });
  if (q.isLoading) return <Loading />;
  if (q.isError || !q.data) return <ErrorState error={q.error} onRetry={() => void q.refetch()} />;
  const d = q.data;
  return (
    <div className="grid grid-cols-2 gap-3">
      <Stat label="إجمالي العملاء" value={num(d.total_customers)} /><Stat label="عملاء غير مخصصين" value={num(d.unassigned_customers)} tone="text-amber-600" />
      <Stat label="عملاء مخصصون" value={num(d.assigned_customers)} /><Stat label="الموظفات" value={num(d.total_employees)} />
      <Stat label="أوردرات اليوم" value={num(d.orders_today)} /><Stat label="أوردرات الشهر" value={num(d.orders_this_month)} />
      <Stat label="إجمالي المبيعات" value={money(d.sales_total_period)} tone="text-brand-700" /><Stat label="لم يُتواصل معهم" value={num(d.customers_not_contacted)} tone="text-red-600" />
      <Stat label="متابعات مستحقة" value={num(d.followups_due)} /><Stat label="تحتاج إعادة محاولة" value={num(d.customers_needing_retry)} />
    </div>
  );
}

function EmployeeHome() {
  const q = useQuery({ queryKey: ["dash-ws"], queryFn: dashboardApi.workspace });
  if (q.isLoading) return <Loading />;
  if (q.isError || !q.data) return <ErrorState error={q.error} onRetry={() => void q.refetch()} />;
  const w = q.data;
  const progress = w.assigned_customers ? Math.round((w.contacted_today / w.assigned_customers) * 100) : 0;
  return (
    <div className="space-y-3">
      <div className="card"><div className="flex justify-between text-sm mb-2"><span>تقدّم اليوم</span><span>{num(progress)}%</span></div>
        <div className="h-3 rounded-full bg-gray-100 overflow-hidden"><div className="h-full bg-brand-600" style={{ width: `${progress}%` }} /></div></div>
      <div className="grid grid-cols-2 gap-3">
        <Stat label="عملائي" value={num(w.assigned_customers)} /><Stat label="تم التواصل اليوم" value={num(w.contacted_today)} tone="text-brand-700" />
        <Stat label="لم يُتواصل" value={num(w.not_contacted_today)} tone="text-red-600" /><Stat label="متابعات اليوم" value={num(w.followups_due_today)} />
        <Stat label="أوردرات اليوم" value={num(w.orders_today)} /><Stat label="مبيعات اليوم" value={money(w.sales_today)} tone="text-brand-700" />
      </div>
    </div>
  );
}

export default function HomePage() {
  const { user } = useAuth();
  return user?.role === "SYSTEM_MANAGER" ? <ManagerHome /> : <EmployeeHome />;
}
