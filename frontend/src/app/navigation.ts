import type { Role } from "./AuthContext";

export type NavItem = { label: string; path: string; roles?: Role[] };
