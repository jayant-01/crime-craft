// Thin wrappers around the Catalyst Web SDK for hosted authentication.
// All usage is guarded so nothing runs (or errors) in local dev, where the SDK
// isn't present. In production the SDK is loaded from index.html.

interface CatalystAuth {
  signOut?: (redirectUrl: string) => void;
}
interface CatalystGlobal {
  auth?: CatalystAuth;
}

function catalyst(): CatalystGlobal | undefined {
  return (window as unknown as { catalyst?: CatalystGlobal }).catalyst;
}

// Catalyst-hosted login page (reserved path on the Catalyst domain).
export const CATALYST_LOGIN_URL = "/__catalyst/auth/login";

export function redirectToCatalystLogin(): void {
  window.location.href = CATALYST_LOGIN_URL;
}

export function catalystSignOut(): void {
  const auth = catalyst()?.auth;
  if (auth?.signOut) auth.signOut("/");
  else window.location.href = "/";
}
