import { mockRequest } from "./mocks";

const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
const csrfMethods = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export class ApiRequestError extends Error {
  constructor(message: string, readonly status: number, readonly details: Record<string, string> = {}) {
    super(message);
    this.name = "ApiRequestError";
  }
}

function errorDetails(value: unknown): Record<string, string> {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return Object.fromEntries(Object.entries(value).map(([key, detail]) => [
    key,
    typeof detail === "string" ? detail : detail instanceof Error ? detail.message : String(JSON.stringify(detail) ?? ""),
  ]));
}

function readCsrfCookie(): string | undefined {
  if (typeof document === "undefined") return undefined;
  const prefix = "csrf_token=";
  const cookie = document.cookie.split(";").map((part) => part.trim()).find((part) => part.startsWith(prefix));
  if (!cookie) return undefined;
  const value = cookie.slice(prefix.length);
  if (!value) return undefined;
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  if (import.meta.env.VITE_USE_MOCKS === "true") return mockRequest<T>(path, init);
  const method = (init?.method ?? "GET").toUpperCase();
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (csrfMethods.has(method)) {
    const csrfToken = readCsrfCookie();
    if (csrfToken) headers.set("X-CSRF-Token", csrfToken);
  }
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    let details: Record<string, string> = {};
    try {
      const payload = await response.json() as { error?: { message?: string; details?: unknown } };
      const error = payload.error;
      details = errorDetails(error?.details);
      message = error?.message ?? message;
    } catch {
      // Keep the HTTP status message when the server response is not JSON.
    }
    throw new ApiRequestError(message, response.status, details);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
