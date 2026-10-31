import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "../api/client";
import type { SessionUser } from "../api/models";

export type Role = "admin" | "staff" | "customer";
export type { SessionUser };
type AuthValue = {
  user: SessionUser | null;
  loading: boolean;
  setUser: (user: SessionUser | null) => void;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
};
type AuthResponse = { user_id?: number; id?: number; email?: string; name?: string; role: Role; customer_id: number | null };

function normalizeIdentity(identity: AuthResponse): SessionUser {
  const email = identity.email ?? identity.name ?? "user@revo.local";
  return { id: identity.user_id ?? identity.id ?? 0, name: identity.name ?? email, email, role: identity.role, customer_id: identity.customer_id };
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<SessionUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    apiRequest<AuthResponse | null>("/auth/me")
      .then((currentUser) => { if (active) setUser(currentUser ? normalizeIdentity(currentUser) : null); })
      .catch(() => { if (active) setUser(null); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const identity = await apiRequest<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    const nextUser = normalizeIdentity(identity);
    queryClient.clear();
    setUser(nextUser);
  }, [queryClient]);

  const signOut = useCallback(async () => {
    await apiRequest<void>("/auth/logout", { method: "POST" }).catch(() => undefined);
    queryClient.clear(); setUser(null);
  }, [queryClient]);

  const value = useMemo(() => ({ user, loading, setUser, signIn, signOut }), [user, loading, signIn, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
