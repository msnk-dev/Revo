import { mockRequest } from "./mocks";

const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
const csrfMethods = new Set(["POST", "PUT", "PATCH", "DELETE"]);

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
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
