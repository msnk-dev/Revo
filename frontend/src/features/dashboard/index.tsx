import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { apiRequest } from "../../api/client";
import type { RevenuePoint, Summary } from "../../api/models";
import { DataTable, type Column } from "../../components/DataTable";
import { Money } from "../../components/Money";
import { ErrorState, LoadingState, Screen } from "../../components/Screen";
import { RoleGuard } from "../../app/RoleGuard";
import { useAuth } from "../../app/AuthContext";

type RenewalReminder = { subscription_id: number; number: string; customer_id: number; expiry_date: string };
type JobName = "activate_subscriptions" | "auto_close_expired" | "generate_invoices" | "expire_quotations" | "renewal_reminders" | "daily_cfo_brief";
const jobs: { name: JobName; label: string; description: string }[] = [
  { name: "activate_subscriptions", label: "Activate subscriptions", description: "Activate confirmed subscriptions whose start date has arrived." },
  { name: "auto_close_expired", label: "Close expired subscriptions", description: "Close active subscriptions whose plan enables auto-close." },
  { name: "generate_invoices", label: "Generate due invoices", description: "Create draft invoices for due subscriptions." },
  { name: "expire_quotations", label: "Check expired quotations", description: "List quotations past their validity date." },
  { name: "renewal_reminders", label: "Refresh renewal reminders", description: "List active subscriptions expiring within seven days." },
  { name: "daily_cfo_brief", label: "Generate CFO brief", description: "Run the daily brief job using report data." },
];

function AdminJobsPanel() {
  const queryClient = useQueryClient();
  const mockMode = import.meta.env.VITE_USE_MOCKS === "true";
  const quotations = useQuery({ queryKey: ["admin-jobs", "expired-quotations"], queryFn: () => apiRequest<{ count: number; subscription_ids: number[] }>("/admin/jobs/expired-quotations"), refetchInterval: 60_000, enabled: !mockMode });
  const reminders = useQuery({ queryKey: ["admin-jobs", "renewal-reminders"], queryFn: () => apiRequest<{ count: number; items: RenewalReminder[] }>("/admin/jobs/renewal-reminders"), refetchInterval: 60_000, enabled: !mockMode });
  const run = useMutation({ mutationFn: (name: JobName) => apiRequest<Record<string, unknown>>(`/admin/jobs/${name}/run`, { method: "POST" }), onSuccess: async (_result, name) => { await queryClient.invalidateQueries({ queryKey: ["admin-jobs"] }); if (name === "generate_invoices") await queryClient.invalidateQueries({ queryKey: ["invoices"] }); if (name === "daily_cfo_brief") await queryClient.invalidateQueries({ queryKey: ["ai", "brief"] }); } });
  if (mockMode) return <section className="border-t-2 border-slate-300 bg-white p-5"><h2 className="text-lg font-semibold text-slate-900">Background jobs</h2><p className="mt-2 text-base text-slate-600">Job status and manual runs require the live API. Demo mode does not fabricate job results.</p></section>;
  return <section className="space-y-5 border-t-2 border-slate-300 bg-white p-5" aria-labelledby="job-panel-title">
    <div><h2 id="job-panel-title" className="text-lg font-semibold text-slate-900">Background jobs</h2><p className="mt-1 text-base text-slate-600">Review scheduler outputs and run an existing backend job on demand.</p></div>
    <div className="grid gap-3 sm:grid-cols-2"><article className="rounded-xl bg-slate-50 p-4"><p className="text-sm font-medium text-slate-700">Expired quotations</p>{quotations.isLoading ? <p role="status" className="mt-2 text-sm text-slate-500">Loading…</p> : quotations.error ? <p role="alert" className="mt-2 text-sm text-rose-700">Could not load expired quotations.</p> : <p className="mt-2 text-2xl font-semibold text-slate-900">{quotations.data?.count ?? 0}</p>}</article><article className="rounded-xl bg-slate-50 p-4"><p className="text-sm font-medium text-slate-700">Renewals due in 7 days</p>{reminders.isLoading ? <p role="status" className="mt-2 text-sm text-slate-500">Loading…</p> : reminders.error ? <p role="alert" className="mt-2 text-sm text-rose-700">Could not load renewal reminders.</p> : <><p className="mt-2 text-2xl font-semibold text-slate-900">{reminders.data?.count ?? 0}</p>{(reminders.data?.items ?? []).slice(0, 3).map((item) => <p key={item.subscription_id} className="mt-1 text-xs text-slate-500">{item.number} · expires {item.expiry_date}</p>)}</>}</article></div>
    <div className="divide-y divide-slate-200 border-y border-slate-300">{jobs.map((job) => <button type="button" key={job.name} disabled={run.isPending} onClick={() => run.mutate(job.name)} className="flex min-h-14 w-full flex-col justify-center gap-1 py-3 text-left transition-colors hover:bg-slate-50 disabled:opacity-50 sm:flex-row sm:items-center sm:justify-between sm:gap-5"><span className="text-base font-semibold text-slate-800">{run.isPending && run.variables === job.name ? "Running…" : job.label}</span><span className="text-sm leading-5 text-slate-600 sm:text-right">{job.description}</span></button>)}</div>
    {run.data && <p role="status" className="rounded-lg bg-emerald-50 p-3 text-xs text-emerald-800">Job response: {JSON.stringify(run.data)}</p>}{run.error && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{run.error instanceof Error ? run.error.message : "The job could not be run."}</p>}
  </section>;
}

