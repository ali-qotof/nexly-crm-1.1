import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { assignmentsApi, customersApi, employeesApi, type ImportPreview } from "../api/endpoints";
import { useDebounce } from "../hooks/useDebounce";
import { Empty, ErrorState, Loading } from "../components/States";
import { useToast } from "../components/Toast";
import { num } from "../utils/format";

/** توزيع العملاء (القاعدة 13-15): اختيار موظفة ← عملاء غير مخصصين/الكل ← إسناد أو سحب، أو استيراد Excel بمعاينة. */
export default function AssignmentPage() {
  const toast = useToast(); const qc = useQueryClient(); const [sp] = useSearchParams();
  const [employee, setEmployee] = useState(sp.get("employee") ?? ""); const [unassignedOnly, setUnassignedOnly] = useState(true);
  const [q, setQ] = useState(""); const dq = useDebounce(q); const [page, setPage] = useState(1);
  const [sel, setSel] = useState<Set<string>>(new Set()); const [preview, setPreview] = useState<ImportPreview | null>(null);
  const emps = useQuery({ queryKey: ["employees"], queryFn: employeesApi.list });
  const list = useQuery({ queryKey: ["assign-list", dq, unassignedOnly, page], queryFn: () => customersApi.all({ q: dq, unassigned_only: unassignedOnly, page, page_size: 25 }), placeholderData: (p) => p });
  useEffect(() => { setSel(new Set()); }, [dq, unassignedOnly, page]);
  const done = (msg: string) => { toast("success", msg); setSel(new Set()); setPreview(null); void qc.invalidateQueries(); };
  const assign = useMutation({ mutationFn: () => assignmentsApi.assign([...sel], employee), onSuccess: (r) => done(`تم إسناد ${num(r.assigned)} عميل (تخطّي ${num(r.skipped_already_assigned)} مخصص مسبقًا)`), onError: (e: Error) => toast("error", e.message) });
  const unassign = useMutation({ mutationFn: () => assignmentsApi.unassign([...sel]), onSuccess: (r) => done(`تم سحب ${num(r.assigned)} عميل`), onError: (e: Error) => toast("error", e.message) });
  const previewM = useMutation({ mutationFn: (f: File) => assignmentsApi.importPreview(f), onSuccess: setPreview, onError: (e: Error) => toast("error", e.message) });
  const confirm = useMutation({ mutationFn: () => assignmentsApi.importConfirm(preview!.matched.map((m) => m.matched_customer_id), employee), onSuccess: (r) => done(`تم إسناد ${num(r.assigned)} عميل من الملف`), onError: (e: Error) => toast("error", e.message) });
  const items = list.data?.items ?? [];
  const toggle = (id: string) => setSel((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const allOnPage = items.length > 0 && items.every((c) => sel.has(c.id));
  const pages = list.data ? Math.max(1, Math.ceil(list.data.total / list.data.page_size)) : 1;
  return (
    <div className="space-y-3">
      <select className="input" value={employee} onChange={(e) => setEmployee(e.target.value)} aria-label="الموظفة">
        <option value="">— اختر الموظفة —</option>
        {(emps.data ?? []).filter((e) => e.is_active && !e.deleted_at).map((e) => <option key={e.id} value={e.id}>{e.full_name} ({num(e.assigned_customers_count)})</option>)}
      </select>
      <label className="card flex items-center justify-between gap-3">
        <span className="text-sm">استيراد ملف Excel / CSV (Customer ID / Phone)</span>
        <input type="file" accept=".xlsx,.csv" disabled={!employee || previewM.isPending} onChange={(e) => { const f = e.target.files?.[0]; if (f) previewM.mutate(f); e.target.value = ""; }} />
      </label>
      {preview && <div className="card space-y-2">
        <div className="font-bold">معاينة الاستيراد</div>
        <div className="grid grid-cols-2 gap-2 text-sm"><span>إجمالي الصفوف: {num(preview.total_rows)}</span><span className="text-green-700">مطابق: {num(preview.matched_count)}</span>
          <span className="text-red-600">غير موجود: {num(preview.missing_count)}</span><span className="text-amber-600">مكرر: {num(preview.duplicate_count)}</span><span>غير صالح: {num(preview.invalid_count)}</span></div>
        <div className="flex gap-2"><button className="btn btn-primary flex-1" disabled={confirm.isPending || preview.matched_count === 0} onClick={() => confirm.mutate()}>{confirm.isPending ? "جارٍ الإسناد…" : "تأكيد الإسناد"}</button><button className="btn btn-ghost" onClick={() => setPreview(null)}>إلغاء</button></div></div>}
      <div className="grid grid-cols-2 gap-2">
        <button className={`btn ${unassignedOnly ? "btn-primary" : "btn-ghost"}`} onClick={() => { setUnassignedOnly(true); setPage(1); }}>غير المخصصين</button>
        <button className={`btn ${!unassignedOnly ? "btn-primary" : "btn-ghost"}`} onClick={() => { setUnassignedOnly(false); setPage(1); }}>كل العملاء</button>
      </div>
      <input className="input" placeholder="بحث" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
      {list.isLoading ? <Loading /> : list.isError ? <ErrorState error={list.error} onRetry={() => void list.refetch()} /> : items.length === 0 ? <Empty text="لا يوجد عملاء مطابقون للبحث" /> : (<>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={allOnPage} onChange={() => setSel(allOnPage ? new Set() : new Set(items.map((c) => c.id)))} className="h-5 w-5" />تحديد كل الصفحة الحالية</label>
        <ul className="space-y-2">{items.map((c) => (
          <li key={c.id}><label className="card flex items-center gap-3"><input type="checkbox" className="h-5 w-5" checked={sel.has(c.id)} onChange={() => toggle(c.id)} />
            <div className="flex-1"><div className="font-semibold">{c.name}</div><div className="text-xs text-gray-500">{c.phone} · {c.assigned_employee_name ?? "غير مخصص"}</div></div></label></li>))}</ul>
        {pages > 1 && <div className="flex items-center justify-between"><button className="btn btn-ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>السابق</button><span className="text-sm">{page} / {pages}</span><button className="btn btn-ghost" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>التالي</button></div>}
      </>)}
      <div className="sticky bottom-20 md:bottom-2 grid grid-cols-2 gap-2">
        <button className="btn btn-primary shadow-lg" disabled={!employee || sel.size === 0 || assign.isPending} onClick={() => assign.mutate()}>إسناد ({num(sel.size)})</button>
        <button className="btn btn-danger shadow-lg" disabled={sel.size === 0 || unassign.isPending} onClick={() => window.confirm(`سحب ${sel.size} عميل من موظفاتهم؟`) && unassign.mutate()}>سحب ({num(sel.size)})</button>
      </div>
    </div>
  );
}
