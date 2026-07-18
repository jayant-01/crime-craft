import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { redirectToCatalystLogin } from "../auth/catalyst";
export default function LoginPage() {
    const { user, login, catalystMode } = useAuth();
    const navigate = useNavigate();
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState(null);
    const [submitting, setSubmitting] = useState(false);
    if (user)
        return _jsx(Navigate, { to: "/", replace: true });
    // Production: hand off to the Catalyst-hosted login page.
    if (catalystMode) {
        return (_jsx("div", { className: "min-h-screen flex items-center justify-center bg-brand-50", children: _jsxs("div", { className: "bg-card shadow rounded-lg p-8 w-full max-w-sm space-y-4 text-center", children: [_jsx("h1", { className: "text-xl font-semibold text-brand-700", children: "Crime Craft" }), _jsx("p", { className: "text-sm text-muted", children: "Sign in with your KSP account to continue." }), _jsx("button", { onClick: () => redirectToCatalystLogin(), className: "w-full rounded bg-brand-600 text-white py-2 font-medium hover:bg-brand-700", children: "Sign in" })] }) }));
    }
    async function onSubmit(e) {
        e.preventDefault();
        setError(null);
        setSubmitting(true);
        try {
            await login(username, password);
            navigate("/", { replace: true });
        }
        catch (err) {
            setError(err instanceof Error ? err.message : "login failed");
        }
        finally {
            setSubmitting(false);
        }
    }
    return (_jsx("div", { className: "min-h-screen flex items-center justify-center bg-brand-50", children: _jsxs("form", { onSubmit: onSubmit, className: "bg-card shadow rounded-lg p-8 w-full max-w-sm space-y-4", children: [_jsxs("div", { children: [_jsx("h1", { className: "text-xl font-semibold text-brand-700", children: "Crime Craft" }), _jsx("p", { className: "text-sm text-muted", children: "Sign in to continue." })] }), _jsxs("label", { className: "block text-sm", children: [_jsx("span", { className: "text-ink", children: "Username" }), _jsx("input", { value: username, onChange: (e) => setUsername(e.target.value), required: true, autoFocus: true, className: "mt-1 w-full rounded border-line border px-2 py-1.5" })] }), _jsxs("label", { className: "block text-sm", children: [_jsx("span", { className: "text-ink", children: "Password" }), _jsx("input", { type: "password", value: password, onChange: (e) => setPassword(e.target.value), required: true, className: "mt-1 w-full rounded border-line border px-2 py-1.5" })] }), error && _jsx("div", { className: "text-sm text-rose-600", children: error }), _jsx("button", { disabled: submitting, className: "w-full rounded bg-brand-600 text-white py-1.5 font-medium hover:bg-brand-700 disabled:opacity-50", children: submitting ? "Signing in…" : "Sign in" }), _jsxs("p", { className: "text-xs text-subtle leading-snug", children: ["Local-dev login stub. Try ", _jsx("code", { children: "officer_priya" }), ", ", _jsx("code", { children: "admin_jayant" }), ", or any other username \u2014 role is inferred from the prefix."] })] }) }));
}
