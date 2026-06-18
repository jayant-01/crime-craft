import { Link, NavLink, Outlet } from "react-router-dom";
import { hasRole, useAuth } from "../auth/AuthContext";

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
            <button onClick={logout} className="underline hover:no-underline">Logout</button>
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
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
