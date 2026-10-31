import type { ReactNode } from "react";

type ConfirmDialogProps = { open: boolean; title: string; children: ReactNode; confirmLabel?: string; onConfirm: () => void; onCancel: () => void };

export function ConfirmDialog({ open, title, children, confirmLabel = "Confirm", onConfirm, onCancel }: ConfirmDialogProps) {
  if (!open) return null;
  return <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/40 p-4" role="presentation">
    <section role="dialog" aria-modal="true" aria-labelledby="confirm-title" className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
      <h2 id="confirm-title" className="text-lg font-semibold">{title}</h2><div className="mt-3 text-sm text-slate-600">{children}</div>
      <div className="mt-6 flex justify-end gap-2"><button className="rounded-lg px-4 py-2 text-sm text-slate-600" onClick={onCancel}>Cancel</button><button className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white" onClick={onConfirm}>{confirmLabel}</button></div>
    </section>
  </div>;
}
