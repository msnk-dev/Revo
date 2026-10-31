import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiRequest } from "../../api/client";
import { AuthProvider } from "../../app/AuthContext";
import { AssistantPage } from "./AssistantPanel";

vi.mock("../../api/client", () => ({ apiRequest: vi.fn() }));
const request = vi.mocked(apiRequest);

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}><AuthProvider><AssistantPage /></AuthProvider></QueryClientProvider>);
}

describe("AssistantPage", () => {
  beforeEach(() => {
    vi.stubEnv("VITE_USE_MOCKS", "false");
    request.mockReset();
    request.mockImplementation(async (path) => {
      if (path === "/auth/me") return { id: 1, name: "Admin", role: "admin", customer_id: null } as never;
      if (path === "/ai/brief/latest") return { brief_date: "2026-10-31", payload: {}, narrative: "Collected 50.00", used_fallback: true } as never;
      if (path === "/ai/brief/generate") return { brief_date: "2026-10-31", payload: {}, narrative: "Brief refreshed", used_fallback: false } as never;
      if (path === "/ai/chat") return { answer: "A reminder is ready.", thread_id: "thread-1", proposals: [{ id: "17", title: "Send reminder", description: "Send invoice reminder INV-1." }] } as never;
      if (path === "/ai/actions/17/confirm") return { id: 17, status: "sent", message: "Reminder sent" } as never;
      throw new Error(`Unexpected request ${String(path)}`);
    });
  });
  afterEach(() => { cleanup(); vi.unstubAllEnvs(); });

  it("renders the latest brief and refreshes it through the API", async () => {
    renderPage();
    expect(await screen.findByText("Collected 50.00")).toBeInTheDocument();
    expect(screen.getByText("Deterministic fallback")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Generate now" }));
    expect(await screen.findByText("Brief refreshed")).toBeInTheDocument();
    expect(request).toHaveBeenCalledWith("/ai/brief/generate", { method: "POST" });
  });

  it("requires explicit approval before confirming a proposed action", async () => {
    renderPage();
    const field = screen.getByLabelText("Message the assistant");
    fireEvent.change(field, { target: { value: "Draft a reminder" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText(/Approval required/)).toBeInTheDocument();
    expect(request).not.toHaveBeenCalledWith("/ai/actions/17/confirm", expect.anything());
    fireEvent.click(screen.getByRole("button", { name: "Approve and send" }));
    expect(await screen.findByText("sent")).toBeInTheDocument();
    await waitFor(() => expect(request).toHaveBeenCalledWith("/ai/actions/17/confirm", { method: "POST" }));
  });
});
