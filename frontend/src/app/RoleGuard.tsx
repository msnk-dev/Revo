import { Navigate, Outlet } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth, type Role } from "./AuthContext";

export function RoleGuard({ roles, children }: { roles?: Role[]; children?: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-10 text-sm text-slate-500" role="status">Loading your workspace…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to={user.role === "customer" ? "/portal" : "/"} replace />;
  return children ?? <Outlet />;
}
