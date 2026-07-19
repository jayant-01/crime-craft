import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { redirectToCatalystLogin } from "../auth/catalyst";

export default function LoginPage() {
  const { user, login, catalystMode } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen grid md:grid-cols-2">
      {/* brand panel */}
      <div className="hidden md:flex flex-col justify-between bg-brand-700 text-white p-10">
        <div className="flex items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-white/10 text-lg">🛡️</span>
          <span className="font-semibold">Crime Craft</span>
        </div>
        <div>
          <h1 className="text-3xl font-semibold leading-tight">Intelligent case insights<br />for Karnataka State Police</h1>
          <p className="mt-3 max-w-md text-brand-100/80">
            Chat, analytics, criminal-network mapping and recidivism scoring — role-aware and audit-logged.
          </p>
        </div>
        <div className="flag-stripe w-40 rounded" />
      </div>

      {/* form panel */}
      <div className="flex items-center justify-center bg-surface p-6">
        <div className="card card-pad w-full max-w-sm fade-in">
          <div className="mb-6 md:hidden flex items-center gap-2">
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-brand-600 text-white text-lg">🛡️</span>
            <span className="font-semibold text-ink">Crime Craft</span>
          </div>
          <h2 className="text-lg font-semibold text-ink">Sign in</h2>
          <p className="mt-1 text-sm text-muted">
            {catalystMode ? "Continue with your KSP account." : "Local demo — role is inferred from the username prefix."}
          </p>

          {catalystMode ? (
            <button onClick={() => redirectToCatalystLogin()} className="btn btn-primary w-full mt-6">
              Sign in with KSP account
            </button>
          ) : (
            <form onSubmit={onSubmit} className="mt-6 space-y-4">
              <label className="block">
                <span className="text-xs font-medium text-muted">Username</span>
                <input value={username} onChange={(e) => setUsername(e.target.value)} required autoFocus
                  placeholder="senior_jayant" className="input mt-1" />
              </label>
              <label className="block">
                <span className="text-xs font-medium text-muted">Password</span>
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
                  placeholder="any value" className="input mt-1" />
              </label>
              {error && <div className="text-sm text-rose-600">{error}</div>}
              <button disabled={submitting} className="btn btn-primary w-full">
                {submitting ? "Signing in…" : "Sign in"}
              </button>
              <p className="text-xs text-subtle leading-snug">
                Try <code className="chip">senior_jayant</code>, <code className="chip">officer_priya</code>, or
                <code className="chip">admin_ravi</code>.
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
