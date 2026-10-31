import { useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "../../api/client";
import type { Page } from "../../api/types";
import { DataTable, type Column } from "../../components/DataTable";
import { Money } from "../../components/Money";
import { StatusChip } from "../../components/StatusChip";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { EmptyState, ErrorState, LoadingState, Screen, primaryButton, secondaryButton } from "../../components/Screen";
import { RoleGuard } from "../../app/RoleGuard";

type Customer = { id: number; name: string; email: string; is_active: boolean };
type Plan = { id: number; name: string; price: string; billing_period: "daily" | "weekly" | "monthly" | "yearly"; min_quantity: number; pausable: boolean; closable: boolean; renewable: boolean; is_active: boolean };
type Product = { id: number; name: string; sales_price: string; default_tax_id: number | null; is_active: boolean };
type Template = { id: number; name: string; plan_id: number; validity_days: number; lines: { product_id: number; quantity: number; variant_value_ids: number[] }[] };
type SubscriptionRecord = { id: number; number: string; customer_id: number; plan_id: number; status: "draft" | "quotation" | "confirmed" | "active" | "closed"; start_date: string; expiry_date: string | null; next_invoice_date: string | null; payment_terms_days: number; quotation_expires_on: string | null; is_paused: boolean; lines: { id: number; product_id: number; description: string; quantity: number; unit_price: string; tax_id: number | null; variant_value_ids: number[] }[]; history: { id: number; from_status: string | null; to_status: string; changed_at: string; changed_by: number | null }[] };
type DisplaySubscription = SubscriptionRecord & { customer_name: string; plan_name: string; billing_period: Plan["billing_period"]; monthly_value: string; pausable: boolean; closable: boolean; renewable: boolean };
const pageSize = 10;
type CustomerOption = { id: number; name: string; email: string };
type TemplateOption = { id: number; name: string; plan_id: number; validity_days: number };
function CreateFromTemplate({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate(); const queryClient = useQueryClient();
  const customers = useQuery({ queryKey: ["subscription-create", "customers"], queryFn: () => apiRequest<Page<CustomerOption>>("/customers?page=1&page_size=100") });
  const templates = useQuery({ queryKey: ["subscription-create", "templates"], queryFn: () => apiRequest<Page<TemplateOption>>("/quotation-templates?page=1&page_size=100") });
  const create = useMutation({ mutationFn: (input: { templateId: number; customer_id: number; start_date: string }) => apiRequest<SubscriptionRecord>(`/subscriptions/from-template/${input.templateId}`, { method: "POST", body: JSON.stringify({ customer_id: input.customer_id, start_date: input.start_date }) }), onSuccess: async (subscription) => { await queryClient.invalidateQueries({ queryKey: ["subscriptions"] }); navigate(`/subscriptions/${subscription.id}`); } });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const values = new FormData(event.currentTarget);
    create.mutate({ templateId: Number(values.get("template_id")), customer_id: Number(values.get("customer_id")), start_date: String(values.get("start_date")) });
  }
  return <div className="fixed inset-0 z-40 grid place-items-center bg-slate-950/35 p-4"><section role="dialog" aria-modal="true" aria-labelledby="create-sub-title" className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl"><div className="flex items-start justify-between"><div><h2 id="create-sub-title" className="text-lg font-semibold">Create from quotation template</h2><p className="mt-1 text-sm text-slate-500">The API copies the template lines and applies its validity period.</p></div><button type="button" onClick={onClose} aria-label="Close form" className="rounded px-2 text-slate-500">×</button></div>{customers.isLoading || templates.isLoading ? <p role="status" className="mt-5 text-sm text-slate-500">Loading customers and templates…</p> : customers.error || templates.error ? <p role="alert" className="mt-5 text-sm text-rose-700">Could not load customers or quotation templates.</p> : !customers.data?.items.length || !templates.data?.items.length ? <p className="mt-5 text-sm text-slate-500">Create at least one active customer and quotation template before starting a subscription.</p> : <form onSubmit={submit} className="mt-5 space-y-4"><label className="block text-sm font-medium text-slate-700">Quotation template<select name="template_id" required className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2.5">{templates.data.items.map((item) => <option value={item.id} key={item.id}>{item.name} · {item.validity_days} days</option>)}</select></label><label className="block text-sm font-medium text-slate-700">Customer<select name="customer_id" required className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2.5">{customers.data.items.map((item) => <option value={item.id} key={item.id}>{item.name} · {item.email}</option>)}</select></label><label className="block text-sm font-medium text-slate-700">Start date<input name="start_date" type="date" defaultValue={today()} required className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2.5" /></label>{create.error && <p role="alert" className="text-sm text-rose-700">{create.error instanceof Error ? create.error.message : "Could not create subscription."}</p>}<div className="flex justify-end gap-2"><button type="button" onClick={onClose} className={secondaryButton}>Cancel</button><button disabled={create.isPending} className={primaryButton}>{create.isPending ? "Creating…" : "Create quotation"}</button></div></form>}</section></div>;
}

