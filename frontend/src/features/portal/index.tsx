import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "../../api/client";
import type { Invoice, Payment, Subscription } from "../../api/models";
import type { Page } from "../../api/types";
import { DataTable, type Column } from "../../components/DataTable";
import { Money } from "../../components/Money";
import { StatusChip } from "../../components/StatusChip";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { EmptyState, ErrorState, LoadingState, Screen } from "../../components/Screen";
import { RoleGuard } from "../../app/RoleGuard";
import { useAuth } from "../../app/AuthContext";

type PortalSection = "subscriptions" | "invoices" | "payments";
type PlanOption = { id: number; name?: string; closable: boolean };

function PortalPage() {
  const { user } = useAuth();
  const [section, setSection] = useState<PortalSection>("subscriptions"); const [pageNumber, setPageNumber] = useState(1); const pageSize = 20;
  const [closeCandidate, setCloseCandidate] = useState<Subscription | null>(null); const [notice, setNotice] = useState(""); const queryClient = useQueryClient();
  const mockMode = import.meta.env.VITE_USE_MOCKS === "true";
  const result = useQuery({ queryKey: ["portal", section, pageNumber], queryFn: () => apiRequest<Page<Subscription | Invoice | Payment>>(`/portal/${section}?page=${pageNumber}&page_size=${pageSize}`) });
  const plans = useQuery({ queryKey: ["portal", "plans"], queryFn: () => apiRequest<Page<PlanOption>>("/plans?page=1&page_size=100"), enabled: section === "subscriptions" && !mockMode });
  const closeRequest = useMutation({ mutationFn: (subscription: Subscription) => apiRequest(`/subscriptions/${subscription.id}/close`, { method: "POST" }), onSuccess: async () => { setCloseCandidate(null); setNotice("The subscription has been closed."); await queryClient.invalidateQueries({ queryKey: ["portal", "subscriptions"] }); } });
  const tabs: { key: PortalSection; label: string }[] = [{ key: "subscriptions", label: "Subscriptions" }, { key: "invoices", label: "Invoices" }, { key: "payments", label: "Payments" }];
  let columns: Column<Subscription | Invoice | Payment>[] = [];
  if (section === "subscriptions") columns = [
    { key: "number", header: "Subscription", render: (row) => <span className="font-semibold">{(row as Subscription).number}</span> },
    { key: "plan", header: "Plan", render: (row) => { const sub = row as Subscription; return sub.plan_name ?? `Plan #${sub.plan_id}`; } },
    { key: "status", header: "Status", render: (row) => <div className="flex gap-2"><StatusChip status={(row as Subscription).status} />{(row as Subscription).is_paused && <StatusChip status="paused" />}</div> },
    { key: "next", header: "Next invoice", render: (row) => (row as Subscription).next_invoice_date ?? "—" },
    { key: "action", header: "Action", render: (row) => { const subscription = row as Subscription; const canClose = subscription.status === "active" && (subscription.closable ?? plans.data?.items.find((plan) => plan.id === subscription.plan_id)?.closable); return canClose ? <button onClick={() => setCloseCandidate(subscription)} className="text-sm font-semibold text-indigo-700 hover:underline">Close subscription</button> : "—"; } },
  ];
  if (section === "invoices") columns = [
    { key: "number", header: "Invoice", render: (row) => (row as Invoice).number },
    { key: "date", header: "Invoice date", render: (row) => (row as Invoice).invoice_date },
    { key: "due", header: "Due date", render: (row) => (row as Invoice).due_date },
    { key: "status", header: "Status", render: (row) => <StatusChip status={(row as Invoice).status} /> },
    { key: "total", header: "Total", align: "right", render: (row) => <Money amount={(row as Invoice).total} /> },
    { key: "pdf", header: "PDF", render: (row) => mockMode ? <button onClick={() => window.print()} className="font-medium text-indigo-700">Print / save PDF</button> : <a className="font-medium text-indigo-700" href={`${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1"}/portal/invoices/${(row as Invoice).id}/pdf`} target="_blank" rel="noreferrer">Open PDF</a> },
  ];
  if (section === "payments") columns = [
    { key: "date", header: "Paid on", render: (row) => (row as Payment).paid_on },
    { key: "invoice", header: "Invoice", render: (row) => { const payment = row as Payment; return payment.invoice_number ?? `Invoice #${payment.invoice_id}`; } },
    { key: "method", header: "Method", render: (row) => <span className="capitalize">{(row as Payment).method.replaceAll("_", " ")}</span> },
    { key: "amount", header: "Amount", align: "right", render: (row) => <Money amount={(row as Payment).amount} /> },
  ];
  return <Screen eyebrow="Customer portal" title="My account" description="Your subscriptions, invoices, and payment history.">
    <section className="bg-[#193b2b] px-5 py-5 text-white sm:px-7 sm:py-6"><h2 className="text-2xl font-semibold tracking-tight">Welcome, {user?.name ?? "customer"}</h2><p className="mt-2 text-base leading-6 text-white/80">Your account activity and documents, securely scoped to your profile.</p><p className="mt-4 text-sm text-white/70">{user?.email}</p></section>
    <div className="flex flex-wrap gap-x-6 border-b border-slate-300">{tabs.map((tab) => <button key={tab.key} onClick={() => { setSection(tab.key); setPageNumber(1); }} aria-current={section === tab.key ? "page" : undefined} className={`min-h-12 border-b-2 px-1 py-3 text-sm font-semibold transition-colors ${section === tab.key ? "border-indigo-700 text-indigo-800" : "border-transparent text-slate-600 hover:text-slate-900"}`}>{tab.label}</button>)}</div>
    {notice && <p role="status" className="rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-800">{notice}</p>}
    {closeRequest.error && <ErrorState message={closeRequest.error instanceof Error ? closeRequest.error.message : "Close request failed."} />}
    <div className="pt-2">{result.isLoading ? <LoadingState label={`Loading ${section}…`} /> : result.error ? <ErrorState message={`Could not load your ${section}.`} onRetry={() => void result.refetch()} /> : (result.data?.total ?? 0) === 0 ? <EmptyState title={`No ${section} yet`} description="Your account records will appear here when they are available." /> : <DataTable rows={result.data?.items ?? []} columns={columns} rowKey={(row) => row.id} page={pageNumber} pageSize={pageSize} total={result.data?.total ?? 0} onPageChange={setPageNumber} />}</div>
    <p className="text-xs text-slate-400">Portal data is requested through customer-scoped endpoints; the API must enforce ownership.</p>
    {mockMode && <p className="text-xs text-slate-400">Demo data is enabled.</p>}
    <ConfirmDialog open={Boolean(closeCandidate)} title="Close this subscription?" confirmLabel="Close subscription" onCancel={() => setCloseCandidate(null)} onConfirm={() => closeCandidate && closeRequest.mutate(closeCandidate)}>This will close {closeCandidate?.number} and stop future billing. The API checks the plan’s close policy.</ConfirmDialog>
  </Screen>;
}

export const routes = [{ path: "portal", element: <RoleGuard roles={["customer"]}><PortalPage /></RoleGuard> }];
