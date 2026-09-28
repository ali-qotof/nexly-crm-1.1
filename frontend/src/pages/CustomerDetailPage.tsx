import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { customersApi, ordersApi } from "../api/endpoints";
import type { Customer } from "../types";
import { ErrorState, Loading, Empty } from "../components/States";
import { StatusBadge } from "../components/StatusBadge";
import { InteractionModal } from "../components/InteractionModal";
import { OrderModal } from "../components/OrderModal";
import { FollowUpModal } from "../components/FollowUpModal";
import { dateTime, money, waLink } from "../utils/format";

const CHANNEL: Record<string, string> = { call: "اتصال", whatsapp: "واتساب", note: "ملاحظة" };

export default function CustomerDetailPage() {
  const { id = "" } = useParams();
  const [act, setAct] = useState<"interaction" | "order" | "followup" | null>(null);
  const cq = useQuery({ queryKey: ["customer", id], queryFn: () => api<Customer>(`/customers/${id}`) });
  const tq = useQuery({ queryKey: ["timeline", id], queryFn: () => customersApi.timeline(id) });
  const oq = useQuery({ queryKey: ["customer-orders", id], queryFn: () => ordersApi.list({ customer_id: id }) });

  if (cq.isLoading) return <Loading />;
  if (cq.isError) return <ErrorState error={cq.error} onRetry={() => void cq.refetch()} />;
  const c = cq.data!;
  return (
    <div className="space-y-4">
      <section className="card space-y-2">
        <h1 className="text-xl font-bold">{c.name}</h1>
        <div className="text-sm text-gray-600 space-y-1">
          <div>الكود: {c.customer_code}</div><div dir="ltr" className="text-right">{c.phone}</div>
          {c.address && <div>{c.address}</div>}{c.governorate && <div>المحافظة: {c.governorate}</div>}
        </div>
        <div className="grid grid-cols-4 gap-2 pt-2">
          <a className="btn btn-ghost" href={`tel:${c.phone}`}>اتصال</a>
          <a className="btn btn-ghost" href={waLink(c.whatsapp ?? c.phone)} target="_blank" rel="noreferrer">واتساب</a>
          <button className="btn btn-ghost" onClick={() => setAct("interaction")}>تفاعل</button>
          <button className="btn btn-primary" onClick={() => setAct("order")}>أوردر</button>
        </div>
        <button className="btn btn-ghost w-full" onClick={() => setAct("followup")}>إضافة متابعة</button>
      </section>

      <section className="card">
        <h2 className="font-bold mb-2">الأوردرات</h2>
        {oq.isLoading ? <Loading /> : oq.isError ? <ErrorState error={oq.error} onRetry={() => void oq.refetch()} /> :
          oq.data!.items.length === 0 ? <Empty text="لا توجد أوردرات" /> : (
            <ul className="divide-y">
              {oq.data!.items.map((o) => (
                <li key={o.id} className="py-3 text-sm">
                  <div className="flex justify-between font-semibold"><span>{o.order_number}</span><span>{money(o.total_amount)}</span></div>
                  <div className="text-gray-500">{dateTime(o.created_at)} — {o.status}</div>
                  <div className="text-gray-600">{o.items.map((i) => `${i.name_snapshot} ×${i.quantity}`).join("، ")}</div>
                  <div className="text-xs text-gray-400">خصم {money(o.discount_amount)} · شحن {money(o.shipping_amount)}</div>
                </li>
              ))}
            </ul>
          )}
      </section>

      <section className="card">
        <h2 className="font-bold mb-2">سجل التواصل</h2>
        {tq.isLoading ? <Loading /> : tq.isError ? <ErrorState error={tq.error} onRetry={() => void tq.refetch()} /> :
          tq.data!.length === 0 ? <Empty text="لا يوجد تواصل مسجّل" /> : (
            <ol className="space-y-3 border-r-2 border-brand-100 pr-3">
              {tq.data!.map((i) => (
                <li key={i.id} className="text-sm">
                  <div className="flex items-center gap-2"><strong>{CHANNEL[i.channel] ?? i.channel}</strong><StatusBadge code={i.status_code} /></div>
                  {i.note && <p className="text-gray-700">{i.note}</p>}
                  <time className="text-xs text-gray-400">{dateTime(i.created_at)}</time>
                </li>
              ))}
            </ol>
          )}
      </section>
      {act === "interaction" && <InteractionModal customerId={id} onClose={() => setAct(null)} />}
      {act === "order" && <OrderModal customerId={id} onClose={() => setAct(null)} />}
      {act === "followup" && <FollowUpModal customerId={id} onClose={() => setAct(null)} />}
    </div>
  );
}
