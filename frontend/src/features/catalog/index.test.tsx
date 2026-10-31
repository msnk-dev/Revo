import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiRequest } from "../../api/client";
import { AuthProvider } from "../../app/AuthContext";
import { routes } from "./index";

vi.mock("../../api/client", () => ({ apiRequest: vi.fn() }));
const mockApiRequest = vi.mocked(apiRequest);

const demoProduct = { id: 1, name: "Sample Cloud", type: "software", sales_price: "100.00", cost_price: "0.00", notes: null, default_tax_id: null, is_active: true };
const page = <T,>(items: T[]) => ({ items, total: items.length, page: 1, page_size: 100 });

function renderCatalog() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={["/catalog"]}><AuthProvider><Routes>
    <Route path="/catalog" element={routes[0].element} />
    <Route path="/" element={<p>Staff home</p>} />
  </Routes></AuthProvider></MemoryRouter></QueryClientProvider>);
}

describe("admin catalog settings", () => {
  beforeEach(() => {
    mockApiRequest.mockReset();
    mockApiRequest.mockImplementation(async (path, init) => {
      if (path === "/auth/me") return { id: 1, email: "admin@example.com", name: "Demo", role: "admin", customer_id: null } as never;
      if (path.startsWith("/products?page=1&page_size=100") || path.startsWith("/products?page=1&page_size=10")) return page([demoProduct]) as never;
      if (path.startsWith("/plans?page=1&page_size=100") || path.startsWith("/plans?page=1&page_size=10")) return page([]) as never;
      if (path.startsWith("/taxes?page=1&page_size=100") || path.startsWith("/taxes?page=1&page_size=10")) return page([]) as never;
      if (path === "/products/1/variants") return [] as never;
      if (init?.method === "POST") return { id: 2 } as never;
      return page([]) as never;
    });
  });

  it("creates an Odoo variant and a 10 percent minimum-quantity discount through the forms", async () => {
    renderCatalog();
    expect(await screen.findByRole("heading", { name: "Catalog settings" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Product variants" }));
    fireEvent.change(await screen.findByLabelText("Product"), { target: { value: "1" } });
    fireEvent.change(screen.getByLabelText("Attribute"), { target: { value: "Brand" } });
    fireEvent.change(screen.getByLabelText("Value"), { target: { value: "Odoo" } });
    fireEvent.change(screen.getByLabelText("Extra price"), { target: { value: "560.00" } });
    fireEvent.click(screen.getByRole("button", { name: "Add variant attribute" }));
    await waitFor(() => expect(mockApiRequest).toHaveBeenCalledWith("/products/1/variants", expect.objectContaining({
      method: "POST", body: JSON.stringify({ name: "Brand", values: [{ value: "Odoo", extra_price: "560.00" }] }),
    })));

    fireEvent.click(screen.getByRole("tab", { name: "Discounts" }));
    fireEvent.change(await screen.findByLabelText("Name"), { target: { value: "Seat saver" } });
    fireEvent.change(screen.getByLabelText("Percent off"), { target: { value: "10" } });
    fireEvent.change(screen.getByLabelText("Minimum quantity"), { target: { value: "5" } });
    fireEvent.click(screen.getByLabelText("Sample Cloud"));
    fireEvent.click(screen.getByRole("button", { name: "Add discount" }));
    await waitFor(() => expect(mockApiRequest).toHaveBeenCalledWith("/discounts", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ name: "Seat saver", type: "percent", value: "10", scope: "product", min_purchase: "0.00", min_quantity: 5, start_date: null, end_date: null, max_uses: null, product_ids: [1] }),
    })));
  });

});
