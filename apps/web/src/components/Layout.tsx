import { useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { hasRole, useAuth } from "../auth/AuthContext";
import { useTheme } from "../theme/ThemeContext";
import type { Role } from "../api/types";

interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
  roles?: Role[];
}

const NAV: NavItem[] = [
  { to: "/cases", label: "Cases", icon: <IconFolder /> },
  { to: "/map", label: "Crime Map", icon: <IconMap />, roles: ["officer", "senior_officer", "admin"] },
  { to: "/dashboard", label: "Dashboard", icon: <IconGrid />, roles: ["officer", "senior_officer", "admin"] },
  { to: "/network", label: "Network", icon: <IconNodes />, roles: ["officer", "senior_officer", "admin"] },
  { to: "/person", label: "People", icon: <IconUser />, roles: ["officer", "senior_officer", "admin"] },
  { to: "/recidivism", label: "Recidivism", icon: <IconAlert />, roles: ["senior_officer", "admin"] },
  { to: "/chat", label: "Assistant", icon: <IconChat /> },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const items = NAV.filter((n) => !n.roles || hasRole(user, ...n.roles));

  return (
    <div className="min-h-screen md:flex">
      {/* mobile top bar */}
      <div className="md:hidden sticky top-0 z-30 flex items-center justify-between bg-brand-700 text-white px-4 py-3">
        <Link to="/" className="font-semibold">Crime Craft</Link>
        <button onClick={() => setOpen((o) => !o)} aria-label="Menu" className="p-1.5 rounded hover:bg-white/10">
          <IconMenu />
        </button>
      </div>

      {/* sidebar */}
      <aside
        className={`${open ? "block" : "hidden"} md:flex md:sticky md:top-0 md:h-screen w-full md:w-64 shrink-0
                    flex-col bg-brand-700 text-white`}
      >
        <div className="px-5 pt-5 pb-4">
          <Link to="/" className="flex items-center gap-2" onClick={() => setOpen(false)}>
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-white/10 text-lg">🛡️</span>
            <div className="leading-tight">
              <div className="font-semibold">Crime Craft</div>
              <div className="text-[11px] text-brand-100/70">Karnataka State Police</div>
            </div>
          </Link>
        </div>
        <div className="flag-stripe mx-5 rounded" />

        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {items.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              onClick={() => setOpen(false)}
              className={({ isActive }) => `nav-link ${isActive ? "nav-link-active" : ""}`}
            >
              <span className="opacity-90">{n.icon}</span>
              {n.label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-white/10 p-3">
          <div className="flex items-center gap-2 rounded-lg px-2 py-1.5">
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-white/15 text-sm font-semibold">
              {(user?.email ?? "?")[0]?.toUpperCase()}
            </span>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm">{user?.email}</div>
              <div className="text-[11px] uppercase tracking-wide text-brand-100/70">{user?.role}</div>
            </div>
            <ThemeToggle />
          </div>
          <button onClick={logout} className="mt-1 w-full nav-link justify-start">
            <IconLogout /> Sign out
          </button>
        </div>
      </aside>

      {/* main */}
      <div className="flex-1 min-w-0">
        <main className="mx-auto max-w-6xl px-4 py-6 md:px-8 md:py-8">
          <PageHeader />
          <div className="fade-in">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

const TITLES: Record<string, string> = {
  "/cases": "Cases",
  "/map": "Crime Map",
  "/dashboard": "Dashboard",
  "/network": "Criminal Network",
  "/person": "Person Dossier",
  "/recidivism": "Recidivism Scoring",
  "/chat": "Assistant",
};

function PageHeader() {
  const { pathname } = useLocation();
  const key = Object.keys(TITLES).find((k) => pathname.startsWith(k));
  if (!key) return null;
  return <h1 className="mb-5 text-xl font-semibold tracking-tight text-ink">{TITLES[key]}</h1>;
}

function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const dark = theme === "dark";
  return (
    <button
      onClick={toggle}
      aria-label={dark ? "Light mode" : "Dark mode"}
      className="rounded-md p-1.5 text-brand-100/80 hover:text-white hover:bg-white/10 transition"
    >
      {dark ? <IconSun /> : <IconMoon />}
    </button>
  );
}

/* --- icons (inline, currentColor) --- */
function svg(children: React.ReactNode) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{children}</svg>
  );
}
function IconFolder() { return svg(<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />); }
function IconMap() { return svg(<><path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2z" /><path d="M9 4v14M15 6v14" /></>); }
function IconGrid() { return svg(<><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>); }
function IconNodes() { return svg(<><circle cx="6" cy="6" r="2.5" /><circle cx="18" cy="6" r="2.5" /><circle cx="12" cy="18" r="2.5" /><path d="M7.7 7.6 10.5 16M16.3 7.6 13.5 16M8 6h8" /></>); }
function IconAlert() { return svg(<><path d="M12 3 2 20h20L12 3z" /><path d="M12 9v5M12 17h.01" /></>); }
function IconChat() { return svg(<path d="M21 15a2 2 0 0 1-2 2H8l-4 4V5a2 2 0 0 1 2-2h13a2 2 0 0 1 2 2z" />); }
function IconUser() { return svg(<><circle cx="12" cy="8" r="3.5" /><path d="M4.5 20a7.5 7.5 0 0 1 15 0" /></>); }
function IconLogout() { return svg(<><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><path d="M16 17l5-5-5-5M21 12H9" /></>); }
function IconMenu() { return svg(<path d="M4 6h16M4 12h16M4 18h16" />); }
function IconMoon() { return svg(<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />); }
function IconSun() { return svg(<><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>); }