function decimalCents(value: string): bigint { const [whole, fraction = ""] = value.split("."); return BigInt(whole) * 100n + BigInt(fraction.padEnd(2, "0").slice(0, 2)); }
function centsDecimal(value: bigint): string { const absolute = value < 0n ? -value : value; return `${value < 0n ? "-" : ""}${absolute / 100n}.${String(absolute % 100n).padStart(2, "0")}`; }
function monthlyValue(subscription: SubscriptionRecord, period: Plan["billing_period"]): string {
  const cents = subscription.lines.reduce((sum, line) => sum + decimalCents(line.unit_price) * BigInt(line.quantity), 0n);
  if (period === "daily") return centsDecimal(cents * 30n);
  if (period === "weekly") return centsDecimal(cents * 52n / 12n);
  if (period === "yearly") return centsDecimal(cents / 12n);
  return centsDecimal(cents);
}
function today() { const date = new Date(); return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`; }
function nextTransition(subscription: SubscriptionRecord): SubscriptionRecord["status"] | null {
  if (subscription.status === "draft") return "quotation";
  if (subscription.status === "quotation") return subscription.quotation_expires_on && subscription.quotation_expires_on < today() ? null : "confirmed";
  if (subscription.status === "confirmed") return subscription.start_date <= today() ? "active" : null;
  return null;
}

function SubscriptionList() {
  const [page, setPage] = useState(1); const [status, setStatus] = useState(""); const [createOpen, setCreateOpen] = useState(false);
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) }); if (status) params.set("status", status);
  const result = useQuery({ queryKey: ["subscriptions", page, status], queryFn: () => apiRequest<Page<SubscriptionRecord>>(`/subscriptions?${params}`), refetchInterval: 15_000 });
  const customers = useQuery({ queryKey: ["customers", "lookup"], queryFn: () => apiRequest<Page<Customer>>("/customers?page=1&page_size=100") });
  const plans = useQuery({ queryKey: ["catalog", "plans"], queryFn: () => apiRequest<Page<Plan>>("/plans?page=1&page_size=100") });
  const rows = useMemo(() => (result.data?.items ?? []).map((subscription): DisplaySubscription => {
    const plan = plans.data?.items.find((item) => item.id === subscription.plan_id);
    return { ...subscription, customer_name: customers.data?.items.find((item) => item.id === subscription.customer_id)?.name ?? `Customer #${subscription.customer_id}`, plan_name: plan?.name ?? `Plan #${subscription.plan_id}`, billing_period: plan?.billing_period ?? "monthly", monthly_value: monthlyValue(subscription, plan?.billing_period ?? "monthly"), pausable: plan?.pausable ?? false, closable: plan?.closable ?? false, renewable: plan?.renewable ?? false };
  }), [result.data, customers.data, plans.data]);
  const columns = useMemo<Column<DisplaySubscription>[]>(() => [
    { key: "number", header: "Subscription", render: (row) => <Link className="font-semibold text-indigo-700" to={`/subscriptions/${row.id}`}>{row.number}</Link> },
    { key: "customer", header: "Customer", render: (row) => row.customer_name },
    { key: "plan", header: "Plan", render: (row) => <><span className="block font-medium text-slate-800">{row.plan_name}</span><span className="text-xs capitalize text-slate-500">{row.billing_period}</span></> },
    { key: "status", header: "Status", render: (row) => <div className="flex items-center gap-2"><StatusChip status={row.status} />{row.is_paused && <StatusChip status="paused" />}</div> },
    { key: "next", header: "Next invoice", render: (row) => row.next_invoice_date ? new Date(`${row.next_invoice_date}T00:00:00`).toLocaleDateString("en-IN") : "—" },
    { key: "mrr", header: "Monthly value", align: "right", render: (row) => <Money amount={row.monthly_value} /> },
  ], []);
  return <Screen eyebrow="Billing" title="Subscriptions" description="Track subscription status, billing dates, and customer value." actions={<div className="flex flex-wrap gap-2"><Link to="/subscriptions/new" className={primaryButton}>Create subscription</Link><button type="button" onClick={() => setCreateOpen(true)} className={secondaryButton}>Create from template</button></div>}>
    <div className="flex flex-wrap gap-3 rounded-xl border border-slate-200 bg-white p-4"><select aria-label="Filter by status" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }} className="rounded-lg border border-slate-300 px-3 py-2 text-sm"><option value="">All statuses</option>{["draft", "quotation", "confirmed", "active", "closed"].map((item) => <option key={item}>{item}</option>)}</select><button onClick={() => { setStatus(""); setPage(1); }} className={secondaryButton}>Clear filter</button></div>
    {result.isLoading || customers.isLoading || plans.isLoading ? <LoadingState label="Loading subscriptions…" /> : result.error || customers.error || plans.error ? <ErrorState message="Could not load subscriptions or their customer and plan details." onRetry={() => { void result.refetch(); void customers.refetch(); void plans.refetch(); }} /> : result.data?.total === 0 ? <EmptyState title="No subscriptions found" description="Create a subscription for an existing customer and plan." action={<Link to="/subscriptions/new" className={primaryButton}>Create subscription</Link>} /> : <DataTable rows={rows} columns={columns} rowKey={(row) => row.id} page={page} pageSize={pageSize} total={result.data?.total ?? 0} onPageChange={setPage} />}
    {createOpen && <CreateFromTemplate onClose={() => setCreateOpen(false)} />}
  </Screen>;
}

