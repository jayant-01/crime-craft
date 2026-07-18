import { jsx as _jsx, Fragment as _Fragment } from "react/jsx-runtime";
import { Navigate } from "react-router-dom";
import { hasRole, useAuth } from "../auth/AuthContext";
export default function ProtectedRoute({ children, roles }) {
    const { user } = useAuth();
    if (!user)
        return _jsx(Navigate, { to: "/login", replace: true });
    if (roles && !hasRole(user, ...roles)) {
        return _jsx("div", { className: "p-8 text-rose-600", children: "Forbidden \u2014 your role can't access this page." });
    }
    return _jsx(_Fragment, { children: children });
}
