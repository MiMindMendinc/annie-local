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
  const context = {window, TextDecoder, Uint8Array, AbortController, setTimeout, fetch: async () => new Response(stream, {headers: {'Content-Type':'text/event-stream'}})};
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
