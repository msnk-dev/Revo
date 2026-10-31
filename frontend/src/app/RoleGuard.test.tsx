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
});
