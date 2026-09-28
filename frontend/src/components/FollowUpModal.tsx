import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { followupsApi } from "../api/endpoints";
import { useToast } from "./Toast";
import { Modal } from "./Modal";

const localNow = () => { const d = new Date(Date.now() + 3600_000); d.setMinutes(0, 0, 0); return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16); };

export function FollowUpModal({ customerId, onClose }: { customerId: string; onClose: () => void }) {
  const toast = useToast(); const qc = useQueryClient();
  const [due, setDue] = useState(localNow()); const [note, setNote] = useState("");
  const m = useMutation({
    mutationFn: () => followupsApi.create({ customer_id: customerId, due_at: new Date(due).toISOString(), note: note || undefined }),
    onSuccess: () => { toast("success", "تم حفظ المتابعة"); qc.invalidateQueries({ queryKey: ["followups"] }); onClose(); },
    onError: (e: Error) => toast("error", e.message),
  });
  return (
    <Modal title="متابعة جديدة" onClose={onClose}>
      <div className="space-y-3">
        <input type="datetime-local" className="input" value={due} onChange={(e) => setDue(e.target.value)} />
        <textarea className="input !min-h-[80px] py-2" placeholder="ملاحظة" value={note} onChange={(e) => setNote(e.target.value)} />
        <button className="btn btn-primary w-full" disabled={m.isPending || !due} onClick={() => m.mutate()}>{m.isPending ? "جارٍ الحفظ…" : "حفظ"}</button>
      </div>
    </Modal>
  );
}
