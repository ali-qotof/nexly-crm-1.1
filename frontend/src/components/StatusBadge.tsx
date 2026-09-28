import { useStatuses } from "../hooks/useStatuses";

export function StatusBadge({ code, fallback }: { code?: string | null; fallback?: string | null }) {
  const { byCode } = useStatuses();
  if (!code) return <span className="text-xs text-gray-400">لم يُتواصل</span>;
  const s = byCode.get(code);
  const color = s?.color_hex ?? "#6b7280";
  return (
    <span className="inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold"
      style={{ color, backgroundColor: `${color}1a`, border: `1px solid ${color}55` }}>
      {s?.label_ar ?? fallback ?? code}
    </span>
  );
}
