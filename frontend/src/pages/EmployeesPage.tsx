import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { employeesApi } from "../api/endpoints";
import { Empty, ErrorState, Loading } from "../components/States";
import { Modal } from "../components/Modal";
import { useToast } from "../components/Toast";
import { num } from "../utils/format";

export default function EmployeesPage() {
  const toast = useToast(); const qc = useQueryClient(); const nav = useNavigate();
  const [adding, setAdding] = useState(false); const [delId, setDelId] = useState<string | null>(null);
  const [f, setF] = useState({ full_name: "", username: "", password: "" }); const [pw, setPw] = useState("");
  const q = useQuery({ queryKey: ["employees"], queryFn: employeesApi.list });
  const refresh = () => void qc.invalidateQueries({ queryKey: ["employees"] });
  const create = useMutation({ mutationFn: () => employeesApi.create(f),
    onSuccess: (e) => { toast("success", "تم إنشاء الموظفة"); refresh(); setAdding(false); setF({ full_name: "", username: "", password: "" }); nav(`/assignment?employee=${e.id}`); },
    onError: (e: Error) => toast("error", e.message) });
  const toggle = useMutation({ mutationFn: (v: { id: string; on: boolean }) => employeesApi.setActive(v.id, v.on), onSuccess: refresh, onError: (e: Error) => toast("error", e.message) });
  const del = useMutation({ mutationFn: () => employeesApi.remove(delId!, pw),
    onSuccess: () => { toast("success", "تم حذف الموظفة وتحرير عملائها"); setDelId(null); setPw(""); refresh(); void qc.invalidateQueries(); },
    onError: (e: Error) => toast("error", e.message) });
  const submit = (e: FormEvent) => { e.preventDefault(); create.mutate(); };
  const rows = (q.data ?? []).filter((e) => !e.deleted_at);
  return (
    <div className="space-y-3">
      <button className="btn btn-primary w-full" onClick={() => setAdding(true)}>+ إضافة موظفة</button>
      {q.isLoading ? <Loading /> : q.isError ? <ErrorState error={q.error} onRetry={() => void q.refetch()} /> : rows.length === 0 ? <Empty text="لا توجد موظفات" /> :
        rows.map((e) => (
          <div key={e.id} className="card flex items-center justify-between gap-2">
            <div><div className="font-bold">{e.full_name} {!e.is_active && <span className="text-xs text-red-600">(معطّلة)</span>}</div>
              <div className="text-sm text-gray-500">{e.username} · {num(e.assigned_customers_count)} عميل</div></div>
            <div className="flex gap-2">
              <button className="btn btn-ghost !min-h-[40px]" onClick={() => toggle.mutate({ id: e.id, on: !e.is_active })}>{e.is_active ? "تعطيل" : "تفعيل"}</button>
              <button className="btn btn-danger !min-h-[40px]" onClick={() => setDelId(e.id)}>حذف</button>
            </div>
          </div>))}
      {adding && <Modal title="إضافة موظفة" onClose={() => setAdding(false)}>
        <form onSubmit={submit} className="space-y-3">
          <input className="input" placeholder="الاسم" value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} />
          <input className="input" placeholder="اسم المستخدم" autoComplete="off" value={f.username} onChange={(e) => setF({ ...f, username: e.target.value })} />
          <input className="input" type="password" placeholder="كلمة المرور (8 أحرف على الأقل)" autoComplete="new-password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} />
          <button className="btn btn-primary w-full" disabled={create.isPending || !f.full_name || f.username.length < 3 || f.password.length < 8}>{create.isPending ? "جارٍ الحفظ…" : "حفظ الموظفة والمتابعة ←"}</button>
        </form></Modal>}
      {delId && <Modal title="تأكيد حذف الموظفة" onClose={() => { setDelId(null); setPw(""); }}>
        <p className="text-sm text-gray-600 mb-3">سيتم تعطيل الحساب وتحرير عملائها. لن تُحذف الأوردرات أو التفاعلات. أدخل كلمة مرورك للتأكيد.</p>
        <input className="input mb-3" type="password" placeholder="كلمة مرور المدير" autoComplete="current-password" value={pw} onChange={(e) => setPw(e.target.value)} />
        <button className="btn btn-danger w-full" disabled={del.isPending || !pw} onClick={() => del.mutate()}>{del.isPending ? "جارٍ الحذف…" : "تأكيد الحذف"}</button>
      </Modal>}
    </div>
  );
}
