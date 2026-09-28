import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ordersApi, productsApi } from "../api/endpoints";
import { money } from "../utils/format";
import { useToast } from "./Toast";
import { Modal } from "./Modal";
import { Loading } from "./States";

interface Line { key: string; kind: "variant" | "bundle"; id: string; name: string; price: number; qty: number; }

/**
 * تسجيل أوردر (القاعدة 17-20). الإجمالي المعروض هنا تقدير فوري فقط — الرقم النهائي المحفوظ
 * يأتي من الـ Backend (Source of Truth). مفتاح Idempotency يُولَّد مرة واحدة عند فتح النافذة،
 * فأي ضغط متكرر على "حفظ" يُنتج أوردرًا واحدًا فقط.
 */
export function OrderModal({ customerId, onClose }: { customerId: string; onClose: () => void }) {
  const toast = useToast(); const qc = useQueryClient();
  const [idemKey] = useState(() => crypto.randomUUID());
  const [q, setQ] = useState(""); const [lines, setLines] = useState<Line[]>([]);
  const [dType, setDType] = useState<"" | "PERCENTAGE" | "FIXED">(""); const [dVal, setDVal] = useState("");
  const [notes, setNotes] = useState("");
  const products = useQuery({ queryKey: ["products"], queryFn: () => productsApi.list() });
  const bundles = useQuery({ queryKey: ["bundles"], queryFn: productsApi.bundles });

  const options = useMemo(() => {
    const term = q.trim();
    const v = (products.data ?? []).flatMap((p) => p.variants.filter((x) => x.is_active).map((x) => ({ kind: "variant" as const, id: x.id, name: `${p.name_ar} ${x.unit_label}`, price: x.price })));
    const b = (bundles.data ?? []).map((x) => ({ kind: "bundle" as const, id: x.id, name: `🎁 ${x.name}`, price: x.bundle_price }));
    return [...b, ...v].filter((o) => !term || o.name.includes(term)).slice(0, 30);
  }, [products.data, bundles.data, q]);

  const add = (o: { kind: "variant" | "bundle"; id: string; name: string; price: number }) =>
    setLines((l) => l.some((x) => x.id === o.id) ? l.map((x) => x.id === o.id ? { ...x, qty: x.qty + 1 } : x) : [...l, { ...o, key: o.id, qty: 1 }]);
  const setQty = (id: string, qty: number) => setLines((l) => qty <= 0 ? l.filter((x) => x.id !== id) : l.map((x) => x.id === id ? { ...x, qty } : x));
  const estimate = lines.reduce((s, l) => s + l.price * l.qty, 0);

  const m = useMutation({
    mutationFn: () => ordersApi.create({
      idempotency_key: idemKey, customer_id: customerId, notes: notes || undefined,
      items: lines.map((l) => ({ [l.kind === "variant" ? "product_variant_id" : "bundle_id"]: l.id, quantity: l.qty })),
      discount_type: dType || undefined, discount_value: dType && dVal ? Number(dVal) : undefined,
    }),
    onSuccess: (o) => { toast("success", `تم حفظ الأوردر ${o.order_number} — الإجمالي ${money(o.total_amount)}`); qc.invalidateQueries(); onClose(); },
    onError: (e: Error) => toast("error", e.message),
  });

  return (
    <Modal title="تسجيل أوردر" onClose={onClose}>
      <div className="space-y-3">
        <input className="input" placeholder="ابحث عن منتج أو عرض…" value={q} onChange={(e) => setQ(e.target.value)} />
        {(products.isLoading || bundles.isLoading) ? <Loading /> : (
          <div className="max-h-40 overflow-y-auto rounded-xl border divide-y">
            {options.map((o) => (
              <button key={o.id} className="w-full flex justify-between px-3 py-3 text-right hover:bg-gray-50" onClick={() => add(o)}>
                <span>{o.name}</span><span className="text-brand-700 font-semibold">{money(o.price)}</span>
              </button>
            ))}
          </div>
        )}
        {lines.length > 0 && (
          <ul className="space-y-2">
            {lines.map((l) => (
              <li key={l.key} className="flex items-center justify-between gap-2 rounded-xl bg-gray-50 p-2">
                <span className="flex-1 text-sm">{l.name}</span>
                <div className="flex items-center gap-1">
                  <button className="btn btn-ghost !min-h-[40px] !px-3" onClick={() => setQty(l.id, l.qty - 1)} aria-label="إنقاص">−</button>
                  <span className="w-8 text-center">{l.qty}</span>
                  <button className="btn btn-ghost !min-h-[40px] !px-3" onClick={() => setQty(l.id, l.qty + 1)} aria-label="زيادة">+</button>
                </div>
              </li>
            ))}
          </ul>
        )}
        <div className="grid grid-cols-2 gap-2">
          <select className="input" value={dType} onChange={(e) => setDType(e.target.value as typeof dType)} aria-label="نوع الخصم">
            <option value="">بدون خصم</option><option value="PERCENTAGE">نسبة %</option><option value="FIXED">مبلغ ثابت</option>
          </select>
          <input className="input" inputMode="decimal" placeholder="قيمة الخصم" value={dVal} disabled={!dType} onChange={(e) => setDVal(e.target.value)} />
        </div>
        <textarea className="input !min-h-[64px] py-2" placeholder="ملاحظات" value={notes} onChange={(e) => setNotes(e.target.value)} />
        <div className="flex justify-between font-semibold"><span>الإجمالي التقديري (قبل الخصم والشحن)</span><span>{money(estimate)}</span></div>
        <button className="btn btn-primary w-full" disabled={m.isPending || lines.length === 0} onClick={() => m.mutate()}>
          {m.isPending ? "جارٍ الحفظ…" : "حفظ الأوردر"}
        </button>
      </div>
    </Modal>
  );
}
