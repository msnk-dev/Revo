export function FeaturePlaceholder({ title, description = "This area is scaffolded for the next Revo milestone." }: { title: string; description?: string }) {
  return <section className="mx-auto max-w-6xl">
    <div className="mb-8"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-indigo-600">Revo workspace</p><h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">{title}</h1><p className="mt-2 text-sm text-slate-500">{description}</p></div>
    <div className="rounded-xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center text-sm text-slate-500">Your {title.toLowerCase()} workspace will appear here.</div>
  </section>;
}
