import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

type Kind = "success" | "warning" | "error" | "info";
interface T { id: number; kind: Kind; text: string; }
const Ctx = createContext<(kind: Kind, text: string) => void>(() => {});
const COLORS: Record<Kind, string> = { success: "bg-green-600", warning: "bg-amber-500", error: "bg-red-600", info: "bg-sky-600" };

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<T[]>([]);
  const push = useCallback((kind: Kind, text: string) => {
    const id = Date.now() + Math.random();
    setItems((l) => [...l, { id, kind, text }]);
    window.setTimeout(() => setItems((l) => l.filter((x) => x.id !== id)), 4000);
  }, []);
  return (
    <Ctx.Provider value={push}>
      {children}
      <div className="fixed top-3 inset-x-3 z-[100] flex flex-col gap-2 pointer-events-none" role="status" aria-live="polite">
        {items.map((t) => <div key={t.id} className={`${COLORS[t.kind]} text-white rounded-xl px-4 py-3 shadow-lg`}>{t.text}</div>)}
      </div>
    </Ctx.Provider>
  );
}
export const useToast = () => useContext(Ctx);
