"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { createDemoClient } = require("../src/annie/ui/demo.js");

function response(status, payload) {
  return { ok: status < 400, status, json: async () => payload, blob: async () => payload };
}

test("separate pages receive separate capabilities without cookies or URL tokens", async () => {
  const calls = [];
  let count = 0;
  const fetcher = async (url, options) => {
    calls.push({ url, options });
    return response(url === "/api/session" ? 201 : 200,
      url === "/api/session" ? { token: String(++count).repeat(43) } : { reply: "ok" });
  };
  const alice = createDemoClient(fetcher);
  const bob = createDemoClient(fetcher);
  await alice.start(); await bob.start();
  await alice.chat("Alice"); await bob.chat("Bob");
  assert.equal(calls[0].options.headers.Authorization, undefined);
  assert.equal(calls[1].options.headers.Authorization, undefined);
  assert.equal(calls[2].options.headers.Authorization, `Bearer ${"1".repeat(43)}`);
  assert.equal(calls[3].options.headers.Authorization, `Bearer ${"2".repeat(43)}`);
  for (const { url, options } of calls) {
    assert.equal(options.credentials, "omit");
    assert.equal(options.cache, "no-store");
    assert.equal(url.includes("?"), false);
    assert.equal(options.body.includes("token"), false);
  }
});

test("repeated start does not abandon the current temporary conversation", async () => {
  let calls = 0;
  const client = createDemoClient(async () => { calls += 1; return response(201, { token: "x".repeat(43) }); });
  await client.start(); await client.start();
  assert.equal(calls, 1);
});

test("expired chat is never replayed or silently assigned a new conversation", async () => {
  const paths = [];
  const client = createDemoClient(async (path) => {
    paths.push(path);
    return path === "/api/session" ? response(201, { token: "x".repeat(43) }) : response(401, { detail: "Conversation expired." });
  });
  await client.start();
  await assert.rejects(client.chat("keep my draft"), /expired/);
  assert.equal(client.hasSession(), false);
  await assert.rejects(client.chat("keep my draft"), /Start a new/);
  assert.deepEqual(paths, ["/api/session", "/api/chat"]);
});

test("network failures do not retry a chat POST", async () => {
  let chatCalls = 0;
  const client = createDemoClient(async (path) => {
    if (path === "/api/session") return response(201, { token: "x".repeat(43) });
    chatCalls += 1;
    throw new Error("Network failure");
  });
  await client.start();
  await assert.rejects(client.chat("hello"), /Network failure/);
  assert.equal(chatCalls, 1);
  assert.equal(client.hasSession(), true);
});

test("end chat revokes this page's capability and blocks later chat or speech", async () => {
  const calls = [];
  const client = createDemoClient(async (url, options) => {
    calls.push({ url, options });
    return response(200, { token: "x".repeat(43) });
  });
  await client.start(); await client.end();
  assert.equal(calls[1].options.method, "DELETE");
  assert.equal(calls[1].options.headers.Authorization, `Bearer ${"x".repeat(43)}`);
  assert.equal(client.hasSession(), false);
  await assert.rejects(client.chat("hello"), /Start a new/);
  await assert.rejects(client.speak("hello"), /Start a new/);
  assert.equal(calls.length, 2);
});

test("a failed end keeps the existing capability until deletion succeeds", async () => {
  let busy = true;
  const client = createDemoClient(async (url, options) => options.method === "DELETE"
    ? response(busy ? 409 : 200, { detail: "Reply still running" })
    : response(201, { token: "x".repeat(43) }));
  await client.start();
  await assert.rejects(client.end(), /still running/);
  assert.equal(client.hasSession(), true);
  busy = false;
  await client.end();
  assert.equal(client.hasSession(), false);
});
