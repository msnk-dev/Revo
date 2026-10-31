import type { ReactNode } from "react";

export function Screen({ eyebrow, title, description, actions, children }: { eyebrow?: string; title: string; description?: string; actions?: ReactNode; children: ReactNode }) {
  return <section className="mx-auto max-w-7xl space-y-6">
    <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>{eyebrow && <p className="text-xs font-semibold uppercase tracking-[0.16em] text-indigo-600">{eyebrow}</p>}<h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>{description && <p className="mt-1.5 text-sm text-slate-500">{description}</p>}</div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
    {children}
  </section>;
}

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500" role="status">{label}</div>;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <div className="rounded-xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800" role="alert"><p>{message}</p>{onRetry && <button onClick={onRetry} className="mt-3 font-semibold underline">Try again</button>}</div>;
}

export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center"><h2 className="font-semibold text-slate-800">{title}</h2><p className="mx-auto mt-2 max-w-md text-sm text-slate-500">{description}</p>{action && <div className="mt-5">{action}</div>}</div>;
}

export function MetricCard({ label, value, note, accent = "indigo" }: { label: string; value: ReactNode; note?: string; accent?: "indigo" | "emerald" | "amber" | "rose" }) {
  const tones = { indigo: "bg-indigo-50 text-indigo-700", emerald: "bg-emerald-50 text-emerald-700", amber: "bg-amber-50 text-amber-700", rose: "bg-rose-50 text-rose-700" };
  return <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-100"><div className="flex items-center justify-between"><p className="text-sm font-medium text-slate-500">{label}</p><span className={`h-2.5 w-2.5 rounded-full ${tones[accent].split(" ")[0]}`} /></div><div className="mt-3 text-2xl font-semibold tracking-tight text-slate-900">{value}</div>{note && <p className="mt-2 text-xs text-slate-500">{note}</p>}</article>;
}

export const primaryButton = "inline-flex items-center justify-center rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50";
export const secondaryButton = "inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50";
