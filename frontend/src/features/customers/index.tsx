import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "../../api/client";
import type { Page } from "../../api/types";
import { DataTable, type Column } from "../../components/DataTable";
import { StatusChip } from "../../components/StatusChip";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { ErrorState, LoadingState, Screen, primaryButton, secondaryButton } from "../../components/Screen";
import { RoleGuard } from "../../app/RoleGuard";

type Customer = { id: number; user_id: number | null; name: string; email: string; phone: string | null; company: string | null; billing_address: string | null; tax_id: string | null; is_active: boolean };
const pageSize = 10;

function CustomerList() {
  const [page, setPage] = useState(1); const [search, setSearch] = useState("");
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) }); if (search.trim()) params.set("q", search.trim());
  const query = useQuery({ queryKey: ["customers", page, search], queryFn: () => apiRequest<Page<Customer>>(`/customers?${params}`) });
  const columns = useMemo<Column<Customer>[]>(() => [
    { key: "name", header: "Customer", render: (row) => <Link to={`/customers/${row.id}`} className="font-semibold text-indigo-700">{row.name}</Link> },
    { key: "company", header: "Company", render: (row) => row.company || "—" },
    { key: "email", header: "Email", render: (row) => <a className="text-slate-700 hover:text-indigo-700" href={`mailto:${row.email}`}>{row.email}</a> },
    { key: "phone", header: "Phone", render: (row) => row.phone || "—" },
    { key: "status", header: "Status", render: (row) => <StatusChip status={row.is_active ? "active" : "inactive"} /> },
  ], []);
  return <Screen eyebrow="Workspace" title="Customers" description="Keep customer contacts and billing details ready for every subscription.">
    <div className="flex flex-wrap gap-3 rounded-xl border border-slate-200 bg-white p-4"><input aria-label="Search customers" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="Search name, company, or email" className="min-w-64 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" /><Link className={primaryButton} to="/customers/new">Add customer</Link></div>
    {query.isLoading ? <LoadingState label="Loading customers…" /> : query.error ? <ErrorState message="Could not load customers. Check your connection and try again." onRetry={() => void query.refetch()} /> : <DataTable rows={query.data?.items ?? []} columns={columns} rowKey={(row) => row.id} page={page} pageSize={pageSize} total={query.data?.total ?? 0} onPageChange={setPage} />}
  </Screen>;
}

function CustomerForm({ customer, onDone }: { customer?: Customer; onDone: () => void }) {
  const [error, setError] = useState(""); const [name, setName] = useState(customer?.name ?? ""); const [email, setEmail] = useState(customer?.email ?? "");
  const [company, setCompany] = useState(customer?.company ?? ""); const [phone, setPhone] = useState(customer?.phone ?? ""); const [billingAddress, setBillingAddress] = useState(customer?.billing_address ?? ""); const [taxId, setTaxId] = useState(customer?.tax_id ?? "");
  const queryClient = useQueryClient();
  const save = useMutation({ mutationFn: () => apiRequest<Customer>(customer ? `/customers/${customer.id}` : "/customers", { method: customer ? "PUT" : "POST", body: JSON.stringify({ name, email, company: company || null, phone: phone || null, billing_address: billingAddress || null, tax_id: taxId || null }) }), onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["customers"] }); onDone(); }, onError: (reason) => setError(reason instanceof Error ? reason.message : "Could not save customer.") });
  return <form className="space-y-5 rounded-xl border border-slate-200 bg-white p-5" onSubmit={(event) => { event.preventDefault(); setError(""); save.mutate(); }}>
    <div className="grid gap-4 sm:grid-cols-2"><label className="text-sm font-medium text-slate-700">Full name<input required maxLength={160} value={name} onChange={(e) => setName(e.target.value)} className="mt-1.5 block w-full rounded-lg border border-slate-300 px-3 py-2.5 font-normal" /></label><label className="text-sm font-medium text-slate-700">Email<input required type="email" maxLength={320} value={email} onChange={(e) => setEmail(e.target.value)} className="mt-1.5 block w-full rounded-lg border border-slate-300 px-3 py-2.5 font-normal" /></label><label className="text-sm font-medium text-slate-700">Company<input maxLength={160} value={company} onChange={(e) => setCompany(e.target.value)} className="mt-1.5 block w-full rounded-lg border border-slate-300 px-3 py-2.5 font-normal" /></label><label className="text-sm font-medium text-slate-700">Phone<input maxLength={40} value={phone} onChange={(e) => setPhone(e.target.value)} className="mt-1.5 block w-full rounded-lg border border-slate-300 px-3 py-2.5 font-normal" /></label><label className="text-sm font-medium text-slate-700">Tax ID<input maxLength={80} value={taxId} onChange={(e) => setTaxId(e.target.value)} className="mt-1.5 block w-full rounded-lg border border-slate-300 px-3 py-2.5 font-normal" /></label><label className="text-sm font-medium text-slate-700 sm:col-span-2">Billing address<textarea maxLength={4000} rows={3} value={billingAddress} onChange={(e) => setBillingAddress(e.target.value)} className="mt-1.5 block w-full rounded-lg border border-slate-300 px-3 py-2.5 font-normal" /></label></div>
    {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}<div className="flex gap-2"><button disabled={save.isPending} className={primaryButton}>{save.isPending ? "Saving…" : customer ? "Save changes" : "Create customer"}</button><Link className={secondaryButton} to={customer ? `/customers/${customer.id}` : "/customers"}>Cancel</Link></div>
  </form>;
}

