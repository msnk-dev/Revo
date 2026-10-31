import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { apiRequest } from "../../api/client";
import type { RevenuePoint, Summary } from "../../api/models";
import { DataTable, type Column } from "../../components/DataTable";
import { Money } from "../../components/Money";
import { ErrorState, LoadingState, MetricCard, Screen } from "../../components/Screen";
import { RoleGuard } from "../../app/RoleGuard";

function cents(value: string): bigint {
  const [whole, fraction = ""] = value.split(".");
  return BigInt(whole) * 100n + BigInt(fraction.padEnd(2, "0").slice(0, 2));
}

function monthLabel(value: string) {
  return new Intl.DateTimeFormat("en-IN", { month: "short" }).format(new Date(`${value}T00:00:00`));
}

function localIsoDate(value: Date) { return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`; }

function DashboardPage() {
  type OverdueRow = { invoice_id: number; invoice_number: string; customer_name: string; due_date: string; days_overdue: number; amount_due: string };
  type Brief = { brief_date: string; narrative: string; used_fallback: boolean; provider: string | null; model: string | null };
  const queryClient = useQueryClient();
  const today = new Date(); const end = localIsoDate(today); const yearStart = `${today.getFullYear()}-01-01`; const sixMonthStart = localIsoDate(new Date(today.getFullYear(), today.getMonth() - 5, 1));
  const summary = useQuery({ queryKey: ["reports", "summary", yearStart, end], queryFn: () => apiRequest<Summary>(`/reports/summary?${new URLSearchParams({ from: yearStart, to: end })}`), refetchInterval: 15_000 });
  const revenue = useQuery({ queryKey: ["reports", "revenue", sixMonthStart, end], queryFn: () => apiRequest<RevenuePoint[]>(`/reports/revenue?${new URLSearchParams({ from: sixMonthStart, to: end })}`) });
  const overdue = useQuery({ queryKey: ["reports", "overdue"], queryFn: () => apiRequest<OverdueRow[]>("/reports/overdue?limit=5"), refetchInterval: 15_000 });
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
    { key: "amount", header: "Amount due", render: (row) => <Money amount={row.amount_due} /> },
  ];

  return <Screen eyebrow="Overview" title="Dashboard" description="A live view of subscriptions, collections, and receivables.">
    {import.meta.env.VITE_USE_MOCKS === "true" && <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-900">Demo data is enabled. Values shown here come from local mock fixtures.</p>}
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
      <MetricCard label="Active subscriptions" value={summary.data.active_subscriptions} note={`${summary.data.paused_subscriptions} paused`} />
      <MetricCard label="MRR" value={<Money amount={summary.data.mrr} />} note="Pre-tax monthly equivalent" />
      <MetricCard label="Collected" value={<Money amount={summary.data.collected} />} note="Payments received" accent="emerald" />
      <MetricCard label="Outstanding" value={<Money amount={summary.data.outstanding} />} note="Confirmed invoices" accent="amber" />
      <MetricCard label="Overdue invoices" value={summary.data.overdue_count} note="Past due with balance remaining" accent="rose" />
    </div>
    <div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex items-center justify-between"><div><h2 className="font-semibold text-slate-900">Revenue trend</h2><p className="mt-1 text-xs text-slate-500">Collected payments by month</p></div><span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600">Last 6 months</span></div>
        {revenue.isLoading ? <LoadingState /> : revenue.error ? <ErrorState message="Revenue data is unavailable." onRetry={() => void revenue.refetch()} /> : <div className="mt-7 flex h-52 items-end gap-3 border-b border-slate-200 px-2">{points.map((point) => {
          const height = Number((cents(point.revenue_collected) * 100n) / max);
          return <div key={point.month} className="flex h-full flex-1 flex-col items-center justify-end gap-2"><div className="group relative flex w-full flex-1 items-end"><div title={`${point.revenue_collected} collected`} className="w-full rounded-t-md bg-indigo-500 transition hover:bg-indigo-600" style={{ height: `${Math.max(4, height)}%` }} /></div><span className="pb-2 text-xs text-slate-500">{monthLabel(point.month)}</span></div>;
        })}</div>}
        <div className="mt-3 flex items-center gap-2 text-xs text-slate-500"><span className="h-2.5 w-2.5 rounded-sm bg-indigo-500" />Collected</div>
      </section>
      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="mb-4 flex items-center justify-between"><div><h2 className="font-semibold text-slate-900">Latest overdue</h2><p className="mt-1 text-xs text-slate-500">Invoices that need follow-up</p></div><a href="/invoices" className="text-sm font-medium text-indigo-700">View invoices</a></div>
        {overdue.isLoading ? <LoadingState /> : overdue.error ? <ErrorState message="Overdue invoices are unavailable." onRetry={() => void overdue.refetch()} /> : <DataTable rows={overdue.data ?? []} columns={overdueColumns} rowKey={(row) => row.invoice_id} page={1} pageSize={5} total={overdue.data?.length ?? 0} onPageChange={() => undefined} />}
      </section>
    </div>
    <section className="rounded-xl border border-slate-200 bg-white p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">AI daily brief</p><h2 className="mt-1 font-semibold">CFO summary</h2></div><button disabled={generateBrief.isPending} onClick={() => generateBrief.mutate()} className="rounded-lg border border-indigo-200 px-3 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-50 disabled:opacity-50">{generateBrief.isPending ? "Generating…" : "Generate now"}</button></div>{generateBrief.error && <p role="alert" className="mt-3 text-sm text-rose-700">{generateBrief.error instanceof Error ? generateBrief.error.message : "Brief generation failed."}</p>}{brief.isLoading ? <p className="mt-4 text-sm text-slate-500">Loading the latest brief…</p> : brief.error ? <p className="mt-4 text-sm text-slate-500">The brief is unavailable. Try generating one.</p> : brief.data ? <><p className="mt-4 text-sm leading-6 text-slate-700">{brief.data.narrative}</p><p className="mt-3 text-xs text-slate-400">{brief.data.brief_date} · {brief.data.used_fallback ? "Deterministic fallback" : `${brief.data.provider ?? "AI"} · ${brief.data.model ?? ""}`}</p></> : <p className="mt-4 text-sm text-slate-500">No daily brief yet. Generate one for today.</p>}</section>
    <p className="text-xs text-slate-400">MRR normalizes recurring pre-tax line values: daily × 30, weekly × 52/12, monthly × 1, yearly ÷ 12.</p>
  </Screen>;
}

export const routes = [{ index: true, element: <RoleGuard roles={["admin", "staff"]}><DashboardPage /></RoleGuard> }];
