import { useState, type FormEvent } from "react";
import { FormField } from "../../components/FormField";

export type PaymentDraft = { amount: string; paid_on: string; method_id: number; note: string };
type PaymentMethod = { id: number; name: string };

export function PaymentDialog({ open, amountDue, methods, onCancel, onSubmit, busy }: { open: boolean; amountDue: string; methods: PaymentMethod[]; onCancel: () => void; onSubmit: (payment: PaymentDraft) => Promise<void>; busy?: boolean }) {
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); const form = new FormData(event.currentTarget);
    try { await onSubmit({ amount: String(form.get("amount")), paid_on: String(form.get("paid_on")), method_id: Number(form.get("method_id")), note: String(form.get("note") ?? "") }); onCancel(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Payment could not be recorded"); }
  }
  if (!open) return null;
  return <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/40 p-4" role="presentation">
    <section role="dialog" aria-modal="true" aria-labelledby="payment-title" className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
      <div className="flex items-start justify-between"><div><h2 id="payment-title" className="text-lg font-semibold">Record payment</h2><p className="mt-1 text-sm text-slate-500">Amount due: <strong className="text-slate-700">{amountDue}</strong></p></div><button type="button" onClick={onCancel} aria-label="Close payment form" className="rounded px-2 text-slate-500 hover:bg-slate-100">×</button></div>
      <form onSubmit={submit} className="mt-5 space-y-4">
        <FormField label="Amount" name="amount" type="text" inputMode="decimal" pattern="[0-9]+(\.[0-9]{1,2})?" placeholder="0.00" required />
        <FormField label="Payment date" name="paid_on" type="date" defaultValue={new Date().toISOString().slice(0, 10)} required />
        <label className="block text-sm font-medium text-slate-700">Payment method<select required name="method_id" className="mt-1.5 block w-full rounded-lg border border-slate-300 px-3 py-2.5 font-normal">{methods.map((method) => <option key={method.id} value={method.id}>{method.name.replaceAll("_", " ")}</option>)}</select></label>
        <FormField label="Note" name="note" maxLength={500} placeholder="Optional reference" />
        {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
        <div className="flex justify-end gap-2"><button type="button" onClick={onCancel} className="rounded-lg px-4 py-2.5 text-sm text-slate-600">Cancel</button><button type="submit" disabled={busy || methods.length === 0} className="rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{busy ? "Recording…" : "Record payment"}</button></div>
      </form>
    </section>
  </div>;
}
