import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "../../api/client";
import type { Page } from "../../api/types";
import { DataTable, type Column } from "../../components/DataTable";
import { StatusChip } from "../../components/StatusChip";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { ErrorState, Screen, LoadingState, primaryButton } from "../../components/Screen";
import { RoleGuard } from "../../app/RoleGuard";

type StaffUser = { id: number; name: string | null; email: string; role: "admin" | "staff" | "customer"; is_active: boolean };
type StaffPage = Page<StaffUser>;
const pageSize = 10;

function StaffPageView() {
  const [page, setPage] = useState(1); const [name, setName] = useState(""); const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [formError, setFormError] = useState(""); const [deactivating, setDeactivating] = useState<StaffUser | null>(null);
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["staff", page], queryFn: () => apiRequest<StaffPage>(`/admin/staff?page=${page}&page_size=${pageSize}`) });
  const create = useMutation({ mutationFn: () => apiRequest<StaffUser>("/admin/staff", { method: "POST", body: JSON.stringify({ name, email, password }) }), onSuccess: async () => { setName(""); setEmail(""); setPassword(""); setFormError(""); await queryClient.invalidateQueries({ queryKey: ["staff"] }); }, onError: (reason) => setFormError(reason instanceof Error ? reason.message : "Could not create staff account.") });
  const deactivate = useMutation({ mutationFn: (staffId: number) => apiRequest<StaffUser>(`/admin/staff/${staffId}`, { method: "PATCH", body: JSON.stringify({ is_active: false }) }), onSuccess: async () => { setDeactivating(null); await queryClient.invalidateQueries({ queryKey: ["staff"] }); } });
  const columns = useMemo<Column<StaffUser>[]>(() => [
    { key: "name", header: "Team member", render: (row) => <span className="font-semibold text-slate-900">{row.name || "—"}</span> },
    { key: "email", header: "Email", render: (row) => <a href={`mailto:${row.email}`} className="text-indigo-700">{row.email}</a> },
    { key: "role", header: "Role", render: (row) => <span className="capitalize">{row.role}</span> },
    { key: "status", header: "Status", render: (row) => <StatusChip status={row.is_active ? "active" : "inactive"} /> },
    { key: "actions", header: "", render: (row) => row.is_active && row.role !== "admin" ? <button onClick={() => setDeactivating(row)} className="text-sm font-semibold text-rose-700 hover:underline">Deactivate</button> : null },
  ], []);
  return <Screen eyebrow="Workspace · Admin" title="Staff" description="Manage the people who can access the Revo workspace.">
    <section className="rounded-xl border border-slate-200 bg-white p-5"><h2 className="font-semibold">Invite a team member</h2><p className="mt-1 text-sm text-slate-500">New accounts receive the staff role. Share the temporary password through your team’s secure channel.</p><form className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4" onSubmit={(event) => { event.preventDefault(); setFormError(""); create.mutate(); }}><label className="text-sm font-medium text-slate-700">Name<input required maxLength={160} value={name} onChange={(e) => setName(e.target.value)} className="mt-1.5 block w-full rounded-lg border border-slate-300 px-3 py-2.5 font-normal" /></label><label className="text-sm font-medium text-slate-700">Email<input required type="email" maxLength={320} value={email} onChange={(e) => setEmail(e.target.value)} className="mt-1.5 block w-full rounded-lg border border-slate-300 px-3 py-2.5 font-normal" /></label><label className="text-sm font-medium text-slate-700">Temporary password<input required type="password" minLength={12} value={password} onChange={(e) => setPassword(e.target.value)} className="mt-1.5 block w-full rounded-lg border border-slate-300 px-3 py-2.5 font-normal" /></label><button disabled={create.isPending} className={`${primaryButton} self-end`}>{create.isPending ? "Creating…" : "Add staff"}</button></form>{formError && <p role="alert" className="mt-3 text-sm text-rose-700">{formError}</p>}</section>
    {deactivate.error && <ErrorState message={deactivate.error instanceof Error ? deactivate.error.message : "Could not deactivate staff account."} />}
    {query.isLoading ? <LoadingState label="Loading staff…" /> : query.error ? <ErrorState message="Could not load staff accounts." onRetry={() => void query.refetch()} /> : <DataTable rows={query.data?.items ?? []} columns={columns} rowKey={(row) => row.id} page={page} pageSize={pageSize} total={query.data?.total ?? 0} onPageChange={setPage} />}
    <ConfirmDialog open={Boolean(deactivating)} title={`Deactivate ${deactivating?.name || "this account"}?`} confirmLabel={deactivate.isPending ? "Deactivating…" : "Deactivate account"} onCancel={() => setDeactivating(null)} onConfirm={() => { if (deactivating) deactivate.mutate(deactivating.id); }}>This immediately revokes the account’s refresh sessions and removes workspace access.</ConfirmDialog>
  </Screen>;
}

export const routes = [{ path: "staff", element: <RoleGuard roles={["admin"]}><StaffPageView /></RoleGuard> }];
