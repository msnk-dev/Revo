export type Page<T> = { items: T[]; total: number; page: number; page_size: number };
export type ApiError = { error: { code: string; message: string; details?: unknown } };
