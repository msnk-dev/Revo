import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiRequest } from "./client";

const fetchMock = vi.fn<typeof fetch>(async () => new Response(null, { status: 204 }));

function lastRequestHeaders() {
  const init = fetchMock.mock.calls.at(-1)?.[1];
  return new Headers(init?.headers);
}

describe("API client CSRF headers", () => {
  beforeEach(() => {
    vi.stubEnv("VITE_USE_MOCKS", "false");
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockClear();
    document.cookie = "csrf_token=csrf%2Bvalue; Path=/";
  });

  afterEach(() => {
    document.cookie = "csrf_token=; Max-Age=0; Path=/";
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it.each(["POST", "PUT", "PATCH", "DELETE"])("%s includes the decoded csrf_token cookie", async (method) => {
    await apiRequest("/resource", { method });

    expect(lastRequestHeaders().get("X-CSRF-Token")).toBe("csrf+value");
  });

  it.each(["GET", "HEAD", "OPTIONS"])("%s does not include a CSRF header", async (method) => {
    await apiRequest("/resource", { method });

    expect(lastRequestHeaders().has("X-CSRF-Token")).toBe(false);
  });

  it("preserves bearer authorization while adding the cookie token", async () => {
    await apiRequest("/resource", { method: "POST", headers: { Authorization: "Bearer session-token" } });

    expect(lastRequestHeaders().get("Authorization")).toBe("Bearer session-token");
    expect(lastRequestHeaders().get("X-CSRF-Token")).toBe("csrf+value");
  });

  it("does not add the header when the CSRF cookie is absent", async () => {
    document.cookie = "csrf_token=; Max-Age=0; Path=/";
    await apiRequest("/resource", { method: "POST" });

    expect(lastRequestHeaders().has("X-CSRF-Token")).toBe(false);
  });

  it("keeps mock requests on the mock layer", async () => {
    vi.stubEnv("VITE_USE_MOCKS", "true");
    await apiRequest("/auth/logout", { method: "POST" });

    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("retains field-level validation details from the API", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ error: { message: "Request validation failed", details: { name: "Field is required" } } }), { status: 422 }));

    await expect(apiRequest("/products", { method: "POST", body: "{}" })).rejects.toMatchObject({
      name: "ApiRequestError",
      status: 422,
      details: { name: "Field is required" },
    });
  });
});
