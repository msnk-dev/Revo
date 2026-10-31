import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "../../api/client";
import type { InvoiceLine } from "../../api/models";
import type { Page } from "../../api/types";
import { DataTable, type Column } from "../../components/DataTable";
import { Money } from "../../components/Money";
import { StatusChip } from "../../components/StatusChip";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { EmptyState, ErrorState, LoadingState, Screen, primaryButton, secondaryButton } from "../../components/Screen";
import { PaymentDialog, type PaymentDraft } from "./PaymentDialog";
import { RoleGuard } from "../../app/RoleGuard";

type Customer = { id: number; name: string; email: string };
type PaymentMethod = { id: number; name: string; is_active: boolean };
type InvoiceRecord = { id: number; number: string; customer_id: number; status: "draft" | "confirmed" | "paid" | "cancelled"; invoice_date: string; due_date: string; total: string; amount_due: string };
type InvoiceBreakdown = { invoice_id: number; invoice_number: string; lines: InvoiceLine[]; subtotal: string; discount_total: string; tax_total: string; total: string };
type InvoiceGenerate = { dry_run: boolean; as_of: string; eligible_count?: number; created?: number; skipped_duplicates?: number; failed: { sub_id: number; error: string }[] };
type InvoiceDetailData = { meta: InvoiceRecord; breakdown: InvoiceBreakdown };
const pageSize = 10;
function amountCents(value: string) { const [whole, fraction = ""] = value.split("."); return BigInt(whole) * 100n + BigInt(fraction.padEnd(2, "0").slice(0, 2)); }
function centsString(value: bigint) { return `${value / 100n}.${String(value % 100n).padStart(2, "0")}`; }
function displayStatus(invoice: InvoiceRecord) { return invoice.status === "confirmed" && amountCents(invoice.amount_due) > 0n && invoice.due_date < new Date().toISOString().slice(0, 10) ? "overdue" : invoice.status; }
async function getInvoiceMeta(invoiceId: number): Promise<InvoiceRecord> {
  const pageSize = 100; const first = await apiRequest<Page<InvoiceRecord>>(`/invoices?page=1&page_size=${pageSize}`);
  const found = first.items.find((invoice) => invoice.id === invoiceId); if (found) return found;
  const pageCount = Math.ceil(first.total / pageSize);
  for (let page = 2; page <= pageCount; page += 1) {
    const next = await apiRequest<Page<InvoiceRecord>>(`/invoices?page=${page}&page_size=${pageSize}`);
    const item = next.items.find((invoice) => invoice.id === invoiceId); if (item) return item;
  }
  throw new Error("Invoice not found");
}

function InvoiceList() {
  const [page, setPage] = useState(1); const [status, setStatus] = useState(""); const [confirmGenerate, setConfirmGenerate] = useState(false); const [eligible, setEligible] = useState<number | null>(null); const [notice, setNotice] = useState(""); const queryClient = useQueryClient();
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) }); if (status) params.set("status", status);
  const query = useQuery({ queryKey: ["invoices", page, status], queryFn: () => apiRequest<Page<InvoiceRecord>>(`/invoices?${params}`), refetchInterval: 15_000 });
  const customers = useQuery({ queryKey: ["customers", "lookup"], queryFn: () => apiRequest<Page<Customer>>("/customers?page=1&page_size=100") });
  const preview = useMutation({ mutationFn: () => apiRequest<InvoiceGenerate>("/invoices/generate?dry_run=true", { method: "POST" }), onSuccess: (result) => { setEligible(result.eligible_count ?? 0); setConfirmGenerate(true); }, onError: (reason) => setNotice(reason instanceof Error ? reason.message : "Could not preview invoice generation.") });
  const generate = useMutation({ mutationFn: () => apiRequest<InvoiceGenerate>("/invoices/generate", { method: "POST" }), onSuccess: async (result) => { setConfirmGenerate(false); setNotice(`Generated ${result.created ?? 0} invoice(s); ${result.skipped_duplicates ?? 0} duplicate period(s) were skipped.`); await queryClient.invalidateQueries({ queryKey: ["invoices"] }); await queryClient.invalidateQueries({ queryKey: ["reports"] }); }, onError: (reason) => setNotice(reason instanceof Error ? reason.message : "Invoice generation failed.") });
  const columns = useMemo<Column<InvoiceRecord>[]>(() => [
    { key: "number", header: "Invoice", render: (row) => <Link to={`/invoices/${row.id}`} className="font-semibold text-indigo-700">{row.number}</Link> },
    { key: "customer", header: "Customer", render: (row) => customers.data?.items.find((customer) => customer.id === row.customer_id)?.name ?? `Customer #${row.customer_id}` },
    { key: "date", header: "Invoice date", render: (row) => new Date(`${row.invoice_date}T00:00:00`).toLocaleDateString("en-IN") },
    { key: "due", header: "Due date", render: (row) => new Date(`${row.due_date}T00:00:00`).toLocaleDateString("en-IN") },
    { key: "status", header: "Status", render: (row) => <StatusChip status={displayStatus(row)} /> },
    { key: "total", header: "Total", align: "right", render: (row) => <Money amount={row.total} /> },
    { key: "due_amount", header: "Amount due", align: "right", render: (row) => <Money amount={row.amount_due} /> },
  ], [customers.data]);
  return <Screen eyebrow="Billing" title="Invoices" description="Review invoices, record payments, and follow up on overdue balances." actions={<button disabled={preview.isPending || generate.isPending} onClick={() => { setNotice(""); preview.mutate(); }} className={primaryButton}>{preview.isPending ? "Checking…" : "Generate invoices"}</button>}>
    <div className="flex flex-wrap gap-3 rounded-xl border border-slate-200 bg-white p-4"><select aria-label="Filter invoices by status" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }} className="rounded-lg border border-slate-300 px-3 py-2 text-sm"><option value="">All statuses</option>{["draft", "confirmed", "paid", "cancelled"].map((item) => <option key={item}>{item}</option>)}</select><button onClick={() => { setStatus(""); setPage(1); }} className={secondaryButton}>Clear filter</button></div>
    {notice && <p role="status" className="rounded-lg bg-indigo-50 px-4 py-2 text-sm text-indigo-800">{notice}</p>}
    {query.isLoading || customers.isLoading ? <LoadingState label="Loading invoices…" /> : query.error || customers.error ? <ErrorState message="Could not load invoices or customer details." onRetry={() => { void query.refetch(); void customers.refetch(); }} /> : (query.data?.total ?? 0) === 0 ? <EmptyState title="No invoices yet" description="Generate invoices for subscriptions that are due." /> : <DataTable rows={query.data?.items ?? []} columns={columns} rowKey={(row) => row.id} page={page} pageSize={pageSize} total={query.data?.total ?? 0} onPageChange={setPage} />}
    <ConfirmDialog open={confirmGenerate} title="Generate due invoices?" confirmLabel={generate.isPending ? "Generating…" : "Generate invoices"} onCancel={() => setConfirmGenerate(false)} onConfirm={() => generate.mutate()}>The billing service found {eligible ?? 0} eligible subscription(s). The API rechecks eligibility and skips periods already billed.</ConfirmDialog>
  </Screen>;
}

