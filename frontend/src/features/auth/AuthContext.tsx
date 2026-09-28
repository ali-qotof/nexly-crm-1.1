import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { authApi } from "../../api/endpoints";
import { ApiError, setUnauthorizedHandler } from "../../api/client";
import type { User } from "../../types";

/**
 * Boot Sequence (القاعدة 7): تحقق من الجلسة → (تجديد إن لزم) → جاهز.
 * كل خطوة لها timeout داخل عميل API، وأي فشل ينتقل لحالة "error" مع إعادة محاولة —
 * لا Splash بلا نهاية، ولا setTimeout لإصلاح منطق.
 */
type BootState = "booting" | "ready" | "unauthenticated" | "error";

interface AuthValue {
  state: BootState; user: User | null; error: string | null;
  login: (u: string, p: string) => Promise<void>; logout: () => Promise<void>; retry: () => void;
}
const Ctx = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<BootState>("booting");
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const ctrl = new AbortController();
    setState("booting"); setError(null);
    (async () => {
      try {
        try { setUser(await authApi.me(ctrl.signal)); setState("ready"); return; }
        catch (e) { if (!(e instanceof ApiError) || e.status !== 401) throw e; }
        const r = await authApi.refresh(ctrl.signal);
        setUser(r.user); setState("ready");
      } catch (e) {
        if (ctrl.signal.aborted) return;
        if (e instanceof ApiError && e.status === 401) { setUser(null); setState("unauthenticated"); }
        else { setError(e instanceof ApiError ? e.message : "تعذر الاتصال بالخادم"); setState("error"); }
      }
    })();
    return () => ctrl.abort();
  }, [attempt]);

  useEffect(() => setUnauthorizedHandler(() => { setUser(null); setState("unauthenticated"); }), []);

  const login = useCallback(async (u: string, p: string) => {
    const r = await authApi.login(u, p); setUser(r.user); setState("ready");
  }, []);
  const logout = useCallback(async () => {
    try { await authApi.logout(); } finally { setUser(null); setState("unauthenticated"); }
  }, []);
  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  return <Ctx.Provider value={{ state, user, error, login, logout, retry }}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthValue {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth must be used inside AuthProvider");
  return v;
}
