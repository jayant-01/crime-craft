// Thin wrappers around the Catalyst Web SDK for hosted authentication.
// All usage is guarded so nothing runs (or errors) in local dev, where the SDK
// isn't present. In production the SDK is loaded from index.html.
function catalyst() {
    return window.catalyst;
}
// Catalyst-hosted login page (reserved path on the Catalyst domain).
export const CATALYST_LOGIN_URL = "/__catalyst/auth/login";
export function redirectToCatalystLogin() {
    window.location.href = CATALYST_LOGIN_URL;
}
export function catalystSignOut() {
    const auth = catalyst()?.auth;
    if (auth?.signOut)
        auth.signOut("/");
    else
        window.location.href = "/";
}
