import { jsx as _jsx } from "react/jsx-runtime";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
const ThemeCtx = createContext(null);
function getInitialTheme() {
    try {
        const saved = localStorage.getItem("theme");
        if (saved === "light" || saved === "dark")
            return saved;
        if (window.matchMedia("(prefers-color-scheme: dark)").matches)
            return "dark";
    }
    catch {
        /* localStorage/matchMedia unavailable — fall through to light */
    }
    return "light";
}
export function ThemeProvider({ children }) {
    const [theme, setTheme] = useState(getInitialTheme);
    useEffect(() => {
        const root = document.documentElement;
        root.classList.toggle("dark", theme === "dark");
        try {
            localStorage.setItem("theme", theme);
        }
        catch {
            /* ignore persistence failures (private mode, etc.) */
        }
    }, [theme]);
    const toggle = useCallback(() => setTheme((t) => (t === "light" ? "dark" : "light")), []);
    return _jsx(ThemeCtx.Provider, { value: { theme, toggle }, children: children });
}
export function useTheme() {
    const ctx = useContext(ThemeCtx);
    if (!ctx)
        throw new Error("useTheme must be used inside <ThemeProvider>");
    return ctx;
}
