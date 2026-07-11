import { api, getToken } from "./client";
import type {
  Case,
  ChatRequest,
  ChatResponse,
  Conversation,
  ConversationSummary,
  HotspotsResponse,
  LoginResponse,
  NetworkResponse,
  RecidivismRequest,
  RecidivismResponse,
  TopLocalitiesResponse,
  TranscribeResponse,
  TrendsResponse,
  User,
} from "./types";

export const healthApi = {
  // Unauthenticated — tells the frontend whether the backend is in Catalyst mode.
  get(): Promise<{ status: string; env: string; catalyst: boolean }> {
    return api.get("/health");
  },
};

export const authApi = {
  login(username: string, password: string): Promise<LoginResponse> {
    const form = new FormData();
    form.set("username", username);
    form.set("password", password);
    return api.postForm("/auth/login", form);
  },
  me(): Promise<User> {
    return api.get("/me");
  },
};

export const casesApi = {
  list(): Promise<Case[]> {
    return api.get("/cases");
  },
  get(id: string): Promise<Case> {
    return api.get(`/cases/${encodeURIComponent(id)}`);
  },
};

export const chatApi = {
  send(req: ChatRequest): Promise<ChatResponse> {
    return api.post("/chat", req);
  },
};

export const conversationsApi = {
  create(): Promise<Conversation> {
    return api.post("/conversations");
  },
  list(): Promise<ConversationSummary[]> {
    return api.get("/conversations");
  },
  get(id: string): Promise<Conversation> {
    return api.get(`/conversations/${id}`);
  },
  delete(id: string) {
    return api.delete(`/conversations/${id}`);
  },
};

export const voiceApi = {
  transcribe(blob: Blob): Promise<TranscribeResponse> {
    const form = new FormData();
    const ext = blob.type.includes("webm") ? "webm" : "wav";
    form.set("file", blob, `recording.${ext}`);
    return api.postForm("/voice/transcribe", form);
  },
  async tts(text: string, language: string): Promise<Blob> {
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
    if (!res.ok) throw new Error(`tts failed: ${res.status}`);
    return await res.blob();
  },
};

export const pdfApi = {
  exportConversation(id: string): string {
    // Returns the URL — caller opens it in a new tab so the browser handles
    // the auth header via cookie/header injection done elsewhere.
    return `/api/conversations/${encodeURIComponent(id)}/export.pdf`;
  },
};

export const predictiveApi = {
  recidivism(req: RecidivismRequest): Promise<RecidivismResponse> {
    return api.post("/predictive/recidivism", req);
  },
};

export const networkApi = {
  forCase(caseId: string, depth = 1): Promise<NetworkResponse> {
    return api.get(`/network/case/${encodeURIComponent(caseId)}?depth=${depth}`);
  },
  forSuspect(name: string, depth = 1): Promise<NetworkResponse> {
    return api.get(`/network/suspect/${encodeURIComponent(name)}?depth=${depth}`);
  },
};

export const analyticsApi = {
  trends(params: { granularity?: "week" | "month"; from_date?: string; to_date?: string; crime_type?: string; locality?: string } = {}): Promise<TrendsResponse> {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v && q.set(k, String(v)));
    return api.get(`/analytics/trends${q.size ? "?" + q : ""}`);
  },
  topLocalities(limit = 10): Promise<TopLocalitiesResponse> {
    return api.get(`/analytics/top-localities?limit=${limit}`);
  },
  hotspots(limit = 10, window_days = 30): Promise<HotspotsResponse> {
    return api.get(`/analytics/hotspots?limit=${limit}&window_days=${window_days}`);
  },
};
