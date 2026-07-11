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

  // Production: hand off to the Catalyst-hosted login page.
  if (catalystMode) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-brand-50">
        <div className="bg-card shadow rounded-lg p-8 w-full max-w-sm space-y-4 text-center">
          <h1 className="text-xl font-semibold text-brand-700">Crime Craft</h1>
          <p className="text-sm text-muted">Sign in with your KSP account to continue.</p>
          <button
            onClick={() => redirectToCatalystLogin()}
            className="w-full rounded bg-brand-600 text-white py-2 font-medium hover:bg-brand-700"
          >
            Sign in
          </button>
        </div>
      </div>
    );
  }

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
    <div className="min-h-screen flex items-center justify-center bg-brand-50">
      <form onSubmit={onSubmit} className="bg-card shadow rounded-lg p-8 w-full max-w-sm space-y-4">
        <div>
          <h1 className="text-xl font-semibold text-brand-700">Crime Craft</h1>
          <p className="text-sm text-muted">Sign in to continue.</p>
        </div>
        <label className="block text-sm">
          <span className="text-ink">Username</span>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoFocus
            className="mt-1 w-full rounded border-line border px-2 py-1.5"
          />
        </label>
        <label className="block text-sm">
          <span className="text-ink">Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="mt-1 w-full rounded border-line border px-2 py-1.5"
          />
        </label>
        {error && <div className="text-sm text-rose-600">{error}</div>}
        <button
          disabled={submitting}
          className="w-full rounded bg-brand-600 text-white py-1.5 font-medium hover:bg-brand-700 disabled:opacity-50"
        >
          {submitting ? "Signing in…" : "Sign in"}
        </button>
        <p className="text-xs text-subtle leading-snug">
          Local-dev login stub. Try <code>officer_priya</code>, <code>admin_jayant</code>, or any other
          username — role is inferred from the prefix.
        </p>
      </form>
    </div>
  );
}
