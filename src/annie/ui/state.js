"use strict";

/**
 * Reactive UI state with pub/sub notifications.
 */
(function initAnnieState(global) {
  const listeners = new Map();

  function notify(key, value) {
    const subs = listeners.get(key);
    if (subs) {
      subs.forEach((fn) => fn(value));
    }
  }

  const store = {
    get(key, fallback) {
      try {
        const value = localStorage.getItem(`annie5.${key}`);
        return value ? JSON.parse(value) : fallback;
      } catch {
        return fallback;
      }
    },
    set(key, value) {
      try {
        localStorage.setItem(`annie5.${key}`, JSON.stringify(value));
      } catch {
        /* ignore quota errors */
      }
      notify(key, value);
    },
    subscribe(key, fn) {
      if (!listeners.has(key)) {
        listeners.set(key, new Set());
      }
      listeners.get(key).add(fn);
      return () => listeners.get(key)?.delete(fn);
    },
  };

  const state = {
    ui: store.get("ui", { speak: false, memory: true }),
    settings: {
      model: null,
      ollama_url: "http://127.0.0.1:11434",
      voice_url: "http://127.0.0.1:8123",
      temperature: 0.7,
      tools_enabled: true,
      default_doctrine: "",
    },
    auth: {
      token: store.get("auth.token", null),
      user: store.get("auth.user", null),
    },
    busy: false,
  };

  global.AnnieState = {
    get: (key) => state[key],
    set(key, value) {
      state[key] = value;
      if (key === "ui") {
        store.set("ui", value);
      }
      if (key === "auth") {
        store.set("auth.token", value?.token ?? null);
        store.set("auth.user", value?.user ?? null);
      }
      notify(key, value);
    },
    subscribe: store.subscribe,
    persistUi() {
      store.set("ui", state.ui);
    },
  };
})(window);
