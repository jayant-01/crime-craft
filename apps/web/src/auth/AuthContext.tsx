import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { authApi, healthApi } from "../api/endpoints";
import { getToken, setToken } from "../api/client";
import { catalystSignOut } from "./catalyst";
import type { Role, User } from "../api/types";

interface AuthState {
  user: User | null;
  loading: boolean;
  catalystMode: boolean;   // true in production → hosted Catalyst login
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthCtx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [catalystMode, setCatalystMode] = useState(false);

  useEffect(() => {
    (async () => {
      // Ask the backend whether it's in Catalyst mode (hosted login) or the
      // local dev JWT stub.
      let catalyst = false;
      try {
        catalyst = !!(await healthApi.get()).catalyst;
      } catch {
        /* health unreachable — assume dev */
      }
      setCatalystMode(catalyst);

      // Load the current user. In Catalyst mode the session rides on a cookie,
      // so we just try /me; in dev we only try if we hold a token.
      if (catalyst || getToken()) {
        try {
          setUser(await authApi.me());
        } catch {
          if (!catalyst) setToken(null);
        }
      }
      setLoading(false);
    })();
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    // Dev JWT stub only — in Catalyst mode LoginPage redirects to hosted login.
    const res = await authApi.login(username, password);
    setToken(res.access_token);
    const me = await authApi.me();
    setUser(me);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    if (catalystMode) catalystSignOut();
  }, [catalystMode]);

  const value = useMemo(
    () => ({ user, loading, catalystMode, login, logout }),
    [user, loading, catalystMode, login, logout],
  );
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

export function hasRole(user: User | null, ...allowed: Role[]) {
  return !!user && allowed.includes(user.role);
}
