import { ApiError } from "../api/client";

export const Loading = ({ text = "جارٍ التحميل…" }: { text?: string }) => (
  <div className="py-10 text-center text-gray-500" role="status">{text}</div>
);
export const Empty = ({ text = "لا توجد بيانات" }: { text?: string }) => (
  <div className="py-10 text-center text-gray-500">{text}</div>
);
export function ErrorState({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const msg = error instanceof ApiError ? error.message : "حدث خطأ غير متوقع";
  return (
    <div className="py-10 text-center">
      <p className="text-red-600 mb-3">{msg}</p>
      <button className="btn btn-ghost" onClick={onRetry}>إعادة المحاولة</button>
    </div>
  );
}
