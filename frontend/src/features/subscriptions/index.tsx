import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "../../api/client";
import type { Page } from "../../api/types";
import type { Subscription } from "../../api/models";
import { DataTable, type Column } from "../../components/DataTable";
import { Money } from "../../components/Money";
import { StatusChip } from "../../components/StatusChip";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { EmptyState, ErrorState, LoadingState, Screen, primaryButton, secondaryButton } from "../../components/Screen";
import { RoleGuard } from "../../app/RoleGuard";

const pageSize = 10;

function SubscriptionList() {
  const [page, setPage] = useState(1); const [status, setStatus] = useState(""); const [search, setSearch] = useState("");
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (status) query.set("status", status); if (search.trim()) query.set("q", search.trim());
  const result = useQuery({ queryKey: ["subscriptions", page, status, search], queryFn: () => apiRequest<Page<Subscription>>(`/subscriptions?${query}`) });
  const columns = useMemo<Column<Subscription>[]>(() => [
    { key: "number", header: "Subscription", render: (row) => <Link className="font-semibold text-indigo-700" to={`/subscriptions/${row.id}`}>{row.number}</Link> },
    { key: "customer", header: "Customer", render: (row) => row.customer_name },
    { key: "plan", header: "Plan", render: (row) => <><span className="block font-medium text-slate-800">{row.plan_name}</span><span className="text-xs capitalize text-slate-500">{row.billing_period}</span></> },
    { key: "status", header: "Status", render: (row) => <div className="flex items-center gap-2"><StatusChip status={row.status} />{row.is_paused && <StatusChip status="paused" />}</div> },
    { key: "next", header: "Next invoice", render: (row) => row.next_invoice_date ? new Date(`${row.next_invoice_date}T00:00:00`).toLocaleDateString("en-IN") : "—" },
    { key: "mrr", header: "Monthly value", render: (row) => <Money amount={row.monthly_value} /> },
  ], []);
  return <Screen eyebrow="Billing" title="Subscriptions" description="Track subscription status, billing dates, and customer value.">
    <div className="flex flex-wrap gap-3 rounded-xl border border-slate-200 bg-white p-4">
      <input aria-label="Search subscriptions" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="Search number or customer" className="min-w-64 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
      <select aria-label="Filter by status" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }} className="rounded-lg border border-slate-300 px-3 py-2 text-sm"><option value="">All statuses</option>{["draft", "quotation", "confirmed", "active", "closed"].map((item) => <option key={item}>{item}</option>)}</select>
      <button onClick={() => { setSearch(""); setStatus(""); setPage(1); }} className={secondaryButton}>Clear filters</button>
    </div>
    {result.isLoading ? <LoadingState label="Loading subscriptions…" /> : result.error ? <ErrorState message="Could not load subscriptions. Check the API or enable demo mode." onRetry={() => void result.refetch()} /> : (result.data?.total ?? 0) === 0 ? <EmptyState title="No subscriptions found" description="Try adjusting the filters or create a subscription when the subscription workflow is available." /> : <DataTable rows={result.data?.items ?? []} columns={columns} rowKey={(row) => row.id} page={page} pageSize={pageSize} total={result.data?.total ?? 0} onPageChange={setPage} />}
  </Screen>;
}

