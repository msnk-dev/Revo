import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "../../api/client";
import type { Payment } from "../../api/models";
import type { Page } from "../../api/types";
import { DataTable, type Column } from "../../components/DataTable";
import { Money } from "../../components/Money";
import { EmptyState, ErrorState, LoadingState, Screen } from "../../components/Screen";
import { RoleGuard } from "../../app/RoleGuard";

function PaymentsPage() {
  const [page, setPage] = useState(1); const pageSize = 10;
  const query = useQuery({ queryKey: ["payments", page], queryFn: () => apiRequest<Page<Payment>>(`/payments?page=${page}&page_size=${pageSize}`) });
  const columns: Column<Payment>[] = [
    { key: "date", header: "Paid on", render: (row) => new Date(`${row.paid_on}T00:00:00`).toLocaleDateString("en-IN") },
    { key: "invoice", header: "Invoice", render: (row) => <Link to={`/invoices/${row.invoice_id}`} className="font-semibold text-indigo-700">{row.invoice_number}</Link> },
    { key: "customer", header: "Customer", render: (row) => row.customer_name },
    { key: "method", header: "Method", render: (row) => <span className="capitalize">{row.method.replaceAll("_", " ")}</span> },
    { key: "note", header: "Note", render: (row) => row.note || "—" },
    { key: "amount", header: "Amount", render: (row) => <Money amount={row.amount} /> },
  ];
  return <Screen eyebrow="Billing" title="Payments" description="Recorded customer payments across invoices.">
    {query.isLoading ? <LoadingState label="Loading payments…" /> : query.error ? <ErrorState message="Could not load payments." onRetry={() => void query.refetch()} /> : (query.data?.total ?? 0) === 0 ? <EmptyState title="No payments recorded" description="Payments appear here once they have been recorded against an invoice." /> : <DataTable rows={query.data?.items ?? []} columns={columns} rowKey={(row) => row.id} page={page} pageSize={pageSize} total={query.data?.total ?? 0} onPageChange={setPage} />}
  </Screen>;
}

export const routes = [{ path: "payments", element: <RoleGuard roles={["admin", "staff"]}><PaymentsPage /></RoleGuard> }];
