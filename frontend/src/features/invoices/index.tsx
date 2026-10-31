import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "../../api/client";
import type { Invoice } from "../../api/models";
import type { Page } from "../../api/types";
import { DataTable, type Column } from "../../components/DataTable";
import { Money } from "../../components/Money";
import { StatusChip } from "../../components/StatusChip";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { EmptyState, ErrorState, LoadingState, Screen, primaryButton, secondaryButton } from "../../components/Screen";
import { PaymentDialog, type PaymentDraft } from "./PaymentDialog";
import { RoleGuard } from "../../app/RoleGuard";

const pageSize = 10;
function amountIsPositive(value: string) { const [whole, fraction = ""] = value.split("."); return BigInt(whole) * 100n + BigInt(fraction.padEnd(2, "0").slice(0, 2)) > 0n; }
function todayLocal() { const date = new Date(); return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`; }
function displayStatus(invoice: Invoice) { return invoice.status === "confirmed" && amountIsPositive(invoice.amount_due) && invoice.due_date < todayLocal() ? "overdue" : invoice.status; }

function InvoiceList() {
  const [page, setPage] = useState(1); const [status, setStatus] = useState(""); const [search, setSearch] = useState("");
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) }); if (status) params.set("status", status); if (search.trim()) params.set("q", search.trim());
  const query = useQuery({ queryKey: ["invoices", page, status, search], queryFn: () => apiRequest<Page<Invoice>>(`/invoices?${params}`), refetchInterval: 15_000 });
  const columns = useMemo<Column<Invoice>[]>(() => [
    { key: "number", header: "Invoice", render: (row) => <Link to={`/invoices/${row.id}`} className="font-semibold text-indigo-700">{row.number}</Link> },
    { key: "customer", header: "Customer", render: (row) => row.customer_name },
    { key: "date", header: "Invoice date", render: (row) => new Date(`${row.invoice_date}T00:00:00`).toLocaleDateString("en-IN") },
    { key: "due", header: "Due date", render: (row) => new Date(`${row.due_date}T00:00:00`).toLocaleDateString("en-IN") },
    { key: "status", header: "Status", render: (row) => <StatusChip status={displayStatus(row)} /> },
    { key: "total", header: "Total", render: (row) => <Money amount={row.total} /> },
    { key: "due_amount", header: "Amount due", render: (row) => <Money amount={row.amount_due} /> },
  ], []);
  return <Screen eyebrow="Billing" title="Invoices" description="Review invoices, record payments, and follow up on overdue balances.">
    <div className="flex flex-wrap gap-3 rounded-xl border border-slate-200 bg-white p-4"><input aria-label="Search invoices" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="Search number or customer" className="min-w-64 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" /><select aria-label="Filter invoices by status" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }} className="rounded-lg border border-slate-300 px-3 py-2 text-sm"><option value="">All statuses</option>{["draft", "confirmed", "paid", "cancelled"].map((item) => <option key={item}>{item}</option>)}</select><button onClick={() => { setStatus(""); setSearch(""); setPage(1); }} className={secondaryButton}>Clear filters</button></div>
    {query.isLoading ? <LoadingState label="Loading invoices…" /> : query.error ? <ErrorState message="Could not load invoices. Check the API or enable demo mode." onRetry={() => void query.refetch()} /> : (query.data?.total ?? 0) === 0 ? <EmptyState title="No invoices yet" description="Invoices will appear here after the billing service generates them." /> : <DataTable rows={query.data?.items ?? []} columns={columns} rowKey={(row) => row.id} page={page} pageSize={pageSize} total={query.data?.total ?? 0} onPageChange={setPage} />}
  </Screen>;
}

function InvoiceDetail() {
  const { id = "" } = useParams(); const queryClient = useQueryClient(); const [paymentOpen, setPaymentOpen] = useState(false); const [cancelOpen, setCancelOpen] = useState(false); const [notice, setNotice] = useState("");
  const key = ["invoice", id]; const query = useQuery({ queryKey: key, queryFn: () => apiRequest<Invoice>(`/invoices/${id}`), enabled: Boolean(id) });
  const refresh = async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: ["invoice", id] }), queryClient.invalidateQueries({ queryKey: ["invoices"] }), queryClient.invalidateQueries({ queryKey: ["payments"] }), queryClient.invalidateQueries({ queryKey: ["reports"] })]); };
  const action = useMutation({ mutationFn: ({ name, body }: { name: string; body?: unknown }) => apiRequest<void>(`/invoices/${id}/${name}`, { method: "POST", ...(body ? { body: JSON.stringify(body) } : {}) }), onSuccess: async (_data, vars) => { setNotice(vars.name === "send" ? "Invoice email queued." : `Invoice ${vars.name}ed.`); await refresh(); } });
  const payment = useMutation({ mutationFn: (draft: PaymentDraft) => apiRequest(`/invoices/${id}/payments`, { method: "POST", body: JSON.stringify(draft) }), onSuccess: async () => { setNotice("Payment recorded."); setPaymentOpen(false); await refresh(); } });
  if (query.isLoading) return <LoadingState label="Loading invoice…" />;
  if (query.error || !query.data) return <ErrorState message="Invoice could not be loaded." onRetry={() => void query.refetch()} />;
  const invoice = query.data; const status = displayStatus(invoice); const mockMode = import.meta.env.VITE_USE_MOCKS === "true";
  return <Screen eyebrow="Invoice detail" title={invoice.number} description={`${invoice.customer_name} · ${invoice.invoice_date}`} actions={<Link to="/invoices" className={secondaryButton}>Back to invoices</Link>}>
    {notice && <p role="status" className="rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-800">{notice}</p>}
    {(action.error || payment.error) && <ErrorState message={(action.error ?? payment.error) instanceof Error ? String((action.error ?? payment.error)?.message) : "Invoice action failed"} />}
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><article className="rounded-xl border border-slate-200 bg-white p-5"><p className="text-sm text-slate-500">Status</p><div className="mt-2"><StatusChip status={status} /></div></article><article className="rounded-xl border border-slate-200 bg-white p-5"><p className="text-sm text-slate-500">Invoice date</p><p className="mt-2 font-semibold">{invoice.invoice_date}</p></article><article className="rounded-xl border border-slate-200 bg-white p-5"><p className="text-sm text-slate-500">Due date</p><p className="mt-2 font-semibold">{invoice.due_date}</p></article><article className="rounded-xl border border-slate-200 bg-white p-5"><p className="text-sm text-slate-500">Amount due</p><p className="mt-2 text-xl font-semibold"><Money amount={invoice.amount_due} /></p></article></div>
    <div className="flex flex-wrap gap-2 rounded-xl border border-slate-200 bg-white p-4">
      {invoice.status === "draft" && <button disabled={action.isPending} onClick={() => action.mutate({ name: "confirm" })} className={primaryButton}>Confirm invoice</button>}
      {(invoice.status === "draft" || (invoice.status === "confirmed" && !amountIsPositive(invoice.amount_paid))) && <button disabled={action.isPending} onClick={() => setCancelOpen(true)} className="rounded-lg border border-rose-200 px-4 py-2.5 text-sm font-semibold text-rose-700 hover:bg-rose-50">Cancel invoice</button>}
      {invoice.status === "confirmed" && <><button disabled={action.isPending} onClick={() => action.mutate({ name: "send" })} className={secondaryButton}>Send by email</button><button onClick={() => setPaymentOpen(true)} className={primaryButton}>Record payment</button></>}
      {mockMode ? <button onClick={() => window.print()} className={secondaryButton}>Print / save PDF</button> : <a href={`${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1"}/invoices/${invoice.id}/pdf`} target="_blank" rel="noreferrer" className={secondaryButton}>Download PDF</a>}
    </div>
    <section className="rounded-xl border border-slate-200 bg-white p-5"><h2 className="font-semibold">Invoice lines</h2><div className="mt-4 overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500"><tr><th className="py-3">Description</th><th>Qty</th><th>Unit price</th><th>Discount</th><th>Tax</th><th className="text-right">Line total</th></tr></thead><tbody className="divide-y divide-slate-100">{invoice.lines.map((line, index) => <tr key={`${line.description}-${index}`}><td className="py-3"><p className="font-medium">{line.description}</p>{line.variant_extra !== "0.00" && <p className="text-xs text-slate-500">Includes variant extra <Money amount={line.variant_extra} /></p>}</td><td>{line.quantity}</td><td><Money amount={line.unit_price} /></td><td>{line.discount_name ? <span>{line.discount_name} · <Money amount={line.discount_amount} /><span className="block text-xs text-slate-500">{line.discount_reason}</span></span> : "—"}</td><td>{line.tax_name ? <span>{line.tax_name} ({line.tax_rate_pct}%)<span className="block text-xs text-slate-500"><Money amount={line.tax_amount} /></span></span> : "—"}</td><td className="text-right font-medium"><Money amount={line.line_total} /></td></tr>)}</tbody></table></div><div className="ml-auto mt-6 max-w-sm space-y-2 border-t border-slate-200 pt-4 text-sm"><div className="flex justify-between"><span className="text-slate-500">Subtotal</span><Money amount={invoice.subtotal} /></div><div className="flex justify-between"><span className="text-slate-500">Discount</span><Money amount={invoice.discount_total} /></div><div className="flex justify-between"><span className="text-slate-500">Tax</span><Money amount={invoice.tax_total} /></div><div className="flex justify-between border-t border-slate-200 pt-2 text-base font-semibold"><span>Total</span><Money amount={invoice.total} /></div><div className="flex justify-between text-slate-500"><span>Paid</span><Money amount={invoice.amount_paid} /></div><div className="flex justify-between font-semibold"><span>Due</span><Money amount={invoice.amount_due} /></div></div></section>
    <ConfirmDialog open={cancelOpen} title="Cancel this invoice?" confirmLabel="Cancel invoice" onCancel={() => setCancelOpen(false)} onConfirm={() => { setCancelOpen(false); action.mutate({ name: "cancel" }); }}>This invoice will be cancelled and any reserved discount use will be released.</ConfirmDialog>
    <PaymentDialog open={paymentOpen} amountDue={invoice.amount_due} busy={payment.isPending} onCancel={() => setPaymentOpen(false)} onSubmit={(draft) => payment.mutateAsync(draft).then(() => undefined)} />
  </Screen>;
}

export const routes = [
  { path: "invoices", element: <RoleGuard roles={["admin", "staff"]}><InvoiceList /></RoleGuard> },
  { path: "invoices/:id", element: <RoleGuard roles={["admin", "staff"]}><InvoiceDetail /></RoleGuard> },
];
