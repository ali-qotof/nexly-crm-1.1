const nf = new Intl.NumberFormat("ar-EG", { maximumFractionDigits: 2 });
export const money = (n: number | null | undefined) => (n == null ? "—" : `${nf.format(n)} ج.م`);
export const num = (n: number) => nf.format(n);
export const dateTime = (iso: string | null | undefined) =>
  iso ? new Intl.DateTimeFormat("ar-EG", { dateStyle: "medium", timeStyle: "short" }).format(new Date(iso)) : "—";
export const waLink = (phone: string) => {
  const d = phone.replace(/\D/g, "");
  return `https://wa.me/${d.startsWith("0") ? "20" + d.slice(1) : d}`;
};
