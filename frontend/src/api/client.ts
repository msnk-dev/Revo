import { mockRequest } from "./mocks";

const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
const useMocks = import.meta.env.VITE_USE_MOCKS === "true";

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  if (useMocks) return mockRequest<T>(path, init);
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    credentials: "include",
  });
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