function InvoiceDetail() {
  const { id = "" } = useParams(); const invoiceId = Number(id); const queryClient = useQueryClient(); const [paymentOpen, setPaymentOpen] = useState(false); const [cancelOpen, setCancelOpen] = useState(false); const [notice, setNotice] = useState("");
  const query = useQuery({ queryKey: ["invoice", id], queryFn: async (): Promise<InvoiceDetailData> => { const [breakdown, meta] = await Promise.all([apiRequest<InvoiceBreakdown>(`/invoices/${id}`), getInvoiceMeta(invoiceId)]); return { breakdown, meta }; }, enabled: Number.isInteger(invoiceId) && invoiceId > 0 });
  const customer = useQuery({ queryKey: ["customer", query.data?.meta.customer_id], queryFn: () => apiRequest<Customer>(`/customers/${query.data?.meta.customer_id}`), enabled: Boolean(query.data?.meta.customer_id) });
  const methods = useQuery({ queryKey: ["catalog", "payment-methods"], queryFn: () => apiRequest<Page<PaymentMethod>>("/payment-methods?page=1&page_size=100") });
  const refresh = async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: ["invoice", id] }), queryClient.invalidateQueries({ queryKey: ["invoices"] }), queryClient.invalidateQueries({ queryKey: ["payments"] }), queryClient.invalidateQueries({ queryKey: ["reports"] })]); };
  const action = useMutation({ mutationFn: (name: string) => apiRequest(`/invoices/${id}/${name}`, { method: "POST" }), onSuccess: async (_data, name) => { setNotice(name === "send" ? "Invoice email sent." : `Invoice ${name}ed.`); await refresh(); } });
  const payment = useMutation({ mutationFn: (draft: PaymentDraft) => apiRequest(`/invoices/${id}/payments`, { method: "POST", body: JSON.stringify(draft) }), onSuccess: async () => { setNotice("Payment recorded."); setPaymentOpen(false); await refresh(); } });
  if (query.isLoading) return <LoadingState label="Loading invoice…" />;
  if (query.error || !query.data) return <ErrorState message={query.error instanceof Error ? query.error.message : "Invoice could not be loaded."} onRetry={() => void query.refetch()} />;
  const { meta, breakdown } = query.data; const status = displayStatus(meta); const paid = centsString(amountCents(meta.total) - amountCents(meta.amount_due)); const methodRows = methods.data?.items.filter((item) => item.is_active) ?? [];
  return <Screen eyebrow="Invoice detail" title={meta.number} description={`${customer.data?.name ?? `Customer #${meta.customer_id}`} · ${meta.invoice_date}`} actions={<Link to="/invoices" className={secondaryButton}>Back to invoices</Link>}>
    {notice && <p role="status" className="rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-800">{notice}</p>}{(action.error || payment.error || methods.error || customer.error) && <ErrorState message={(action.error ?? payment.error ?? methods.error ?? customer.error) instanceof Error ? String((action.error ?? payment.error ?? methods.error ?? customer.error)?.message) : "Invoice action failed"} />}
    <dl className="grid grid-cols-2 gap-x-5 border-y border-slate-300 py-4 sm:grid-cols-4"><div className="py-2"><dt className="text-sm text-slate-600">Status</dt><dd className="mt-2"><StatusChip status={status} /></dd></div><div className="py-2"><dt className="text-sm text-slate-600">Invoice date</dt><dd className="mt-2 font-semibold text-slate-900">{meta.invoice_date}</dd></div><div className="py-2"><dt className="text-sm text-slate-600">Due date</dt><dd className="mt-2 font-semibold text-slate-900">{meta.due_date}</dd></div><div className="py-2"><dt className="text-sm text-slate-600">Amount due</dt><dd className="mt-2 text-xl font-semibold tabular-nums text-slate-900"><Money amount={meta.amount_due} /></dd></div></dl>
    <div className="flex flex-wrap gap-2">{meta.status === "draft" && <button disabled={action.isPending} onClick={() => action.mutate("confirm")} className={primaryButton}>Confirm invoice</button>}{(meta.status === "draft" || (meta.status === "confirmed" && amountCents(paid) === 0n)) && <button disabled={action.isPending} onClick={() => setCancelOpen(true)} className="min-h-11 rounded-sm border border-rose-300 px-4 py-2.5 text-sm font-semibold text-rose-800 hover:bg-rose-50">Cancel invoice</button>}{meta.status === "confirmed" && <><button disabled={action.isPending} onClick={() => action.mutate("send")} className={secondaryButton}>Send by email</button><button onClick={() => setPaymentOpen(true)} className={primaryButton}>Record payment</button></>}<a href={`${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1"}/invoices/${invoiceId}/pdf`} target="_blank" rel="noreferrer" className={secondaryButton}>Download PDF</a></div>
    <section className="border-t-2 border-slate-300 bg-white p-5"><h2 className="text-lg font-semibold">Invoice lines</h2><div className="mt-4 overflow-x-auto"><table className="w-full min-w-[760px] text-left text-base"><thead className="sticky top-0 border-b border-slate-300 bg-slate-100 text-sm text-slate-700"><tr><th className="py-3">Description</th><th className="text-right">Qty</th><th className="text-right">Unit price (INR)</th><th className="text-right">Discount (INR)</th><th className="text-right">Tax</th><th className="text-right">Line total (INR)</th></tr></thead><tbody className="divide-y divide-slate-200">{breakdown.lines.map((line, index) => <tr key={`${line.description}-${index}`}><td className="py-3"><p className="font-medium text-slate-900">{line.description}</p>{line.variant_extra !== "0.00" && <p className="text-sm text-slate-600">Includes variant extra <Money amount={line.variant_extra} /></p>}</td><td className="text-right tabular-nums">{line.quantity}</td><td className="text-right tabular-nums"><Money amount={line.unit_price} /></td><td className="text-right tabular-nums">{line.discount_name ? <span>{line.discount_name} · <Money amount={line.discount_amount} /><span className="block text-sm text-slate-600">{line.discount_reason}</span></span> : "—"}</td><td className="text-right tabular-nums">{line.tax_name ? <span>{line.tax_name} ({line.tax_rate_pct}%)<span className="block text-sm text-slate-600"><Money amount={line.tax_amount} /></span></span> : "—"}</td><td className="text-right font-semibold tabular-nums"><Money amount={line.line_total} /></td></tr>)}</tbody></table></div><div className="ml-auto mt-6 max-w-sm space-y-2 border-t border-slate-300 pt-4 text-base tabular-nums"><div className="flex justify-between"><span className="text-slate-600">Subtotal</span><Money amount={breakdown.subtotal} /></div><div className="flex justify-between"><span className="text-slate-600">Discount</span><Money amount={breakdown.discount_total} /></div><div className="flex justify-between"><span className="text-slate-600">Tax</span><Money amount={breakdown.tax_total} /></div><div className="flex justify-between border-t border-slate-300 pt-2 text-lg font-semibold"><span>Total</span><Money amount={breakdown.total} /></div><div className="flex justify-between text-slate-600"><span>Paid</span><Money amount={paid} /></div><div className="flex justify-between font-semibold"><span>Due</span><Money amount={meta.amount_due} /></div></div></section>
    <ConfirmDialog open={cancelOpen} title="Cancel this invoice?" confirmLabel="Cancel invoice" onCancel={() => setCancelOpen(false)} onConfirm={() => { setCancelOpen(false); action.mutate("cancel"); }}>This invoice will be cancelled and any reserved discount use will be released.</ConfirmDialog>
    <PaymentDialog open={paymentOpen} amountDue={meta.amount_due} methods={methodRows} busy={payment.isPending || methods.isLoading} onCancel={() => setPaymentOpen(false)} onSubmit={(draft) => payment.mutateAsync(draft).then(() => undefined)} />
  </Screen>;
}

export const routes = [
  { path: "invoices", element: <RoleGuard roles={["admin", "staff"]}><InvoiceList /></RoleGuard> },
  { path: "invoices/:id", element: <RoleGuard roles={["admin", "staff"]}><InvoiceDetail /></RoleGuard> },
];
