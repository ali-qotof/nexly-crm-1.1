import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "./client";

const json = (status: number, body: unknown) => new Response(JSON.stringify(body), { status });

afterEach(() => vi.restoreAllMocks());

describe("api client", () => {
  it("turns a hanging request into a timeout ApiError instead of waiting forever", async () => {
    vi.stubGlobal("fetch", (_u: string, init: RequestInit) => new Promise((_res, rej) => {
      init.signal?.addEventListener("abort", () => rej(new DOMException("aborted", "AbortError")));
    }));
    await expect(api("/x", { timeoutMs: 30 })).rejects.toMatchObject({ status: 0 });
  });

  it("maps network failure to status 0", async () => {
    vi.stubGlobal("fetch", () => Promise.reject(new TypeError("fail")));
    const err = await api("/x").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(0);
  });

  it("uses backend detail message on errors and generic message otherwise", async () => {
    vi.stubGlobal("fetch", () => Promise.resolve(json(400, { detail: "رسالة من الخادم" })));
    await expect(api("/x")).rejects.toMatchObject({ status: 400, message: "رسالة من الخادم" });
    vi.stubGlobal("fetch", () => Promise.resolve(json(403, {})));
    await expect(api("/x")).rejects.toMatchObject({ status: 403, message: "صلاحيات غير كافية" });
  });

  it("refreshes the session once on 401 and retries the original request", async () => {
    const calls: string[] = [];
    vi.stubGlobal("fetch", (url: string) => {
      calls.push(url);
      if (url.endsWith("/auth/refresh")) return Promise.resolve(json(200, { user: {} }));
      return Promise.resolve(calls.filter((c) => c.endsWith("/data")).length === 1 ? json(401, {}) : json(200, { ok: true }));
    });
    await expect(api("/data")).resolves.toEqual({ ok: true });
    expect(calls.filter((c) => c.endsWith("/auth/refresh")).length).toBe(1);
  });

  it("does not loop on refresh when refresh itself fails", async () => {
    vi.stubGlobal("fetch", () => Promise.resolve(json(401, { detail: "x" })));
    await expect(api("/data")).rejects.toMatchObject({ status: 401 });
  });
});
