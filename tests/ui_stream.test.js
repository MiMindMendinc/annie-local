const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const code = fs.readFileSync('src/annie/ui/api-client.js', 'utf8');
function api(parts) {
  const window = { AnnieState: { get: () => ({}) } };
  const encoded = new TextEncoder().encode(parts);
  const stream = new ReadableStream({start(controller) {
    for (let i = 0; i < encoded.length; i += 7) controller.enqueue(encoded.slice(i, i + 7));
    controller.close();
  }});
  const context = {window, TextDecoder, Uint8Array, AbortController, DOMException, setTimeout, fetch: async () => new Response(stream, {headers: {'Content-Type':'text/event-stream'}})};
  vm.runInNewContext(code, context);
  return window.AnnieApi;
}
test('SSE parser assembles split UTF-8 frames and returns completion', async () => {
  const events = [];
  const result = await api('event: progress\ndata: {"phase":"generating"}\n\nevent: delta\ndata: {"text":"Café"}\n\nevent: done\ndata: {"reply":"Café"}\n\n').streamChat('Hello', null, (name, data) => events.push([name, data]));
  assert.equal(result.reply, 'Café');
  assert.equal(events[1][1].text, 'Café');
});
test('SSE parser rejects incomplete output', async () => {
  await assert.rejects(api('event: progress\ndata: {}\n\n').streamChat('Hello'), /before completion/);
});

test('cancel prevents buffered delta and done events from being delivered', async () => {
  const controller = new AbortController();
  const events = [];
  await assert.rejects(api('event: delta\ndata: {"text":"Hello"}\n\nevent: delta\ndata: {"text":"late"}\n\nevent: done\ndata: {"reply":"late"}\n\n').streamChat('Hi', controller.signal, (event) => {
    events.push(event);
    controller.abort();
  }), {name: 'AbortError'});
  assert.deepEqual(events, ['delta']);
});

test('done is terminal even if the connection stays open', async () => {
  let cancelled = false;
  const window = {AnnieState: {get: () => ({})}};
  const stream = new ReadableStream({
    start(controller) {controller.enqueue(new TextEncoder().encode('event: done\ndata: {"reply":"Ready"}\n\n'));},
    cancel() {cancelled = true;},
  });
  vm.runInNewContext(code, {window, TextDecoder, Uint8Array, DOMException, fetch: async () => new Response(stream)});
  assert.equal((await window.AnnieApi.streamChat('Hi')).reply, 'Ready');
  assert.equal(cancelled, true);
});