function today() { const date = new Date(); return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`; }
function nextTransition(subscription: Subscription): Subscription["status"] | null {
  if (subscription.status === "draft") return subscription.lines.length ? "quotation" : null;
  if (subscription.status === "quotation") return subscription.quotation_expires_on && subscription.quotation_expires_on < today() ? null : "confirmed";
  if (subscription.status === "confirmed") return subscription.start_date <= today() ? "active" : null;
  if (subscription.status === "active") return "closed";
  return null;
}

function SubscriptionDetail() {
  const { id = "" } = useParams(); const queryClient = useQueryClient(); const [confirmClose, setConfirmClose] = useState(false); const [notice, setNotice] = useState("");
  const key = ["subscription", id];
  const query = useQuery({ queryKey: key, queryFn: () => apiRequest<Subscription>(`/subscriptions/${id}`), enabled: Boolean(id) });
  const refresh = async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: ["subscription", id] }), queryClient.invalidateQueries({ queryKey: ["subscriptions"] })]); };
  const mutate = useMutation({ mutationFn: ({ path, body }: { path: string; body?: unknown }) => apiRequest<Subscription>(path, { method: "POST", ...(body ? { body: JSON.stringify(body) } : {}) }), onSuccess: async () => { setNotice("Subscription updated."); await refresh(); } });
  if (query.isLoading) return <LoadingState label="Loading subscription…" />;
  if (query.error || !query.data) return <ErrorState message="Subscription could not be loaded." onRetry={() => void query.refetch()} />;
  const subscription = query.data; const transition = nextTransition(subscription);
  const activate = (to: Subscription["status"]) => mutate.mutate({ path: `/subscriptions/${subscription.id}/transition`, body: { to } });
  return <Screen eyebrow="Subscription detail" title={subscription.number} description={`${subscription.customer_name} · ${subscription.plan_name}`} actions={<Link to="/subscriptions" className={secondaryButton}>Back to list</Link>}>
    {notice && <p role="status" className="rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-800">{notice}</p>}
    {mutate.error && <ErrorState message={mutate.error instanceof Error ? mutate.error.message : "Action failed"} />}
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><article className="rounded-xl border border-slate-200 bg-white p-5"><p className="text-sm text-slate-500">Status</p><div className="mt-2 flex gap-2"><StatusChip status={subscription.status} />{subscription.is_paused && <StatusChip status="paused" />}</div></article><article className="rounded-xl border border-slate-200 bg-white p-5"><p className="text-sm text-slate-500">Plan</p><p className="mt-2 font-semibold">{subscription.plan_name}</p><p className="text-sm capitalize text-slate-500">{subscription.billing_period}</p></article><article className="rounded-xl border border-slate-200 bg-white p-5"><p className="text-sm text-slate-500">Next invoice</p><p className="mt-2 font-semibold">{subscription.next_invoice_date ?? "—"}</p></article><article className="rounded-xl border border-slate-200 bg-white p-5"><p className="text-sm text-slate-500">Monthly value</p><p className="mt-2 text-xl font-semibold"><Money amount={subscription.monthly_value} /></p></article></div>
    <section className="rounded-xl border border-slate-200 bg-white p-5"><h2 className="font-semibold">Subscription lines</h2><div className="mt-4 divide-y divide-slate-100">{subscription.lines.map((line, index) => <div key={`${line.description}-${index}`} className="flex flex-wrap items-center justify-between gap-3 py-3"><div><p className="font-medium">{line.description}</p><p className="text-sm text-slate-500">Quantity {line.quantity}</p></div><Money amount={line.unit_price} /></div>)}</div></section>
    <div className="grid gap-6 lg:grid-cols-2">
      <section className="rounded-xl border border-slate-200 bg-white p-5"><h2 className="font-semibold">Status timeline</h2><ol className="mt-5 space-y-4">{subscription.history.map((item, index) => <li key={`${item.changed_at}-${index}`} className="relative flex gap-3"><span className="mt-1.5 h-2.5 w-2.5 rounded-full bg-indigo-500" /><div><p className="text-sm font-medium capitalize">{item.from_status ? `${item.from_status} → ` : "Created as "}{item.to_status}</p><p className="mt-1 text-xs text-slate-500">{new Date(item.changed_at).toLocaleString("en-IN")} · {item.changed_by}</p></div></li>)}</ol></section>
      <section className="rounded-xl border border-slate-200 bg-white p-5"><h2 className="font-semibold">Available actions</h2><p className="mt-1 text-sm text-slate-500">Actions are checked again by the API when connected.</p><div className="mt-4 flex flex-wrap gap-2">
        {transition && transition !== "closed" && <button disabled={mutate.isPending} onClick={() => activate(transition)} className={primaryButton}>{transition === "active" ? "Activate subscription" : `Move to ${transition}`}</button>}
        {subscription.status === "active" && subscription.pausable === true && <button disabled={mutate.isPending} onClick={() => mutate.mutate({ path: `/subscriptions/${subscription.id}/${subscription.is_paused ? "resume" : "pause"}` })} className={secondaryButton}>{subscription.is_paused ? "Resume billing" : "Pause billing"}</button>}
        {subscription.status === "active" && subscription.closable === true && <button disabled={mutate.isPending} onClick={() => setConfirmClose(true)} className="rounded-lg border border-rose-200 px-4 py-2.5 text-sm font-semibold text-rose-700 hover:bg-rose-50">Close subscription</button>}
        {subscription.status === "active" && subscription.renewable === true && <button disabled={mutate.isPending} onClick={() => mutate.mutate({ path: `/subscriptions/${subscription.id}/renew` })} className={secondaryButton}>Renew</button>}
        {!transition && subscription.status !== "active" && <span className="text-sm text-slate-500">No lifecycle action is available today.</span>}
      </div></section>
    </div>
    <ConfirmDialog open={confirmClose} title="Close this subscription?" confirmLabel="Close subscription" onCancel={() => setConfirmClose(false)} onConfirm={() => { setConfirmClose(false); mutate.mutate({ path: `/subscriptions/${subscription.id}/close` }); }}>Closing is terminal and stops future billing. This action cannot be undone.</ConfirmDialog>
  </Screen>;
}

export const routes = [
  { path: "subscriptions", element: <RoleGuard roles={["admin", "staff"]}><SubscriptionList /></RoleGuard> },
  { path: "subscriptions/:id", element: <RoleGuard roles={["admin", "staff"]}><SubscriptionDetail /></RoleGuard> },
];
