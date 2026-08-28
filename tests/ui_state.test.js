"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "src", "annie", "ui", "state.js"), "utf8");

function loadState(seed = {}) {
  const values = new Map(Object.entries(seed));
  const localStorage = {
    getItem(key) {
      return values.has(key) ? values.get(key) : null;
    },
    setItem(key, value) {
      values.set(key, value);
    },
  };
  const sessionStorage = {
    getItem() {
      return null;
    },
    setItem() {},
  };
  const window = { localStorage, sessionStorage };
  vm.runInNewContext(source, { window, Set, Object, Array, JSON, Error });
  return { state: window.AnnieState, values };
}

test("new users start with spoken replies enabled", () => {
  const { state } = loadState();
  assert.equal(state.get("prefs").speak, true);
});

test("an existing speak false preference remains disabled", () => {
  const { state } = loadState({
    "annie5.prefs": JSON.stringify({ speak: false }),
  });
  assert.equal(state.get("prefs").speak, false);
});

test("partial saved preferences inherit the new speak default", () => {
  const { state } = loadState({
    "annie5.prefs": JSON.stringify({ rate: 1.1 }),
  });
  assert.equal(state.get("prefs").speak, true);
  assert.equal(state.get("prefs").rate, 1.1);
});

test("browser fallback immediately changes the visible output locality", () => {
  const { state } = loadState();
  state.dispatch("HEALTH_OK", {
    model: { availability: "ready" },
    voice: { output: "local_bridge", bridge_available: true },
  });
  state.dispatch("VOICE_FALLBACK");
  assert.equal(state.get("session").runtime.voice.output, "browser_managed_unverified");
  assert.equal(state.get("session").runtime.voice.bridge_available, true);
});
