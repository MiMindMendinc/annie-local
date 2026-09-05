"use strict";

/**
 * Robust API client: JWT auth, retries, structured errors.
 */
(function initApiClient(global) {
  const MAX_RETRIES = 3;
  const BASE_DELAY_MS = 400;

  function sleep(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  function authHeaders() {
    const auth = global.AnnieState?.get("auth");
    const headers = { "Content-Type": "application/json" };
    if (auth?.token) {
      headers.Authorization = `Bearer ${auth.token}`;
    }
    return headers;
  }

  async function request(path, options = {}) {
    const method = options.method || "GET";
    const hadToken = Boolean(global.AnnieState?.get("auth")?.token);
    // Retrying a completed POST can duplicate chat turns or destructive
    // actions. Only idempotent reads retry unless the caller opts in.
    const retries = options.retries ?? (method === "GET" ? MAX_RETRIES : 1);
    let lastError = null;

    for (let attempt = 0; attempt < retries; attempt += 1) {
      try {
        const response = await fetch(path, {
          method,
          headers: { ...authHeaders(), ...(options.headers || {}) },
          body: options.body ? JSON.stringify(options.body) : undefined,
          signal: options.signal,
          cache: "no-store",
        });

        if (response.status === 429 && attempt < retries - 1) {
          await sleep(BASE_DELAY_MS * 2 ** attempt);
          continue;
        }

        const contentType = response.headers.get("content-type") || "";
        const isJson = contentType.includes("application/json");
        const payload = isJson ? await response.json() : await response.blob();

        if (!response.ok) {
          if (response.status === 401 && path !== "/api/auth/login") {
            global.dispatchEvent(new CustomEvent("annie:auth-required", { detail: { hadToken } }));
          }
          const detail = isJson ? payload.detail || payload.error : response.statusText;
          const err = new Error(typeof detail === "string" ? detail : "request failed");
          err.status = response.status;
          err.payload = payload;
          throw err;
        }
        return payload;
      } catch (error) {
        lastError = error;
        if (error.name === "AbortError") {
          throw error;
        }
        if (attempt < retries - 1) {
          await sleep(BASE_DELAY_MS * 2 ** attempt);
          continue;
        }
      }
    }
    throw lastError || new Error("request failed");
  }

  global.AnnieApi = {
    health: () => request("/api/health"),
    getSettings: () => request("/api/settings"),
    updateSettings: (body) => request("/api/settings", { method: "PUT", body }),
    resetDoctrine: () => request("/api/settings/reset-doctrine", { method: "POST" }),
    chat: (message, signal) => request("/api/chat", { method: "POST", body: { message }, signal, retries: 1 }),
    restartSession: () => request("/api/session/restart", { method: "POST" }),
    getKnowledge: () => request("/api/knowledge"),
    addKnowledge: (kind, text) => request("/api/knowledge", { method: "POST", body: { kind, text } }),
    setGoalState: (id, done) => request(`/api/knowledge/goals/${encodeURIComponent(id)}`, { method: "PATCH", body: { done } }),
    deleteKnowledge: () => request("/api/knowledge", { method: "DELETE" }),
    deleteKnowledgeItem: (kind, item_id) =>
      request("/api/knowledge/delete", { method: "POST", body: { kind, item_id } }),
    speak: async (text, signal) => {
      const response = await fetch("/api/voice/speak", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ text }),
        signal,
      });
      if (!response.ok) {
        throw new Error("voice request failed");
      }
      return {
        buffer: await response.arrayBuffer(),
        contentType: response.headers.get("content-type") || "audio/wav",
      };
    },
    login: async (email, password) => {
      const data = await request("/api/auth/login", { method: "POST", body: { email, password } });
      global.AnnieState.set("auth", { token: data.access_token, user: data.user });
      return data;
    },
    register: async (email, password) => {
      const data = await request("/api/auth/register", { method: "POST", body: { email, password } });
      global.AnnieState.set("auth", { token: data.access_token, user: data.user });
      return data;
    },
  };
})(window);
