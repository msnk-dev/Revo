import { Navigate, Outlet } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth, type Role } from "./AuthContext";

export function RoleGuard({ roles, children }: { roles?: Role[]; children?: ReactNode }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children ?? <Outlet />;
}
