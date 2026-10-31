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

type PortalSection = "subscriptions" | "invoices" | "payments";

function PortalPage() {
  const [section, setSection] = useState<PortalSection>("subscriptions"); const [pageNumber, setPageNumber] = useState(1); const pageSize = 20;
  const [closeCandidate, setCloseCandidate] = useState<Subscription | null>(null); const [notice, setNotice] = useState(""); const queryClient = useQueryClient();
  const mockMode = import.meta.env.VITE_USE_MOCKS === "true";
  const result = useQuery({ queryKey: ["portal", section, pageNumber], queryFn: () => apiRequest<Page<Subscription | Invoice | Payment>>(`/portal/${section}?page=${pageNumber}&page_size=${pageSize}`) });
  const closeRequest = useMutation({ mutationFn: (subscription: Subscription) => apiRequest(`/subscriptions/${subscription.id}/close`, { method: "POST" }), onSuccess: async () => { setCloseCandidate(null); setNotice("Your close request was submitted."); await queryClient.invalidateQueries({ queryKey: ["portal", "subscriptions"] }); } });
  const tabs: { key: PortalSection; label: string }[] = [{ key: "subscriptions", label: "Subscriptions" }, { key: "invoices", label: "Invoices" }, { key: "payments", label: "Payments" }];
  let columns: Column<Subscription | Invoice | Payment>[] = [];
  if (section === "subscriptions") columns = [
    { key: "number", header: "Subscription", render: (row) => <span className="font-semibold">{(row as Subscription).number}</span> },
    { key: "plan", header: "Plan", render: (row) => (row as Subscription).plan_name },
    { key: "status", header: "Status", render: (row) => <div className="flex gap-2"><StatusChip status={(row as Subscription).status} />{(row as Subscription).is_paused && <StatusChip status="paused" />}</div> },
    { key: "next", header: "Next invoice", render: (row) => (row as Subscription).next_invoice_date ?? "—" },
    { key: "value", header: "Monthly value", render: (row) => <Money amount={(row as Subscription).monthly_value} /> },
    { key: "action", header: "Action", render: (row) => { const subscription = row as Subscription; return subscription.status === "active" && subscription.closable === true ? <button onClick={() => setCloseCandidate(subscription)} className="text-sm font-semibold text-indigo-700 hover:underline">Request close</button> : "—"; } },
  ];
  if (section === "invoices") columns = [
    { key: "number", header: "Invoice", render: (row) => (row as Invoice).number },
    { key: "date", header: "Invoice date", render: (row) => (row as Invoice).invoice_date },
    { key: "due", header: "Due date", render: (row) => (row as Invoice).due_date },
    { key: "status", header: "Status", render: (row) => <StatusChip status={(row as Invoice).status} /> },
    { key: "total", header: "Total", render: (row) => <Money amount={(row as Invoice).total} /> },
    { key: "pdf", header: "PDF", render: (row) => mockMode ? <button onClick={() => window.print()} className="font-medium text-indigo-700">Print / save PDF</button> : <a className="font-medium text-indigo-700" href={`${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1"}/portal/invoices/${(row as Invoice).id}/pdf`} target="_blank" rel="noreferrer">Open PDF</a> },
  ];
  if (section === "payments") columns = [
    { key: "date", header: "Paid on", render: (row) => (row as Payment).paid_on },
    { key: "invoice", header: "Invoice", render: (row) => (row as Payment).invoice_number },
    { key: "method", header: "Method", render: (row) => <span className="capitalize">{(row as Payment).method.replaceAll("_", " ")}</span> },
    { key: "amount", header: "Amount", render: (row) => <Money amount={(row as Payment).amount} /> },
  ];
  return <Screen eyebrow="Customer portal" title="My account" description="Your subscriptions, invoices, and payment history.">
    <div className="flex flex-wrap gap-2 border-b border-slate-200">{tabs.map((tab) => <button key={tab.key} onClick={() => { setSection(tab.key); setPageNumber(1); }} className={`rounded-t-lg px-4 py-2.5 text-sm font-medium ${section === tab.key ? "border-b-2 border-indigo-600 text-indigo-700" : "text-slate-500 hover:text-slate-800"}`}>{tab.label}</button>)}</div>
    {notice && <p role="status" className="rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-800">{notice}</p>}
    {closeRequest.error && <ErrorState message={closeRequest.error instanceof Error ? closeRequest.error.message : "Close request failed."} />}
    <div className="pt-2">{result.isLoading ? <LoadingState label={`Loading ${section}…`} /> : result.error ? <ErrorState message={`Could not load your ${section}.`} onRetry={() => void result.refetch()} /> : (result.data?.total ?? 0) === 0 ? <EmptyState title={`No ${section} yet`} description="Your account records will appear here when they are available." /> : <DataTable rows={result.data?.items ?? []} columns={columns} rowKey={(row) => row.id} page={pageNumber} pageSize={pageSize} total={result.data?.total ?? 0} onPageChange={setPageNumber} />}</div>
    <p className="text-xs text-slate-400">Portal data is requested through customer-scoped endpoints; the API must enforce ownership.</p>
    {mockMode && <p className="text-xs text-slate-400">Demo data is enabled.</p>}
    <ConfirmDialog open={Boolean(closeCandidate)} title="Request subscription closure?" confirmLabel="Submit request" onCancel={() => setCloseCandidate(null)} onConfirm={() => closeCandidate && closeRequest.mutate(closeCandidate)}>We’ll submit a request to close {closeCandidate?.number}. The API checks whether the plan allows closure.</ConfirmDialog>
  </Screen>;
}

export const routes = [{ path: "portal", element: <RoleGuard roles={["customer"]}><PortalPage /></RoleGuard> }];
