import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { followupsApi } from "../api/endpoints";
import { Empty, ErrorState, Loading } from "../components/States";
import { useToast } from "../components/Toast";
import { dateTime } from "../utils/format";

const TABS = [["overdue", "متأخرة"], ["due_today", "اليوم"], ["upcoming", "قادمة"]] as const;

export default function FollowupsPage() {
  const [bucket, setBucket] = useState<string>("due_today"); const toast = useToast(); const qc = useQueryClient();
  const q = useQuery({ queryKey: ["followups", bucket], queryFn: () => followupsApi.list(bucket) });
  const done = useMutation({ mutationFn: followupsApi.done, onSuccess: () => { toast("success", "تم إكمال المتابعة"); void qc.invalidateQueries({ queryKey: ["followups"] }); }, onError: (e: Error) => toast("error", e.message) });
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2">{TABS.map(([v, l]) => <button key={v} className={`btn ${bucket === v ? "btn-primary" : "btn-ghost"}`} onClick={() => setBucket(v)}>{l}</button>)}</div>
      {q.isLoading ? <Loading /> : q.isError ? <ErrorState error={q.error} onRetry={() => void q.refetch()} /> : q.data!.length === 0 ? <Empty text="لا توجد متابعات" /> : (
        <ul className="space-y-2">{q.data!.map((f) => (
          <li key={f.id} className="card flex items-center justify-between gap-2">
            <div><Link className="font-semibold" to={`/customers/${f.customer_id}`}>فتح العميل</Link><div className="text-sm text-gray-500">{dateTime(f.due_at)}</div>{f.note && <div className="text-sm">{f.note}</div>}</div>
            <button className="btn btn-primary" disabled={done.isPending} onClick={() => done.mutate(f.id)}>تم</button>
          </li>))}
        </ul>)}
    </div>
  );
}
