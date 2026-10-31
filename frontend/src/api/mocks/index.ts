export async function mockRequest<T>(path: string, _init?: RequestInit): Promise<T> {
  await new Promise((resolve) => setTimeout(resolve, 120));
  if (path === "/auth/me") return { id: 1, name: "Demo User", role: "admin" } as T;
  if (path.startsWith("/reports/summary")) return { active_subscriptions: 0, mrr: "0.00", collected: "0.00", outstanding: "0.00", overdue_count: 0 } as T;
  if (path.startsWith("/")) return { items: [], total: 0, page: 1, page_size: 20 } as T;
  throw new Error(`No mock configured for ${path}`);
}