function NewSubscription() {
  const navigate = useNavigate(); const queryClient = useQueryClient(); const [customerId, setCustomerId] = useState(""); const [planId, setPlanId] = useState(""); const [productId, setProductId] = useState(""); const [templateId, setTemplateId] = useState(""); const [quantity, setQuantity] = useState("1"); const [startDate, setStartDate] = useState(today()); const [expiryDate, setExpiryDate] = useState(""); const [terms, setTerms] = useState("14"); const [error, setError] = useState("");
  const customers = useQuery({ queryKey: ["customers", "lookup"], queryFn: () => apiRequest<Page<Customer>>("/customers?page=1&page_size=100") });
  const plans = useQuery({ queryKey: ["catalog", "plans"], queryFn: () => apiRequest<Page<Plan>>("/plans?page=1&page_size=100") });
  const products = useQuery({ queryKey: ["catalog", "products"], queryFn: () => apiRequest<Page<Product>>("/products?page=1&page_size=100") });
  const templates = useQuery({ queryKey: ["catalog", "templates"], queryFn: () => apiRequest<Page<Template>>("/quotation-templates?page=1&page_size=100") });
  const create = useMutation({ mutationFn: async () => {
    if (templateId) return apiRequest<SubscriptionRecord>(`/subscriptions/from-template/${templateId}`, { method: "POST", body: JSON.stringify({ customer_id: Number(customerId), start_date: startDate }) });
    return apiRequest<SubscriptionRecord>("/subscriptions", { method: "POST", body: JSON.stringify({ customer_id: Number(customerId), plan_id: Number(planId), start_date: startDate, expiry_date: expiryDate || null, payment_terms_days: Number(terms), lines: [{ product_id: Number(productId), quantity: Number(quantity), variant_value_ids: [] }] }) });
  }, onSuccess: async (subscription) => { await queryClient.invalidateQueries({ queryKey: ["subscriptions"] }); navigate(`/subscriptions/${subscription.id}`); }, onError: (reason) => setError(reason instanceof Error ? reason.message : "Could not create subscription.") });
  const pending = customers.isLoading || plans.isLoading || products.isLoading || templates.isLoading;
  if (pending) return <LoadingState label="Loading customers, plans, and products…" />;
  if (customers.error || plans.error || products.error || templates.error) return <ErrorState message="Subscription setup data could not be loaded." onRetry={() => { void customers.refetch(); void plans.refetch(); void products.refetch(); void templates.refetch(); }} />;
  const availableCustomers = customers.data?.items.filter((item) => item.is_active) ?? [];
  const availablePlans = plans.data?.items.filter((item) => item.is_active) ?? [];
  const availableProducts = products.data?.items.filter((item) => item.is_active) ?? [];
  return <Screen eyebrow="Billing" title="Create subscription" description="Start a draft subscription from a plan and product, or use a quotation template." actions={<Link to="/subscriptions" className={secondaryButton}>Back to subscriptions</Link>}>
    <form className="space-y-5 rounded-xl border border-slate-200 bg-white p-5" onSubmit={(event) => { event.preventDefault(); setError(""); create.mutate(); }}>
      <div className="grid gap-4 sm:grid-cols-2"><label className="text-sm font-medium text-slate-700">Customer<select required value={customerId} onChange={(e) => setCustomerId(e.target.value)} className="mt-1.5 block w-full rounded-lg border border-slate-300 px-3 py-2.5">{availableCustomers.map((customer) => <option key={customer.id} value={customer.id}>{customer.name} · {customer.email}</option>)}</select></label><label className="text-sm font-medium text-slate-700">Start date<input required type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="mt-1.5 block w-full rounded-lg border border-slate-300 px-3 py-2.5" /></label><label className="text-sm font-medium text-slate-700">Quotation template (optional)<select value={templateId} onChange={(e) => setTemplateId(e.target.value)} className="mt-1.5 block w-full rounded-lg border border-slate-300 px-3 py-2.5"><option value="">Build from plan and product</option>{templates.data?.items.map((template) => <option key={template.id} value={template.id}>{template.name}</option>)}</select></label>
      {!templateId && <><label className="text-sm font-medium text-slate-700">Plan<select required value={planId} onChange={(e) => setPlanId(e.target.value)} className="mt-1.5 block w-full rounded-lg border border-slate-300 px-3 py-2.5">{availablePlans.map((plan) => <option key={plan.id} value={plan.id}>{plan.name} · {plan.price} / {plan.billing_period}</option>)}</select></label><label className="text-sm font-medium text-slate-700">Product<select required value={productId} onChange={(e) => setProductId(e.target.value)} className="mt-1.5 block w-full rounded-lg border border-slate-300 px-3 py-2.5">{availableProducts.map((product) => <option key={product.id} value={product.id}>{product.name} · {product.sales_price}</option>)}</select></label><label className="text-sm font-medium text-slate-700">Quantity<input required type="number" min="1" max="100000" value={quantity} onChange={(e) => setQuantity(e.target.value)} className="mt-1.5 block w-full rounded-lg border border-slate-300 px-3 py-2.5" /></label><label className="text-sm font-medium text-slate-700">Expiry date (optional)<input type="date" value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} className="mt-1.5 block w-full rounded-lg border border-slate-300 px-3 py-2.5" /></label><label className="text-sm font-medium text-slate-700">Payment terms (days)<input type="number" min="0" max="365" value={terms} onChange={(e) => setTerms(e.target.value)} className="mt-1.5 block w-full rounded-lg border border-slate-300 px-3 py-2.5" /></label></>}
      </div>
      {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}<button disabled={create.isPending || !customerId || (!templateId && (!planId || !productId))} className={primaryButton}>{create.isPending ? "Creating…" : templateId ? "Create quotation from template" : "Create draft subscription"}</button>
    </form>
  </Screen>;
}

