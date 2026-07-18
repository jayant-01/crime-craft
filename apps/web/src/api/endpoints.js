import { api, getToken } from "./client";
export const healthApi = {
    // Unauthenticated — tells the frontend whether the backend is in Catalyst mode.
    get() {
        return api.get("/health");
    },
};
export const authApi = {
    login(username, password) {
        const form = new FormData();
        form.set("username", username);
        form.set("password", password);
        return api.postForm("/auth/login", form);
    },
    me() {
        return api.get("/me");
    },
};
export const casesApi = {
    list() {
        return api.get("/cases");
    },
    get(id) {
        return api.get(`/cases/${encodeURIComponent(id)}`);
    },
};
export const chatApi = {
    send(req) {
        return api.post("/chat", req);
    },
};
export const conversationsApi = {
    create() {
        return api.post("/conversations");
    },
    list() {
        return api.get("/conversations");
    },
    get(id) {
        return api.get(`/conversations/${id}`);
    },
    delete(id) {
        return api.delete(`/conversations/${id}`);
    },
};
export const voiceApi = {
    transcribe(blob) {
        const form = new FormData();
        const ext = blob.type.includes("webm") ? "webm" : "wav";
        form.set("file", blob, `recording.${ext}`);
        return api.postForm("/voice/transcribe", form);
    },
    async tts(text, language) {
        const token = getToken();
        const res = await fetch("/api/voice/tts", {
            method: "POST",
            credentials: "include",
            headers: {
                "Content-Type": "application/json",
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: JSON.stringify({ text, language }),
        });
        if (!res.ok)
            throw new Error(`tts failed: ${res.status}`);
        return await res.blob();
    },
};
export const pdfApi = {
    exportConversation(id) {
        // Returns the URL — caller opens it in a new tab so the browser handles
        // the auth header via cookie/header injection done elsewhere.
        return `/api/conversations/${encodeURIComponent(id)}/export.pdf`;
    },
};
export const predictiveApi = {
    recidivism(req) {
        return api.post("/predictive/recidivism", req);
    },
};
export const networkApi = {
    forCase(caseId, depth = 1) {
        return api.get(`/network/case/${encodeURIComponent(caseId)}?depth=${depth}`);
    },
    forSuspect(name, depth = 1) {
        return api.get(`/network/suspect/${encodeURIComponent(name)}?depth=${depth}`);
    },
};
export const analyticsApi = {
    trends(params = {}) {
        const q = new URLSearchParams();
        Object.entries(params).forEach(([k, v]) => v && q.set(k, String(v)));
        return api.get(`/analytics/trends${q.size ? "?" + q : ""}`);
    },
    topLocalities(limit = 10) {
        return api.get(`/analytics/top-localities?limit=${limit}`);
    },
    hotspots(limit = 10, window_days = 30) {
        return api.get(`/analytics/hotspots?limit=${limit}&window_days=${window_days}`);
    },
};
