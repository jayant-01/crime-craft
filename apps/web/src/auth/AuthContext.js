import { jsx as _jsx } from "react/jsx-runtime";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { authApi, healthApi } from "../api/endpoints";
import { getToken, setToken } from "../api/client";
import { catalystSignOut } from "./catalyst";
const AuthCtx = createContext(null);
export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [catalystMode, setCatalystMode] = useState(false);
    useEffect(() => {
        (async () => {
            // Ask the backend whether it's in Catalyst mode (hosted login) or the
            // local dev JWT stub.
            let catalyst = false;
            try {
                catalyst = !!(await healthApi.get()).catalyst;
            }
            catch {
                /* health unreachable — assume dev */
            }
            setCatalystMode(catalyst);
            // Load the current user. In Catalyst mode the session rides on a cookie,
            // so we just try /me; in dev we only try if we hold a token.
            if (catalyst || getToken()) {
                try {
                    setUser(await authApi.me());
                }
                catch {
                    if (!catalyst)
                        setToken(null);
                }
            }
            setLoading(false);
        })();
    }, []);
    const login = useCallback(async (username, password) => {
        // Dev JWT stub only — in Catalyst mode LoginPage redirects to hosted login.
        const res = await authApi.login(username, password);
        setToken(res.access_token);
        const me = await authApi.me();
        setUser(me);
    }, []);
    const logout = useCallback(() => {
        setToken(null);
        setUser(null);
        if (catalystMode)
            catalystSignOut();
    }, [catalystMode]);
    const value = useMemo(() => ({ user, loading, catalystMode, login, logout }), [user, loading, catalystMode, login, logout]);
    return _jsx(AuthCtx.Provider, { value: value, children: children });
}
export function useAuth() {
    const ctx = useContext(AuthCtx);
    if (!ctx)
        throw new Error("useAuth must be used inside <AuthProvider>");
    return ctx;
}
export function hasRole(user, ...allowed) {
    return !!user && allowed.includes(user.role);
}
