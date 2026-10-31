import type { ReactNode } from "react";

export function Screen({ eyebrow, title, description, actions, children }: { eyebrow?: string; title: string; description?: string; actions?: ReactNode; children: ReactNode }) {
  return <section className="mx-auto max-w-7xl space-y-8">
    <header className="flex flex-col gap-5 pb-2 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-2xl"><span className="sr-only">{eyebrow}</span><h1 className="revo-page-heading text-3xl font-semibold leading-tight text-slate-900 sm:text-4xl">{title}</h1>{description && <p className="mt-2 max-w-xl text-base leading-6 text-slate-600">{description}</p>}</div>
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
  const tones = { indigo: "text-indigo-700", emerald: "text-emerald-700", amber: "text-amber-700", rose: "text-rose-700" };
  return <article className="border-b border-slate-200 py-4"><p className="text-sm font-medium text-slate-600">{label}</p><div className={`mt-1 text-2xl font-semibold tabular-nums tracking-tight ${tones[accent]}`}>{value}</div>{note && <p className="mt-1 text-sm text-slate-500">{note}</p>}</article>;
}

export const primaryButton = "inline-flex min-h-11 items-center justify-center rounded-sm bg-indigo-700 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-800 disabled:cursor-not-allowed disabled:opacity-50";
export const secondaryButton = "inline-flex min-h-11 items-center justify-center rounded-sm border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50";
