import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { customersApi } from "../api/endpoints";
import { useDebounce } from "../hooks/useDebounce";
import { Empty, ErrorState, Loading } from "../components/States";
import { StatusBadge } from "../components/StatusBadge";
import { InteractionModal } from "../components/InteractionModal";
import { OrderModal } from "../components/OrderModal";
import { FollowUpModal } from "../components/FollowUpModal";
import { dateTime, money, waLink } from "../utils/format";

type Act = { kind: "interaction" | "order" | "followup"; id: string; channel?: string } | null;

export default function MyCustomersPage() {
  const [q, setQ] = useState(""); const [page, setPage] = useState(1); const [act, setAct] = useState<Act>(null);
  const dq = useDebounce(q);
  const query = useQuery({ queryKey: ["my-customers", dq, page], queryFn: () => customersApi.mine({ q: dq, page, page_size: 20 }), placeholderData: (p) => p });
  const pages = query.data ? Math.max(1, Math.ceil(query.data.total / query.data.page_size)) : 1;
  return (
    <div className="space-y-3">
      <input className="input" placeholder="بحث بالاسم أو الهاتف أو الكود" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
      {query.isLoading ? <Loading /> : query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> :
        query.data!.items.length === 0 ? <Empty text="لا يوجد عملاء مطابقون للبحث" /> : (
          <ul className="space-y-3">
            {query.data!.items.map((c) => (
              <li key={c.id} className="card space-y-3">
                <div className="flex justify-between items-start gap-2">
                  <div>
                    <Link to={`/customers/${c.id}`} className="font-bold text-lg">{c.name}</Link>
                    <div className="text-sm text-gray-500" dir="ltr">{c.phone}</div>
                  </div>
                  <StatusBadge code={c.latest_status_code} fallback={c.latest_status_label} />
                </div>
                <div className="text-xs text-gray-500 flex flex-wrap gap-x-4">
                  <span>آخر تفاعل: {dateTime(c.latest_interaction_at)}</span>
                  <span>آخر أوردر: {dateTime(c.latest_order_at)} {c.latest_order_total != null && `(${money(c.latest_order_total)})`}</span>
                </div>
                <div className="grid grid-cols-4 gap-2">
                  <a className="btn btn-ghost" href={`tel:${c.phone}`} onClick={() => setAct({ kind: "interaction", id: c.id, channel: "call" })}>اتصال</a>
                  <a className="btn btn-ghost" href={waLink(c.whatsapp ?? c.phone)} target="_blank" rel="noreferrer" onClick={() => setAct({ kind: "interaction", id: c.id, channel: "whatsapp" })}>واتساب</a>
                  <button className="btn btn-ghost" onClick={() => setAct({ kind: "followup", id: c.id })}>متابعة</button>
                  <button className="btn btn-primary" onClick={() => setAct({ kind: "order", id: c.id })}>أوردر</button>
                </div>
              </li>
            ))}
          </ul>
        )}
      {pages > 1 && (
        <div className="flex items-center justify-between">
          <button className="btn btn-ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>السابق</button>
          <span className="text-sm">{page} / {pages}</span>
          <button className="btn btn-ghost" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>التالي</button>
        </div>
      )}
      {act?.kind === "interaction" && <InteractionModal customerId={act.id} channel={act.channel} onClose={() => setAct(null)} />}
      {act?.kind === "order" && <OrderModal customerId={act.id} onClose={() => setAct(null)} />}
      {act?.kind === "followup" && <FollowUpModal customerId={act.id} onClose={() => setAct(null)} />}
    </div>
  );
}