function cents(value: string): bigint {
  const [whole, fraction = ""] = value.split(".");
  return BigInt(whole) * 100n + BigInt(fraction.padEnd(2, "0").slice(0, 2));
}

function monthLabel(value: string) {
  return new Intl.DateTimeFormat("en-IN", { month: "short" }).format(new Date(`${value}T00:00:00`));
}

function localIsoDate(value: Date) { return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`; }

function DashboardPage() {
  const { user } = useAuth();
  type OverdueRow = { invoice_id: number; invoice_number: string; customer_name: string; due_date: string; days_overdue: number; amount_due: string };
  type RenewalReminder = { subscription_id: number; number: string; customer_name: string; plan_name: string; expiry_date: string; days_remaining: number };
  type Brief = { brief_date: string; narrative: string; used_fallback: boolean; provider: string | null; model: string | null };
  const queryClient = useQueryClient();
  const today = new Date(); const end = localIsoDate(today); const yearStart = `${today.getFullYear()}-01-01`; const sixMonthStart = localIsoDate(new Date(today.getFullYear(), today.getMonth() - 5, 1));
  const summary = useQuery({ queryKey: ["reports", "summary", yearStart, end], queryFn: () => apiRequest<Summary>(`/reports/summary?${new URLSearchParams({ from: yearStart, to: end })}`), refetchInterval: 15_000 });
  const revenue = useQuery({ queryKey: ["reports", "revenue", sixMonthStart, end], queryFn: () => apiRequest<RevenuePoint[]>(`/reports/revenue?${new URLSearchParams({ from: sixMonthStart, to: end })}`) });
  const overdue = useQuery({ queryKey: ["reports", "overdue"], queryFn: () => apiRequest<OverdueRow[]>("/reports/overdue?limit=5"), refetchInterval: 15_000 });
  const renewals = useQuery({ queryKey: ["reports", "renewal-reminders"], queryFn: () => apiRequest<{ count: number; items: RenewalReminder[] }>("/reports/renewal-reminders"), refetchInterval: 15_000 });
  const brief = useQuery({ queryKey: ["ai", "brief", "latest"], queryFn: () => apiRequest<Brief | null>("/ai/brief/latest"), refetchInterval: 15_000 });
  const generateBrief = useMutation({ mutationFn: () => apiRequest<Brief>("/ai/brief/generate", { method: "POST" }), onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["ai", "brief"] }); } });

  if (summary.isLoading) return <LoadingState label="Loading dashboard…" />;
  if (summary.error || !summary.data) return <ErrorState message={summary.error instanceof Error ? summary.error.message : "Dashboard summary unavailable."} onRetry={() => void summary.refetch()} />;
  const points = revenue.data ?? [];
  const max = points.reduce((largest, point) => cents(point.revenue_collected) > largest ? cents(point.revenue_collected) : largest, 1n);
  const overdueColumns: Column<OverdueRow>[] = [
    { key: "number", header: "Invoice", render: (row) => <Link to={`/invoices/${row.invoice_id}`} className="font-semibold text-indigo-700">{row.invoice_number}</Link> },
    { key: "customer", header: "Customer", render: (row) => row.customer_name },
    { key: "due", header: "Due date", render: (row) => new Date(`${row.due_date}T00:00:00`).toLocaleDateString("en-IN") },
    { key: "amount", header: "Amount due", align: "right", render: (row) => <Money amount={row.amount_due} /> },
  ];
  const renewalColumns: Column<RenewalReminder>[] = [
    { key: "subscription", header: "Subscription", render: (row) => <Link to={`/subscriptions/${row.subscription_id}`} className="font-semibold text-indigo-700">{row.number}</Link> },
    { key: "customer", header: "Customer", render: (row) => row.customer_name },
    { key: "plan", header: "Plan", render: (row) => row.plan_name },
    { key: "expiry", header: "Expires", render: (row) => new Date(`${row.expiry_date}T00:00:00`).toLocaleDateString("en-IN") },
    { key: "days", header: "In", render: (row) => `${row.days_remaining} day${row.days_remaining === 1 ? "" : "s"}` },
  ];

  return <Screen eyebrow="Financial overview" title="Revenue at a glance" description="Recurring value, collections, and the accounts that need attention.">
    {import.meta.env.VITE_USE_MOCKS === "true" && <p className="border-l-4 border-amber-600 bg-amber-50 px-4 py-3 text-sm text-amber-950">Preview data is enabled. Values come from the local mock API.</p>}
    <section className="grid gap-7 bg-[#193b2b] px-5 py-6 text-white sm:grid-cols-[minmax(14rem,.9fr)_2fr] sm:px-7 sm:py-8">
      <div className="sm:border-r sm:border-white/20 sm:pr-7"><h2 className="text-base font-medium text-white/75">Monthly recurring revenue</h2><p className="mt-3 text-3xl font-semibold tabular-nums tracking-tight sm:text-4xl"><Money amount={summary.data.mrr} /></p><p className="mt-2 text-sm text-white/65">Pre-tax monthly equivalent · year to date {new Date(`${yearStart}T00:00:00`).getFullYear()}</p></div>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-3 sm:content-center"><div><dt className="text-sm text-white/65">Active subscriptions</dt><dd className="mt-1 text-xl font-semibold tabular-nums">{summary.data.active_subscriptions}</dd><dd className="mt-1 text-sm text-white/55">{summary.data.paused_subscriptions} paused</dd></div><div><dt className="text-sm text-white/65">Collected</dt><dd className="mt-1 text-xl font-semibold tabular-nums"><Money amount={summary.data.collected} /></dd><dd className="mt-1 text-sm text-white/55">Payments received</dd></div><div><dt className="text-sm text-white/65">Outstanding</dt><dd className="mt-1 text-xl font-semibold tabular-nums"><Money amount={summary.data.outstanding} /></dd><dd className="mt-1 text-sm text-white/55">Confirmed invoices</dd></div><div><dt className="text-sm text-white/65">Overdue invoices</dt><dd className="mt-1 text-xl font-semibold tabular-nums">{summary.data.overdue_count}</dd></div><div><dt className="text-sm text-white/65">Renewals in 7 days</dt><dd className="mt-1 text-xl font-semibold tabular-nums">{renewals.data?.count ?? (renewals.isLoading ? "…" : "—")}</dd></div></dl>
    </section>
    <section className="space-y-3">
      <div><h2 className="font-semibold text-slate-900">Upcoming renewals <span className="text-slate-500">({renewals.data?.count ?? 0})</span></h2><p className="mt-1 text-sm text-slate-500">Active subscriptions expiring today through the next 7 days</p></div>
      {renewals.isLoading ? <LoadingState label="Loading upcoming renewals…" /> : renewals.error ? <ErrorState message="Upcoming renewals are unavailable." onRetry={() => void renewals.refetch()} /> : <DataTable rows={renewals.data?.items ?? []} columns={renewalColumns} rowKey={(row) => row.subscription_id} page={1} pageSize={100} total={renewals.data?.count ?? 0} onPageChange={() => undefined} />}
    </section>
    <div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
      <section className="border-t-2 border-slate-300 bg-white p-5 sm:p-6">
        <div className="flex items-center justify-between"><div><h2 className="text-lg font-semibold text-slate-900">Monthly collections (INR)</h2><p className="mt-1 text-sm text-slate-600">Bar height shows payments collected in each month.</p></div><span className="text-sm text-slate-600">Last 6 months</span></div>
        {revenue.isLoading ? <LoadingState /> : revenue.error ? <ErrorState message="Revenue data is unavailable." onRetry={() => void revenue.refetch()} /> : points.length === 0 ? <p className="mt-7 py-12 text-center text-slate-600">No monthly collection data for this period.</p> : <div role="img" aria-label="Monthly collections in Indian rupees for the last six months" className="mt-7 flex h-52 items-end gap-3 border-b border-slate-300 px-2">{points.map((point) => {
          const height = Number((cents(point.revenue_collected) * 100n) / max);
          return <div key={point.month} className="flex h-full flex-1 flex-col items-center justify-end gap-2"><div className="flex w-full flex-1 items-end"><div title={`${point.revenue_collected} INR collected`} className="w-full bg-indigo-700 transition-colors hover:bg-indigo-800" style={{ height: `${height}%`, minHeight: height > 0 ? 2 : 0 }} /></div><span className="pb-2 text-sm text-slate-600">{monthLabel(point.month)}</span></div>;
        })}</div>}
      </section>
      <section className="border-t-2 border-slate-300 bg-white p-5 sm:p-6">
        <div className="mb-4 flex items-center justify-between"><div><h2 className="font-semibold text-slate-900">Latest overdue</h2><p className="mt-1 text-xs text-slate-500">Invoices that need follow-up</p></div><a href="/invoices" className="text-sm font-medium text-indigo-700">View invoices</a></div>
        {overdue.isLoading ? <LoadingState /> : overdue.error ? <ErrorState message="Overdue invoices are unavailable." onRetry={() => void overdue.refetch()} /> : <DataTable rows={overdue.data ?? []} columns={overdueColumns} rowKey={(row) => row.invoice_id} page={1} pageSize={5} total={overdue.data?.length ?? 0} onPageChange={() => undefined} />}
      </section>
    </div>
    <section className="border-t-2 border-slate-300 bg-white p-5 sm:p-6"><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-lg font-semibold text-slate-900">Daily CFO brief</h2><button disabled={generateBrief.isPending} onClick={() => generateBrief.mutate()} className="min-h-11 rounded-sm border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 disabled:opacity-50">{generateBrief.isPending ? "Generating…" : "Generate now"}</button></div>{generateBrief.error && <p role="alert" className="mt-3 text-base text-rose-700">{generateBrief.error instanceof Error ? generateBrief.error.message : "Brief generation failed."}</p>}{brief.isLoading ? <p role="status" className="mt-4 text-base text-slate-600">Loading the latest brief…</p> : brief.error ? <p role="alert" className="mt-4 text-base text-slate-600">The brief is unavailable. Try generating one.</p> : brief.data ? <><p className="mt-4 text-base leading-7 text-slate-800">{brief.data.narrative}</p><p className="mt-3 text-sm text-slate-500">{brief.data.brief_date} · {brief.data.used_fallback ? "Deterministic fallback" : `${brief.data.provider ?? "AI"} · ${brief.data.model ?? ""}`}</p></> : <p className="mt-4 text-base text-slate-600">No daily brief yet. Generate one for today.</p>}</section>
    {user?.role === "admin" && <AdminJobsPanel />}
    <p className="text-xs text-slate-400">MRR normalizes recurring pre-tax line values: daily × 30, weekly × 52/12, monthly × 1, yearly ÷ 12.</p>
  </Screen>;
}

export const routes = [{ index: true, element: <RoleGuard roles={["admin", "staff"]}><DashboardPage /></RoleGuard> }];
