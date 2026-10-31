const tones: Record<string, string> = {
  active: "bg-emerald-100 text-emerald-800", paid: "bg-emerald-100 text-emerald-800",
  confirmed: "bg-sky-100 text-sky-800", quotation: "bg-amber-100 text-amber-900", draft: "bg-slate-100 text-slate-700",
  overdue: "bg-rose-100 text-rose-800", failed: "bg-rose-100 text-rose-800", cancelled: "bg-slate-200 text-slate-700", closed: "bg-slate-200 text-slate-700",
};

export function StatusChip({ status }: { status: string }) {
  const label = status.replaceAll("_", " ");
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${tones[status] ?? "bg-slate-100 text-slate-700"}`}><span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />{label}</span>;
}
