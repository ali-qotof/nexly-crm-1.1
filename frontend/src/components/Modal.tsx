import type { ReactNode } from "react";

/** موبايل: Bottom Sheet. ديسكتوب: نافذة مركزية. لا Modal داخل Modal (القاعدة 47). */
export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center bg-black/40" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-label={title} onClick={(e) => e.stopPropagation()}
        className="w-full md:max-w-lg max-h-[92vh] overflow-y-auto bg-white rounded-t-3xl md:rounded-3xl p-5 pb-[max(1.25rem,env(safe-area-inset-bottom))]">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">{title}</h2>
          <button className="btn btn-ghost !min-h-[40px] !px-3" onClick={onClose} aria-label="إغلاق">✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}
