import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ordersApi } from "../api/endpoints";
import { useAuth } from "../features/auth/AuthContext";
import { Empty, ErrorState, Loading } from "../components/States";
import { useToast } from "../components/Toast";
import { dateTime, money } from "../utils/format";

export default function OrdersPage() {
  const { user } = useAuth(); const [page, setPage] = useState(1); const toast = useToast(); const qc = useQueryClient();
  const q = useQuery({ queryKey: ["orders", page], queryFn: () => ordersApi.list({ page }), placeholderData: (p) => p });
  const cancel = useMutation({ mutationFn: ordersApi.cancel, onSuccess: () => { toast("success", "تم إلغاء الأوردر"); void qc.invalidateQueries({ queryKey: ["orders"] }); }, onError: (e: Error) => toast("error", e.message) });
  if (q.isLoading) return <Loading />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => void q.refetch()} />;
  const pages = Math.max(1, Math.ceil(q.data!.total / q.data!.page_size));
  return (
    <div className="space-y-3">
      {q.data!.items.length === 0 ? <Empty text="لا توجد أوردرات" /> : q.data!.items.map((o) => (
        <div key={o.id} className="card text-sm space-y-1">
          <div className="flex justify-between font-semibold"><span>{o.order_number}</span><span>{money(o.total_amount)}</span></div>
          <div className="text-gray-500">{dateTime(o.created_at)} — {o.status}</div>
          <div>{o.items.map((i) => `${i.name_snapshot} ×${i.quantity}`).join("، ")}</div>
          <div className="flex gap-2 pt-1"><Link className="btn btn-ghost !min-h-[40px]" to={`/customers/${o.customer_id}`}>العميل</Link>
            {user?.role === "SYSTEM_MANAGER" && o.status !== "CANCELLED" && <button className="btn btn-danger !min-h-[40px]" disabled={cancel.isPending} onClick={() => window.confirm("إلغاء هذا الأوردر؟") && cancel.mutate(o.id)}>إلغاء</button>}</div>
        </div>))}
      {pages > 1 && <div className="flex items-center justify-between"><button className="btn btn-ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>السابق</button><span>{page} / {pages}</span><button className="btn btn-ghost" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>التالي</button></div>}
    </div>
  );
}