function SubscriptionDetail() {
  const { id = "" } = useParams(); const queryClient = useQueryClient(); const [confirmClose, setConfirmClose] = useState(false); const [notice, setNotice] = useState("");
  const key = ["subscription", id]; const query = useQuery({ queryKey: key, queryFn: () => apiRequest<SubscriptionRecord>(`/subscriptions/${id}`), enabled: Boolean(id) });
  const customers = useQuery({ queryKey: ["customer", query.data?.customer_id], queryFn: () => apiRequest<Customer>(`/customers/${query.data?.customer_id}`), enabled: Boolean(query.data?.customer_id) });
  const plan = useQuery({ queryKey: ["plan", query.data?.plan_id], queryFn: () => apiRequest<Plan>(`/plans/${query.data?.plan_id}`), enabled: Boolean(query.data?.plan_id) });
  const refresh = async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: key }), queryClient.invalidateQueries({ queryKey: ["subscriptions"] }), queryClient.invalidateQueries({ queryKey: ["reports"] })]); };
  const mutate = useMutation({ mutationFn: async ({ path, body }: { path: string; body?: unknown }) => {
    const init = { method: "POST", ...(body ? { body: JSON.stringify(body) } : {}) };
    if (path.endsWith("/renew")) {
      const result = await apiRequest<{ subscription: SubscriptionRecord }>(path, init);
      return result.subscription;
    }
    return apiRequest<SubscriptionRecord>(path, init);
  }, onSuccess: async (_data, vars) => { setNotice(vars.path.endsWith("/close") ? "Subscription closed." : vars.path.endsWith("/renew") ? "Renewal draft created." : "Subscription updated."); await refresh(); } });
  if (query.isLoading) return <LoadingState label="Loading subscription…" />;
  if (query.error || !query.data) return <ErrorState message="Subscription could not be loaded." onRetry={() => void query.refetch()} />;
  const subscription = query.data; const transition = nextTransition(subscription); const recurring = monthlyValue(subscription, plan.data?.billing_period ?? "monthly");
  const activate = (to: SubscriptionRecord["status"]) => mutate.mutate({ path: `/subscriptions/${subscription.id}/transition`, body: { to } });
  return <Screen eyebrow="Subscription detail" title={subscription.number} description={`${customers.data?.name ?? `Customer #${subscription.customer_id}`} · ${plan.data?.name ?? `Plan #${subscription.plan_id}`}`} actions={<Link to="/subscriptions" className={secondaryButton}>Back to list</Link>}>
    {notice && <p role="status" className="rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-800">{notice}</p>}{(mutate.error || customers.error || plan.error) && <ErrorState message={mutate.error instanceof Error ? mutate.error.message : "Related account details could not be loaded."} />}
    <dl className="grid grid-cols-2 gap-x-5 border-y border-slate-300 py-4 sm:grid-cols-4"><div className="py-2"><dt className="text-sm text-slate-600">Status</dt><dd className="mt-2 flex flex-wrap gap-2"><StatusChip status={subscription.status} />{subscription.is_paused && <StatusChip status="paused" />}</dd></div><div className="py-2"><dt className="text-sm text-slate-600">Plan</dt><dd className="mt-2 font-semibold text-slate-900">{plan.data?.name ?? `Plan #${subscription.plan_id}`}</dd><dd className="text-sm capitalize text-slate-600">{plan.data?.billing_period ?? "recurring"}</dd></div><div className="py-2"><dt className="text-sm text-slate-600">Next invoice</dt><dd className="mt-2 font-semibold text-slate-900">{subscription.next_invoice_date ?? "—"}</dd></div><div className="py-2"><dt className="text-sm text-slate-600">Monthly value</dt><dd className="mt-2 text-xl font-semibold tabular-nums text-slate-900"><Money amount={recurring} /></dd></div></dl>
    <section className="border-t-2 border-slate-300 bg-white p-5"><h2 className="text-lg font-semibold">Subscription lines</h2><div className="mt-4 divide-y divide-slate-200">{subscription.lines.map((line) => <div key={line.id} className="flex flex-wrap items-center justify-between gap-3 py-3"><div><p className="font-medium text-slate-900">{line.description}</p><p className="text-sm text-slate-600">Quantity {line.quantity}</p></div><Money amount={line.unit_price} /></div>)}</div></section>
    <div className="grid gap-6 lg:grid-cols-2"><section className="rounded-xl border border-slate-200 bg-white p-5"><h2 className="font-semibold">Status timeline</h2><ol className="mt-5 space-y-4">{subscription.history.map((item) => <li key={item.id} className="relative flex gap-3"><span className="mt-1.5 h-2.5 w-2.5 rounded-full bg-indigo-500" /><div><p className="text-sm font-medium capitalize">{item.from_status ? `${item.from_status} → ` : "Created as "}{item.to_status}</p><p className="mt-1 text-xs text-slate-500">{new Date(item.changed_at).toLocaleString("en-IN")} · {item.changed_by ?? "System"}</p></div></li>)}</ol></section>
      <section className="rounded-xl border border-slate-200 bg-white p-5"><h2 className="font-semibold">Available actions</h2><p className="mt-1 text-sm text-slate-500">The API verifies lifecycle rules again for every action.</p><div className="mt-4 flex flex-wrap gap-2">{transition && <button disabled={mutate.isPending} onClick={() => activate(transition)} className={primaryButton}>{transition === "active" ? "Activate subscription" : `Move to ${transition}`}</button>}{subscription.status === "active" && plan.data?.pausable && <button disabled={mutate.isPending} onClick={() => mutate.mutate({ path: `/subscriptions/${subscription.id}/${subscription.is_paused ? "resume" : "pause"}` })} className={secondaryButton}>{subscription.is_paused ? "Resume billing" : "Pause billing"}</button>}{subscription.status === "active" && plan.data?.closable && <button disabled={mutate.isPending} onClick={() => setConfirmClose(true)} className="rounded-lg border border-rose-200 px-4 py-2.5 text-sm font-semibold text-rose-700 hover:bg-rose-50">Close subscription</button>}{subscription.status === "active" && plan.data?.renewable && <button disabled={mutate.isPending} onClick={() => mutate.mutate({ path: `/subscriptions/${subscription.id}/renew` })} className={secondaryButton}>Renew</button>}{!transition && subscription.status !== "active" && <span className="text-sm text-slate-500">No lifecycle action is available today.</span>}</div></section>
    </div>
    <ConfirmDialog open={confirmClose} title="Close this subscription?" confirmLabel="Close subscription" onCancel={() => setConfirmClose(false)} onConfirm={() => { setConfirmClose(false); mutate.mutate({ path: `/subscriptions/${subscription.id}/close` }); }}>Closing is terminal and stops future billing. This action cannot be undone.</ConfirmDialog>
  </Screen>;
}

export const routes = [
  { path: "subscriptions", element: <RoleGuard roles={["admin", "staff"]}><SubscriptionList /></RoleGuard> },
  { path: "subscriptions/new", element: <RoleGuard roles={["admin", "staff"]}><NewSubscription /></RoleGuard> },
  { path: "subscriptions/:id", element: <RoleGuard roles={["admin", "staff"]}><SubscriptionDetail /></RoleGuard> },
];
