import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { interactionsApi } from "../api/endpoints";
import { useStatuses } from "../hooks/useStatuses";
import { useToast } from "./Toast";
import { Modal } from "./Modal";

export function InteractionModal({ customerId, channel: initial = "call", onClose }: { customerId: string; channel?: string; onClose: () => void }) {
  const toast = useToast(); const qc = useQueryClient(); const { list } = useStatuses();
  const [channel, setChannel] = useState(initial); const [status, setStatus] = useState(""); const [note, setNote] = useState("");
  const m = useMutation({
    mutationFn: () => interactionsApi.create({ customer_id: customerId, channel, status_code: status || undefined, note: note || undefined }),
    onSuccess: () => { toast("success", "تم تسجيل التفاعل"); qc.invalidateQueries(); onClose(); },
    onError: (e: Error) => toast("error", e.message),
  });
  return (
    <Modal title="تسجيل تفاعل" onClose={onClose}>
      <div className="space-y-3">
        <div className="grid grid-cols-3 gap-2">
          {[["call", "اتصال"], ["whatsapp", "واتساب"], ["note", "ملاحظة"]].map(([v, l]) => (
            <button key={v} className={`btn ${channel === v ? "btn-primary" : "btn-ghost"}`} onClick={() => setChannel(v)}>{l}</button>
          ))}
        </div>
        <select className="input" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="حالة التواصل">
          <option value="">— حالة التواصل —</option>
          {list.map((s) => <option key={s.id} value={s.code}>{s.label_ar}</option>)}
        </select>
        <textarea className="input !min-h-[96px] py-2" placeholder="ملاحظة" value={note} onChange={(e) => setNote(e.target.value)} />
        <button className="btn btn-primary w-full" disabled={m.isPending} onClick={() => m.mutate()}>{m.isPending ? "جارٍ الحفظ…" : "حفظ"}</button>
      </div>
    </Modal>
  );
}
