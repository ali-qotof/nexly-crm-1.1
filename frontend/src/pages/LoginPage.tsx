import { useState, type FormEvent } from "react";
import { useAuth } from "../features/auth/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const [u, setU] = useState(""); const [p, setP] = useState("");
  const [err, setErr] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try { await login(u.trim(), p); } catch (x) { setErr(x instanceof Error ? x.message : "تعذر تسجيل الدخول"); } finally { setBusy(false); }
  };
  return (
    <div className="min-h-full flex items-center justify-center p-6">
      <form onSubmit={submit} className="card w-full max-w-sm space-y-4">
        <h1 className="text-2xl font-bold text-brand-700 text-center">Nexly CRM</h1>
        <input className="input" placeholder="اسم المستخدم" autoComplete="username" value={u} onChange={(e) => setU(e.target.value)} />
        <input className="input" type="password" placeholder="كلمة المرور" autoComplete="current-password" value={p} onChange={(e) => setP(e.target.value)} />
        {err && <p className="text-red-600 text-sm" role="alert">{err}</p>}
        <button className="btn btn-primary w-full" disabled={busy || !u || !p}>{busy ? "جارٍ الدخول…" : "دخول"}</button>
      </form>
    </div>
  );
}
