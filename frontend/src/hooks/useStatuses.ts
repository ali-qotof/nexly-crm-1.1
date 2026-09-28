import { useQuery } from "@tanstack/react-query";
import { settingsApi } from "../api/endpoints";

/** مصدر الألوان الموحّد لحالات التواصل (القاعدة 11) — تُقرأ من الـ Backend لا من ثوابت. */
export function useStatuses() {
  const q = useQuery({ queryKey: ["statuses"], queryFn: settingsApi.statuses, staleTime: 5 * 60_000 });
  const list = (q.data ?? []).filter((s) => s.is_active);
  const byCode = new Map(list.map((s) => [s.code, s]));
  return { list, byCode, isLoading: q.isLoading };
}
