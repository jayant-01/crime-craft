import { jsx as _jsx, Fragment as _Fragment, jsxs as _jsxs } from "react/jsx-runtime";
import { Link, NavLink, Outlet } from "react-router-dom";
import { hasRole, useAuth } from "../auth/AuthContext";
import { useTheme } from "../theme/ThemeContext";
export default function Layout() {
    const { user, logout } = useAuth();
    return (_jsxs("div", { className: "min-h-screen flex flex-col", children: [_jsxs("header", { className: "bg-brand-700 text-white", children: [_jsxs("div", { className: "max-w-6xl mx-auto px-4 py-3 flex items-center gap-6", children: [_jsx(Link, { to: "/", className: "font-semibold text-lg", children: "Crime Craft" }), _jsxs("nav", { className: "flex gap-4 text-sm", children: [_jsx(NavTo, { to: "/cases", children: "Cases" }), _jsx(NavTo, { to: "/chat", children: "Chat" }), hasRole(user, "officer", "senior_officer", "admin") && (_jsxs(_Fragment, { children: [_jsx(NavTo, { to: "/dashboard", children: "Dashboard" }), _jsx(NavTo, { to: "/network", children: "Network" })] })), hasRole(user, "senior_officer", "admin") && (_jsx(NavTo, { to: "/recidivism", children: "Recidivism" }))] }), _jsxs("div", { className: "ml-auto text-sm flex items-center gap-3", children: [_jsx("span", { className: "text-brand-100", children: user?.email }), _jsx("span", { className: "rounded bg-brand-600 px-2 py-0.5 text-xs uppercase tracking-wide", children: user?.role }), _jsx(ThemeToggle, {}), _jsx("button", { onClick: logout, className: "underline hover:no-underline", children: "Logout" })] })] }), _jsx("div", { className: "flag-stripe" })] }), _jsx("main", { className: "flex-1 max-w-6xl w-full mx-auto px-4 py-6", children: _jsx(Outlet, {}) })] }));
}
function ThemeToggle() {
    const { theme, toggle } = useTheme();
    const dark = theme === "dark";
    return (_jsx("button", { onClick: toggle, "aria-label": dark ? "Switch to light theme" : "Switch to dark theme", title: dark ? "Light mode" : "Dark mode", className: "rounded p-1.5 text-brand-100 hover:text-white hover:bg-brand-600 transition", children: dark ? _jsx(SunIcon, {}) : _jsx(MoonIcon, {}) }));
}
function MoonIcon() {
    return (_jsx("svg", { width: "16", height: "16", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2", strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": "true", children: _jsx("path", { d: "M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" }) }));
}
function SunIcon() {
    return (_jsxs("svg", { width: "16", height: "16", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2", strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": "true", children: [_jsx("circle", { cx: "12", cy: "12", r: "4" }), _jsx("path", { d: "M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" })] }));
}
function NavTo({ to, children }) {
    return (_jsx(NavLink, { to: to, className: ({ isActive }) => `hover:text-white transition ${isActive ? "text-white font-medium" : "text-brand-100"}`, children: children }));
}
