import { Link, NavLink, Outlet } from "react-router-dom";
import { hasRole, useAuth } from "../auth/AuthContext";
import { useTheme } from "../theme/ThemeContext";

export default function Layout() {
  const { user, logout } = useAuth();
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-brand-700 text-white">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center gap-6">
          <Link to="/" className="font-semibold text-lg">Crime Craft</Link>
          <nav className="flex gap-4 text-sm">
            <NavTo to="/cases">Cases</NavTo>
            <NavTo to="/chat">Chat</NavTo>
            {hasRole(user, "officer", "senior_officer", "admin") && (
              <>
                <NavTo to="/dashboard">Dashboard</NavTo>
                <NavTo to="/network">Network</NavTo>
              </>
            )}
            {hasRole(user, "senior_officer", "admin") && (
              <NavTo to="/recidivism">Recidivism</NavTo>
            )}
          </nav>
          <div className="ml-auto text-sm flex items-center gap-3">
            <span className="text-brand-100">{user?.email}</span>
            <span className="rounded bg-brand-600 px-2 py-0.5 text-xs uppercase tracking-wide">
              {user?.role}
            </span>
            <ThemeToggle />
            <button onClick={logout} className="underline hover:no-underline">Logout</button>
          </div>
        </div>
        {/* national-flag tricolour accent */}
        <div className="flag-stripe" />
      </header>
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}

function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const dark = theme === "dark";
  return (
    <button
      onClick={toggle}
      aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
      title={dark ? "Light mode" : "Dark mode"}
      className="rounded p-1.5 text-brand-100 hover:text-white hover:bg-brand-600 transition"
    >
      {dark ? <SunIcon /> : <MoonIcon />}
    </button>
  );
}

function MoonIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
    </svg>
  );
}

function NavTo({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `hover:text-white transition ${isActive ? "text-white font-medium" : "text-brand-100"}`
      }
    >
      {children}
    </NavLink>
  );
}
