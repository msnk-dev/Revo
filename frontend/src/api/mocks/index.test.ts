import { describe, expect, it } from "vitest";
import { mockRequest } from "./index";
import type { Page } from "../types";
import type { SessionUser, Subscription } from "../models";

describe("demo API fixtures", () => {
  it("returns customer-scoped portal subscriptions after customer sign-in", async () => {
    const user = await mockRequest<SessionUser>("/auth/login", { method: "POST", body: JSON.stringify({ email: "customer@example.com", password: "demo" }) });
    const result = await mockRequest<Page<Subscription>>("/portal/subscriptions?page=1&page_size=20");
    expect(user.role).toBe("customer");
    expect(result.items.every((item) => item.customer_id === user.customer_id)).toBe(true);
    expect(result.total).toBe(3);
  });

  it("returns active subscriptions expiring in the next seven days", async () => {
    const result = await mockRequest<{ count: number; items: { subscription_id: number; number: string; customer_name: string; plan_name: string; expiry_date: string; days_remaining: number }[] }>("/reports/renewal-reminders");

    expect(result.count).toBe(1);
    expect(result.items).toEqual([{
      subscription_id: 3,
      number: "SUB-000003",
      customer_name: "Brightloop Demo",
      plan_name: "Annual Support",
      expiry_date: "2026-11-05",
      days_remaining: 5,
    }]);
  });
});
