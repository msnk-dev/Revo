import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

export type Role = "admin" | "staff" | "customer";
export type SessionUser = { id: number; name: string; role: Role };
type AuthValue = { user: SessionUser | null; setUser: (user: SessionUser | null) => void };

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null);
  const value = useMemo(() => ({ user, setUser }), [user]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
