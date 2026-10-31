import { describe, expect, it } from "vitest";
import { mockRequest } from "./index";
import type { Page } from "../types";
import type { SessionUser, Subscription } from "../models";

describe("demo API fixtures", () => {
  it("returns customer-scoped portal subscriptions after customer sign-in", async () => {
    const user = await mockRequest<SessionUser>("/auth/login", { method: "POST", body: JSON.stringify({ email: "customer@revo.local", password: "demo" }) });
    const result = await mockRequest<Page<Subscription>>("/portal/subscriptions?page=1&page_size=20");
    expect(user.role).toBe("customer");
    expect(result.items.every((item) => item.customer_id === user.customer_id)).toBe(true);
    expect(result.total).toBe(2);
  });
});
