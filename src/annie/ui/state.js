"use strict";

/**
 * Small deterministic state machine for the Research Session interface.
 * Operational state is intentionally ephemeral; only user preferences and
 * authentication survive a reload.
 */
(function initAnnieState(global) {
  const ACTIVE_PHASES = new Set(["listening", "thinking", "speaking"]);
  const PHASES = Object.freeze(["idle", "listening", "thinking", "speaking", "offline", "error"]);
  const listeners = new Set();

  const storage = {
    get(key, fallback) {
      try {
        const value = global.localStorage.getItem(`annie5.${key}`);
        return value ? JSON.parse(value) : fallback;
      } catch {
        return fallback;
      }
    },
    set(key, value) {
      try {
        global.localStorage.setItem(`annie5.${key}`, JSON.stringify(value));
      } catch {
        // Private browsing and full storage quotas must not break the app.
      }
    },
  };

  const sessionStore = {
    get(key, fallback) {
      try {
        const value = global.sessionStorage.getItem(`annie5.${key}`);
        return value ? JSON.parse(value) : fallback;
      } catch {
        return fallback;
      }
    },
    set(key, value) {
      try {
        global.sessionStorage.setItem(`annie5.${key}`, JSON.stringify(value));
      } catch {
        // A blocked session store means the user signs in again after reload.
      }
    },
  };

  const defaultRuntime = () => ({
    api: "checking",
    model: { availability: "unknown", name: null, route: "unknown", locality: "unknown" },
    memory: {
      backend: "unknown",
      location: "unknown",
      conversation_persistence: "unknown",
      knowledge_tools: "unknown",
    },
    voice: {
      input: "browser_managed_unverified",
      output: "unknown",
      bridge_available: false,
      route: "unknown",
    },
    assets: { source: "bundled", remote_dependencies: false },
    network: {
      claim: "not_verified",
      reason: "Runtime status has not been checked yet.",
      offline_verified: false,
    },
  });

  const savedPrefs = storage.get("prefs", {});
  const initialPrefs = savedPrefs && typeof savedPrefs === "object" && !Array.isArray(savedPrefs)
    ? { speak: true, ...savedPrefs }
    : { speak: true };

  const state = {
    prefs: initialPrefs,
    settings: {
      model: null,
      ollama_url: "http://127.0.0.1:11434",
      voice_url: "http://127.0.0.1:8123",
      temperature: 0.7,
      tools_enabled: true,
      default_doctrine: "",
    },
    auth: {
      token: sessionStore.get("auth.token", null),
      user: sessionStore.get("auth.user", null),
    },
    session: {
      phase: "idle",
      canStop: false,
      runtime: defaultRuntime(),
      metrics: null,
      error: null,
    },
  };

  function snapshot() {
    return state;
  }

  function emit() {
    listeners.forEach((listener) => listener(snapshot()));
  }

  function setPhase(phase) {
    if (!PHASES.includes(phase)) {
      throw new Error(`Unknown Annie session phase: ${phase}`);
    }
    state.session.phase = phase;
    state.session.canStop = ACTIVE_PHASES.has(phase);
  }

  function restingPhase() {
    return state.session.runtime.model?.availability === "unavailable" ? "offline" : "idle";
  }

  function dispatch(event, payload = {}) {
    switch (event) {
      case "HEALTH_OK": {
        state.session.runtime = {
          ...defaultRuntime(),
          ...payload,
          api: "ready",
        };
        if (!ACTIVE_PHASES.has(state.session.phase)) {
          setPhase(restingPhase());
        }
        if (state.session.phase !== "error") {
          state.session.error = null;
        }
        break;
      }
      case "HEALTH_LOST":
        state.session.runtime = {
          ...state.session.runtime,
          api: "unavailable",
          model: { ...state.session.runtime.model, availability: "unavailable", repair: null },
        };
        if (!ACTIVE_PHASES.has(state.session.phase)) setPhase("offline");
        break;
      case "MIC_STARTED":
        state.session.error = null;
        setPhase("listening");
        break;
      case "MIC_ENDED":
        if (state.session.phase === "listening") setPhase(restingPhase());
        break;
      case "REQUEST_STARTED":
        state.session.error = null;
        state.session.metrics = null;
        setPhase("thinking");
        break;
      case "RESPONSE_READY":
        state.session.metrics = payload.metrics || null;
        break;
      case "RESPONSE_RENDERED":
        if (state.session.phase === "thinking") setPhase(restingPhase());
        break;
      case "SPEECH_STARTED":
        setPhase("speaking");
        break;
      case "SPEECH_ENDED":
        if (state.session.phase === "speaking" || state.session.phase === "thinking") {
          setPhase(restingPhase());
        }
        break;
      case "VOICE_FALLBACK":
        state.session.runtime = {
          ...state.session.runtime,
          voice: {
            ...state.session.runtime.voice,
            output: "browser_managed_unverified",
          },
        };
        break;
      case "STOPPED":
        state.session.error = null;
        setPhase(restingPhase());
        break;
      case "FAILED":
        state.session.error = {
          title: payload.title || "Something went wrong",
          detail: payload.detail || "Try again.",
        };
        setPhase("error");
        break;
      case "CLEAR_ERROR":
        state.session.error = null;
        setPhase(restingPhase());
        break;
      default:
        throw new Error(`Unknown Annie state event: ${event}`);
    }
    emit();
  }

  global.AnnieState = {
    PHASES,
    get: (key) => state[key],
    set(key, value) {
      state[key] = value;
      if (key === "auth") {
        sessionStore.set("auth.token", value?.token ?? null);
        sessionStore.set("auth.user", value?.user ?? null);
      }
      if (key === "prefs") storage.set("prefs", value);
      emit();
    },
    setPrefs(next) {
      state.prefs = { ...state.prefs, ...next };
      storage.set("prefs", state.prefs);
      emit();
    },
    dispatch,
    subscribe(listener) {
      listeners.add(listener);
      listener(snapshot());
      return () => listeners.delete(listener);
    },
  };
})(window);
