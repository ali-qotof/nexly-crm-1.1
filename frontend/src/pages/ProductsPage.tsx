import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { productsApi } from "../api/endpoints";
import { useDebounce } from "../hooks/useDebounce";
import { Empty, ErrorState, Loading } from "../components/States";
import { money } from "../utils/format";

export default function ProductsPage() {
  const [q, setQ] = useState(""); const [tab, setTab] = useState<"products" | "offers">("products"); const dq = useDebounce(q);
  const pq = useQuery({ queryKey: ["products", dq], queryFn: () => productsApi.list(dq) });
  const bq = useQuery({ queryKey: ["bundles"], queryFn: productsApi.bundles });
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2"><button className={`btn ${tab === "products" ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab("products")}>المنتجات</button><button className={`btn ${tab === "offers" ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab("offers")}>العروض</button></div>
      {tab === "products" ? (<>
        <input className="input" placeholder="بحث عن منتج" value={q} onChange={(e) => setQ(e.target.value)} />
        {pq.isLoading ? <Loading /> : pq.isError ? <ErrorState error={pq.error} onRetry={() => void pq.refetch()} /> : pq.data!.length === 0 ? <Empty text="لا توجد منتجات" /> :
          pq.data!.map((p) => (<div key={p.id} className="card"><div className="font-bold">{p.name_ar}</div>
            <div className="flex flex-wrap gap-2 mt-2">{p.variants.filter((v) => v.is_active).map((v) => <span key={v.id} className="rounded-lg bg-gray-100 px-3 py-1 text-sm">{v.unit_label} · {money(v.price)}</span>)}</div></div>))}
      </>) : bq.isLoading ? <Loading /> : bq.isError ? <ErrorState error={bq.error} onRetry={() => void bq.refetch()} /> : bq.data!.length === 0 ? <Empty text="لا توجد عروض" /> :
        bq.data!.map((b) => (<div key={b.id} className="card"><div className="flex justify-between font-bold"><span>{b.name}</span><span className="text-brand-700">{money(b.bundle_price)}</span></div>
          {b.regular_total != null && <div className="text-xs text-gray-500">السعر العادي {money(b.regular_total)}</div>}
          <ul className="text-sm text-gray-700 mt-1">{b.items.map((i) => <li key={i.product_variant_id}>{i.product_name} {i.variant_label} ×{i.quantity}</li>)}</ul></div>))}
    </div>
  );
}
