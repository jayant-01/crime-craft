import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import CasesPage from "./pages/CasesPage";
import CaseDetailPage from "./pages/CaseDetailPage";
import ChatPage from "./pages/ChatPage";
import DashboardPage from "./pages/DashboardPage";
import NetworkPage from "./pages/NetworkPage";
import RecidivismPage from "./pages/RecidivismPage";
import ProtectedRoute from "./components/ProtectedRoute";
import { useAuth } from "./auth/AuthContext";
export default function App() {
    const { loading } = useAuth();
    if (loading)
        return _jsx("div", { className: "p-8 text-muted", children: "Loading\u2026" });
    return (_jsxs(Routes, { children: [_jsx(Route, { path: "/login", element: _jsx(LoginPage, {}) }), _jsxs(Route, { element: _jsx(ProtectedRoute, { children: _jsx(Layout, {}) }), children: [_jsx(Route, { index: true, element: _jsx(Navigate, { to: "/cases", replace: true }) }), _jsx(Route, { path: "/cases", element: _jsx(CasesPage, {}) }), _jsx(Route, { path: "/cases/:id", element: _jsx(CaseDetailPage, {}) }), _jsx(Route, { path: "/chat", element: _jsx(ChatPage, {}) }), _jsx(Route, { path: "/dashboard", element: _jsx(ProtectedRoute, { roles: ["officer", "senior_officer", "admin"], children: _jsx(DashboardPage, {}) }) }), _jsx(Route, { path: "/network", element: _jsx(ProtectedRoute, { roles: ["officer", "senior_officer", "admin"], children: _jsx(NetworkPage, {}) }) }), _jsx(Route, { path: "/recidivism", element: _jsx(ProtectedRoute, { roles: ["senior_officer", "admin"], children: _jsx(RecidivismPage, {}) }) })] }), _jsx(Route, { path: "*", element: _jsx(Navigate, { to: "/", replace: true }) })] }));
}
