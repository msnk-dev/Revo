import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DataTable, type Column } from "./DataTable";

type Row = { id: number; number: string };
const columns: Column<Row>[] = [{ key: "number", header: "Invoice", sortable: true, render: (row) => row.number }];

describe("DataTable", () => {
  it("exposes server pagination and sort changes to its owner", () => {
    const onPageChange = vi.fn(); const onSortChange = vi.fn();
    render(<DataTable rows={[{ id: 1, number: "INV-1" }]} columns={columns} rowKey={(row) => row.id} page={1} pageSize={1} total={2} onPageChange={onPageChange} onSortChange={onSortChange} />);
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    fireEvent.click(screen.getByRole("button", { name: /Invoice/ }));
    expect(onPageChange).toHaveBeenCalledWith(2);
    expect(onSortChange).toHaveBeenCalledWith("number");
  });
});
