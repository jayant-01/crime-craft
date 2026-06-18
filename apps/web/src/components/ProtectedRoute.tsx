import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { hasRole, useAuth } from "../auth/AuthContext";
import type { Role } from "../api/types";

interface Props {
  children: ReactNode;
  roles?: Role[];   // when set, restricts the route to these roles
}

export default function ProtectedRoute({ children, roles }: Props) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !hasRole(user, ...roles)) {
    return <div className="p-8 text-rose-600">Forbidden — your role can't access this page.</div>;
  }
  return <>{children}</>;
}
