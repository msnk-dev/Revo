import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiRequest } from "../api/client";
import { AuthProvider } from "./AuthContext";
import { RoleGuard } from "./RoleGuard";

vi.mock("../api/client", () => ({ apiRequest: vi.fn() }));
const mockApiRequest = vi.mocked(apiRequest);

describe("RoleGuard", () => {
  beforeEach(() => { mockApiRequest.mockReset(); });

  it("sends customer users to their portal when they open an internal route", async () => {
    mockApiRequest.mockImplementation(async () => ({ id: 2, name: "Customer", role: "customer", customer_id: 1 }) as never);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><MemoryRouter initialEntries={["/"]}><AuthProvider><Routes>
      <Route path="/" element={<RoleGuard roles={["admin", "staff"]}><p>Dashboard</p></RoleGuard>} />
      <Route path="/portal" element={<p>Portal destination</p>} />
    </Routes></AuthProvider></MemoryRouter></QueryClientProvider>);
    expect(await screen.findByText("Portal destination")).toBeInTheDocument();
  });

  it("keeps staff out of the admin-only catalog settings screen", async () => {
    mockApiRequest.mockImplementation(async () => ({ id: 3, name: "Staff", role: "staff", customer_id: null }) as never);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><MemoryRouter initialEntries={["/catalog"]}><AuthProvider><Routes>
      <Route path="/catalog" element={<RoleGuard roles={["admin"]}><p>Catalog settings</p></RoleGuard>} />
      <Route path="/" element={<p>Staff dashboard</p>} />
    </Routes></AuthProvider></MemoryRouter></QueryClientProvider>);
    expect(await screen.findByText("Staff dashboard")).toBeInTheDocument();
    expect(screen.queryByText("Catalog settings")).not.toBeInTheDocument();
  });
});