function CustomerDetail() {
  const { id = "" } = useParams(); const [confirmDeactivate, setConfirmDeactivate] = useState(false); const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["customer", id], queryFn: () => apiRequest<Customer>(`/customers/${id}`), enabled: Boolean(id) });
  const deactivate = useMutation({ mutationFn: () => apiRequest<void>(`/customers/${id}`, { method: "DELETE" }), onSuccess: async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: ["customer", id] }), queryClient.invalidateQueries({ queryKey: ["customers"] })]); } });
  if (query.isLoading) return <LoadingState label="Loading customer…" />;
  if (query.error || !query.data) return <ErrorState message="Customer could not be loaded." onRetry={() => void query.refetch()} />;
  const customer = query.data;
  return <Screen eyebrow="Customer record" title={customer.name} description={customer.company || customer.email} actions={<><Link to="/customers" className={secondaryButton}>Back to customers</Link>{customer.is_active && <Link to={`/customers/${id}/edit`} className={primaryButton}>Edit customer</Link>}</>}>
    {deactivate.error && <ErrorState message={deactivate.error instanceof Error ? deactivate.error.message : "Could not deactivate customer."} />}
    <div className="grid gap-4 sm:grid-cols-2"><article className="rounded-xl border border-slate-200 bg-white p-5"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Contact</p><dl className="mt-4 space-y-3 text-sm"><div><dt className="text-slate-500">Email</dt><dd><a href={`mailto:${customer.email}`} className="font-medium text-indigo-700">{customer.email}</a></dd></div><div><dt className="text-slate-500">Phone</dt><dd className="font-medium">{customer.phone || "Not provided"}</dd></div></dl></article><article className="rounded-xl border border-slate-200 bg-white p-5"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Billing profile</p><dl className="mt-4 space-y-3 text-sm"><div><dt className="text-slate-500">Tax ID</dt><dd className="font-medium">{customer.tax_id || "Not provided"}</dd></div><div><dt className="text-slate-500">Address</dt><dd className="whitespace-pre-line font-medium">{customer.billing_address || "Not provided"}</dd></div></dl></article></div>
    <section className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-5"><div><h2 className="font-semibold">Customer status</h2><p className="mt-1 text-sm text-slate-500">Deactivation keeps billing history while preventing this customer from being selected for new work.</p></div><div className="flex items-center gap-3"><StatusChip status={customer.is_active ? "active" : "inactive"} />{customer.is_active && <button onClick={() => setConfirmDeactivate(true)} className="rounded-lg border border-rose-200 px-4 py-2.5 text-sm font-semibold text-rose-700 hover:bg-rose-50">Deactivate</button>}</div></section>
    <ConfirmDialog open={confirmDeactivate} title="Deactivate this customer?" confirmLabel={deactivate.isPending ? "Deactivating…" : "Deactivate customer"} onCancel={() => setConfirmDeactivate(false)} onConfirm={() => { setConfirmDeactivate(false); deactivate.mutate(); }}>The customer and their historical invoices remain available for reference.</ConfirmDialog>
  </Screen>;
}

function NewCustomer() { return <Screen eyebrow="Workspace" title="Add customer" description="Create a customer profile for subscriptions and billing."><CustomerForm onDone={() => { window.location.assign("/customers"); }} /></Screen>; }
function EditCustomer() { const { id = "" } = useParams(); const query = useQuery({ queryKey: ["customer", id], queryFn: () => apiRequest<Customer>(`/customers/${id}`), enabled: Boolean(id) }); if (query.isLoading) return <LoadingState />; if (!query.data || query.error) return <ErrorState message="Customer could not be loaded." onRetry={() => void query.refetch()} />; return <Screen eyebrow="Workspace" title={`Edit ${query.data.name}`}><CustomerForm customer={query.data} onDone={() => { window.location.assign(`/customers/${id}`); }} /></Screen>; }

export const routes = [
  { path: "customers", element: <RoleGuard roles={["admin", "staff"]}><CustomerList /></RoleGuard> },
  { path: "customers/new", element: <RoleGuard roles={["admin", "staff"]}><NewCustomer /></RoleGuard> },
  { path: "customers/:id/edit", element: <RoleGuard roles={["admin", "staff"]}><EditCustomer /></RoleGuard> },
  { path: "customers/:id", element: <RoleGuard roles={["admin", "staff"]}><CustomerDetail /></RoleGuard> },
];
