import type { ReactNode } from "react";

export type Column<T> = { key: string; header: string; render: (row: T) => ReactNode; sortable?: boolean };
type DataTableProps<T> = { rows: T[]; columns: Column<T>[]; rowKey: (row: T) => string | number; page: number; pageSize: number; total: number; onPageChange: (page: number) => void; sort?: string; onSortChange?: (sort: string) => void; filters?: ReactNode };

export function DataTable<T>({ rows, columns, rowKey, page, pageSize, total, onPageChange, sort, onSortChange, filters }: DataTableProps<T>) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
    {filters && <div className="border-b border-slate-200 p-4">{filters}</div>}
    <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr>{columns.map((column) => <th key={column.key} className="px-4 py-3 font-medium">{column.sortable ? <button onClick={() => onSortChange?.(sort === column.key ? `-${column.key}` : column.key)}>{column.header}{sort === column.key ? " ↑" : sort === `-${column.key}` ? " ↓" : ""}</button> : column.header}</th>)}</tr></thead><tbody className="divide-y divide-slate-100">{rows.length ? rows.map((row) => <tr key={rowKey(row)} className="hover:bg-slate-50">{columns.map((column) => <td key={column.key} className="px-4 py-3">{column.render(row)}</td>)}</tr>) : <tr><td colSpan={columns.length} className="px-4 py-10 text-center text-slate-500">No records found</td></tr>}</tbody></table></div>
    <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3 text-sm text-slate-500"><span>{total === 0 ? "0 results" : `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, total)} of ${total}`}</span><div className="flex gap-2"><button disabled={page <= 1} onClick={() => onPageChange(page - 1)} className="rounded border px-3 py-1 disabled:opacity-40">Previous</button><button disabled={page >= pages} onClick={() => onPageChange(page + 1)} className="rounded border px-3 py-1 disabled:opacity-40">Next</button></div></div>
  </div>;
}
