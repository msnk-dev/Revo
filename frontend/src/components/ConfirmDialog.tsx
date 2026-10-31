import { useEffect, useRef, type ReactNode } from "react";

type ConfirmDialogProps = { open: boolean; title: string; children: ReactNode; confirmLabel?: string; onConfirm: () => void; onCancel: () => void };

export function ConfirmDialog({ open, title, children, confirmLabel = "Confirm", onConfirm, onCancel }: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    cancelRef.current?.focus();
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") { event.preventDefault(); onCancel(); return; }
      if (event.key !== "Tab" || !dialogRef.current) return;
      const controls = [...dialogRef.current.querySelectorAll<HTMLElement>('button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])')];
      if (!controls.length) { event.preventDefault(); return; }
      const first = controls[0]; const last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => { document.removeEventListener("keydown", onKeyDown); previous?.focus(); };
  }, [open, onCancel]);
  if (!open) return null;
  return <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/40 p-4" role="presentation">
    <section ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby="confirm-title" className="w-full max-w-md border border-slate-400 bg-white p-6 shadow-xl">
      <h2 id="confirm-title" className="text-xl font-semibold text-slate-900">{title}</h2><div className="mt-3 text-base leading-6 text-slate-700">{children}</div>
      <div className="mt-6 flex justify-end gap-2"><button ref={cancelRef} className="min-h-11 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100" onClick={onCancel}>Cancel</button><button className="min-h-11 rounded-sm bg-indigo-700 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-800" onClick={onConfirm}>{confirmLabel}</button></div>
    </section>
  </div>;
}
