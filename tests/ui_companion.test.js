"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const ui = path.join(__dirname, "..", "src", "annie", "ui");

// A small DOM port for interaction tests; this does not claim visual coverage.
class Element {
  constructor() {
    this.value = "";
    this.textContent = "";
    this.children = [];
    this.dataset = {};
    this.attributes = {};
    this.events = {};
  }
  set innerHTML(value) { throw new Error(`Unexpected HTML injection: ${value}`); }
  setAttribute(key, value) { this.attributes[key] = value; }
  addEventListener(type, handler) { this.events[type] = handler; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  focus() { this.focused = true; }
  async fire(type) { return this.events[type]?.({ preventDefault() {} }); }
}

function workspace(seed = {}) {
  const nodes = new Map([...fs.readFileSync(path.join(ui, "index.html"), "utf8").matchAll(/\bid="([^"]+)"/g)]
    .map((match) => [match[1], new Element()]));
  const elements = [...nodes.values()];
  const calls = [];
  let data = { profile: "", facts: [], goals: [], journal: [], ...seed };
  const api = {
    getKnowledge: async () => structuredClone(data),
    addKnowledge: async (kind, text) => {
      calls.push({ kind, text });
      if (kind === "goal") data.goals.push({ id: "added", text, done: false });
    },
    setGoalState: async (id, done) => {
      calls.push({ id, done });
      data.goals.find((goal) => goal.id === id).done = done;
    },
  };
  const document = {
    getElementById: (id) => { assert(nodes.has(id), `Missing HTML control ${id}`); return nodes.get(id); },
    createElement: () => { const node = new Element(); elements.push(node); return node; },
    querySelectorAll: (selector) => elements.filter((node) => (node.className || "").split(" ").includes(selector.slice(1))),
  };
  const window = {};
  const announcements = [];
  vm.runInNewContext(fs.readFileSync(path.join(ui, "companion.js"), "utf8"), { window, document, AnnieApi: api });
  const companion = window.AnnieCompanion.init({
    openDialog: (dialog) => { dialog.open = true; },
    closeDialog: (dialog) => { dialog.open = false; },
    inspectMemory() {},
    announce: (text) => announcements.push(text),
    autosize() {},
    requestPlan: async () => { calls.push({ mode: "plan", message: nodes.get("input").value }); nodes.get("input").value = ""; },
    connectModel: () => calls.push({ connect: true }),
  });
  companion.setRuntime({ model: { availability: "ready" } });
  return { companion, api, calls, announcements, get: (id) => nodes.get(id), setData: (next) => { data = next; } };
}

test("workspace renders stored notes as text and locks mutations when authentication is required", async () => {
  const w = workspace({ profile: "<img src=x onerror=alert(1)>", goals: [{ id: "g", text: "Build something", done: false }] });
  await w.companion.refresh();
  assert.equal(w.get("profilePreview").textContent, "<img src=x onerror=alert(1)>");
  w.companion.setLocked(true);
  assert.equal(w.get("addGoalBtn").disabled, true);
  w.get("goalInput").value = "Should not save";
  await w.get("goalForm").fire("submit");
  assert.equal(w.calls.length, 0);
});

test("failed saves preserve the goal draft and a retry saves once", async () => {
  const w = workspace();
  await w.companion.refresh();
  const save = w.api.addKnowledge;
  w.api.addKnowledge = async () => { throw new Error("Storage unavailable"); };
  w.get("goalInput").value = "Keep my draft";
  await w.get("goalForm").fire("submit");
  assert.equal(w.get("goalInput").value, "Keep my draft");
  assert.equal(w.get("todayNotice").dataset.tone, "bad");
  assert.equal(w.get("addGoalBtn").disabled, false);
  w.api.addKnowledge = save;
  await w.get("goalForm").fire("submit");
  assert.deepEqual(w.calls, [{ kind: "goal", text: "Keep my draft" }]);
  assert.equal(w.get("goalInput").value, "");
  assert.equal(w.get("goalCount").textContent, "1 open");
});

test("goal controls complete and reopen the selected goal without changing a duplicate", async () => {
  const w = workspace({ goals: [{ id: "one", text: "Same goal", done: false }, { id: "two", text: "Same goal", done: false }] });
  await w.companion.refresh();
  await w.get("goalList").children[1].children[0].fire("click");
  assert.deepEqual(w.calls, [{ id: "two", done: true }]);
  assert.equal(w.get("goalCount").textContent, "1 open");
  await w.get("completedList").children[0].children[0].fire("click");
  assert.deepEqual(w.calls[1], { id: "two", done: false });
  assert.equal(w.get("goalCount").textContent, "2 open");
});

test("planning sends the selected goals in planning mode and preserves an existing chat draft", async () => {
  const w = workspace({ goals: [{ id: "one", text: "Finish the prototype", done: false }] });
  await w.companion.refresh();
  await w.get("planDayBtn").fire("click");
  assert.match(w.calls[0].message, /Finish the prototype/);
  assert.equal(w.calls[0].mode, "plan");
  assert.equal(w.get("main").dataset.view, "chat");
  assert.equal(w.calls.length, 1);
  w.get("input").value = "A draft I am still writing";
  await w.get("unstickBtn").fire("click");
  assert.equal(w.get("input").value, "A draft I am still writing");
  assert.match(w.announcements.at(-1), /existing draft was kept/);
  assert.equal(w.calls.length, 1);
});

test("unavailable model blocks planning, keeps memory usable, and offers model settings", async () => {
  const w = workspace({ goals: [{ id: "one", text: "Build the prototype", done: false }] });
  await w.companion.refresh();
  w.companion.setRuntime({ model: { availability: "unavailable" } });
  assert.equal(w.get("modelSetup").hidden, false);
  assert.equal(w.get("planDayBtn").disabled, true);
  assert.equal(w.get("goalList").children[0].children[2].disabled, true);
  assert.equal(w.get("addGoalBtn").disabled, false);
  assert.equal(w.get("goalList").children[0].children[0].disabled, false);
  await w.get("planDayBtn").fire("click");
  assert.equal(w.calls.length, 0);
  await w.get("connectModelBtn").fire("click");
  assert.deepEqual(w.calls, [{ connect: true }]);
  w.companion.setRuntime({ model: { availability: "ready" } });
  assert.equal(w.get("modelSetup").hidden, true);
  assert.equal(w.get("planDayBtn").disabled, false);
});

test("capture errors keep the dialog and draft available", async () => {
  const w = workspace();
  await w.get("captureBtn").fire("click");
  w.get("captureText").value = "Remember this preference";
  w.api.addKnowledge = async () => { throw new Error("Save failed"); };
  await w.get("captureForm").fire("submit");
  assert.equal(w.get("captureDialog").open, true);
  assert.equal(w.get("captureText").value, "Remember this preference");
  assert.equal(w.get("captureError").hidden, false);
  assert.equal(w.get("captureSave").disabled, false);
});

test("failed refresh clears stale private context instead of presenting it as current", async () => {
  const w = workspace({ profile: "Stored profile", goals: [{ id: "one", text: "Stored goal", done: false }] });
  await w.companion.refresh();
  w.api.getKnowledge = async () => { throw new Error("Session expired"); };
  await assert.rejects(w.companion.refresh(), /Session expired/);
  assert.equal(w.get("goalList").children.length, 0);
  assert.equal(w.get("profilePreview").textContent, "Saved context could not be loaded.");
  assert.equal(w.get("planDayBtn").disabled, true);
});

test('repair hero uses server copy, gates plans, and leaves memory and drafts intact', async () => {
  const h = workspace();
  h.get('input').value = 'Keep this draft';
  h.companion.setRuntime({ model: { availability: 'unavailable', repair: {
    title: 'Choose the installed tag', detail: 'Configured llama3.2 at http://localhost:11434 is ambiguous.',
    actions: [{id:'retry',label:'Retry health now'},{id:'open_settings',label:'Choose installed model'},{id:'copy_pull',label:'Copy exact command',command:'ollama pull llama3.2'}]
  }}});
  assert.equal(h.get('repairTitle').textContent, 'Choose the installed tag');
  assert.match(h.get('repairDetail').textContent, /ambiguous/);
  assert.equal(h.get('retryHealthBtn').textContent, 'Retry health now');
  assert.equal(h.get('planDayBtn').attributes['aria-disabled'], 'true');
  assert.equal(h.get('unstickBtn').disabled, true);
  assert.equal(h.get('attachBtn').disabled, false);
  assert.equal(h.get('captureBtn').disabled, false);
  await h.get('retryHealthBtn').fire('click');
  assert.equal(h.get('input').value, 'Keep this draft');
  assert.equal(h.get('modelAvailabilityAnnouncement').textContent, 'Model offline. Memory still works.');
});
