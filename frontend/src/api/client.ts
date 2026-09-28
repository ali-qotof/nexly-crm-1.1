/**
 * عميل API مركزي (القاعدة 45): timeout + إلغاء + أخطاء مهيكلة + محاولة تجديد جلسة واحدة عند 401.
 * لا يوجد أي طلب بلا timeout، فلا يمكن أن يعلق التطبيق على Splash إلى الأبد (القاعدة 6/7).
 */
const BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";
const DEFAULT_TIMEOUT_MS = 10_000;

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export const isNetworkError = (e: unknown): boolean => e instanceof ApiError && e.status === 0;

let onUnauthorized: (() => void) | null = null;
export const setUnauthorizedHandler = (fn: () => void) => { onUnauthorized = fn; };

const MESSAGES: Record<number, string> = {
  403: "صلاحيات غير كافية", 404: "غير موجود", 409: "تعارض في البيانات", 422: "بيانات غير صالحة",
  429: "محاولات كثيرة، حاول لاحقًا", 500: "خطأ داخلي في الخادم",
};

async function raw(path: string, init: RequestInit & { timeoutMs?: number; signal?: AbortSignal }): Promise<Response> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), init.timeoutMs ?? DEFAULT_TIMEOUT_MS);
  init.signal?.addEventListener("abort", () => ctrl.abort());
  try {
    return await fetch(BASE + path, { credentials: "include", ...init, signal: ctrl.signal });
  } catch {
    throw new ApiError(0, "تعذر الاتصال بالخادم");
  } finally {
    clearTimeout(timer);
  }
}

async function parse<T>(res: Response): Promise<T> {
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = typeof data?.detail === "string" ? data.detail : undefined;
    throw new ApiError(res.status, detail ?? MESSAGES[res.status] ?? "حدث خطأ غير متوقع");
  }
  return data as T;
}

export async function api<T>(
  path: string,
  opts: { method?: string; body?: unknown; form?: FormData; timeoutMs?: number; signal?: AbortSignal; noRefresh?: boolean } = {},
): Promise<T> {
  const init: RequestInit & { timeoutMs?: number; signal?: AbortSignal } = {
    method: opts.method ?? "GET", timeoutMs: opts.timeoutMs, signal: opts.signal,
  };
  if (opts.form) init.body = opts.form;
  else if (opts.body !== undefined) { init.body = JSON.stringify(opts.body); init.headers = { "Content-Type": "application/json" }; }

  let res = await raw(path, init);
  if (res.status === 401 && !opts.noRefresh && !path.startsWith("/auth/")) {
    const refreshed = await raw("/auth/refresh", { method: "POST" });
    if (refreshed.ok) res = await raw(path, init);
    else { onUnauthorized?.(); }
  }
  return parse<T>(res);
}
