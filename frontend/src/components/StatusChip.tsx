const tones: Record<string, string> = {
  active: "bg-emerald-50 text-emerald-700", paid: "bg-emerald-50 text-emerald-700",
  confirmed: "bg-blue-50 text-blue-700", quotation: "bg-amber-50 text-amber-700",
  overdue: "bg-rose-50 text-rose-700", closed: "bg-slate-100 text-slate-600",
};

export function StatusChip({ status }: { status: string }) {
  const label = status.replaceAll("_", " ");
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium capitalize ${tones[status] ?? "bg-slate-100 text-slate-600"}`}>{label}</span>;
}
