// Shared API client. All requests go through here so auth + error handling
// have one chokepoint.
const TOKEN_STORAGE_KEY = "cc.token";
export function getToken() {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
}
export function setToken(token) {
    if (token)
        localStorage.setItem(TOKEN_STORAGE_KEY, token);
    else
        localStorage.removeItem(TOKEN_STORAGE_KEY);
}
export class ApiError extends Error {
    status;
    detail;
    constructor(status, detail) {
        super(`${status}: ${detail}`);
        this.status = status;
        this.detail = detail;
    }
}
async function request(path, init = {}) {
    const token = getToken();
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    if (init.body && !headers.has("Content-Type") && !(init.body instanceof FormData)) {
        headers.set("Content-Type", "application/json");
    }
    if (token)
        headers.set("Authorization", `Bearer ${token}`);
    // `credentials: include` so the Catalyst session cookie (hosted login) is sent
    // to the API in production; harmless for the dev JWT-header flow.
    const res = await fetch(`/api${path}`, { ...init, headers, credentials: "include" });
    if (res.status === 401) {
        setToken(null);
        // Soft redirect — page handlers reading auth will route to login.
        throw new ApiError(401, "unauthorized");
    }
    if (!res.ok) {
        let detail = res.statusText;
        try {
            const body = await res.json();
            detail = body.detail ?? detail;
        }
        catch {
            /* keep statusText */
        }
        throw new ApiError(res.status, detail);
    }
    if (res.status === 204)
        return undefined;
    return (await res.json());
}
export const api = {
    get: (path) => request(path),
    post: (path, body) => request(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined }),
    postForm: (path, form) => request(path, { method: "POST", body: form }),
    delete: (path) => request(path, { method: "DELETE" }),
};
