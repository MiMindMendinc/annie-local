const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const code = fs.readFileSync('src/annie/ui/app.js', 'utf8');

function setup() {
  const cards = [];
  const committed = [];
  const spoken = [];
  let deliver;
  let finish;
  const response = new Promise(resolve => {finish = resolve;});
  const context = {
    AbortController, DOMException, abortController: null,
    el: {input: {value: 'Hello', focus() {}}, stream: {appendChild(card) {cards.push(card);}}, presenceCopy: {}},
    document: {createElement() {return {style: {}, textContent: '', setAttribute() {}, append(...children) {this.children = children;}, remove() {const i = cards.indexOf(this); if (i >= 0) cards.splice(i, 1);}};}},
    AnnieState: {get: () => ({phase: 'thinking', runtime: {model: {availability: 'ready'}}}), dispatch() {}},
    AnnieApi: {streamChat(text, signal, callback) {deliver = callback; return response;}},
    companion: null, autosize() {}, scrollToLatest() {}, announce() {},
    addMessage(role, content) {committed.push({role, content});},
    speakReply: async text => {spoken.push(text);},
    addSystemMessage() {}, addErrorCard() {}, refreshEngine: async () => {},
  };
  let phase = 'idle';
  context.AnnieState.get = () => ({phase, runtime: {model: {availability: 'ready'}}});
  context.AnnieState.dispatch = event => {if (event === 'REQUEST_STARTED') phase = 'thinking';};
  vm.createContext(context);
  vm.runInContext(code.slice(code.indexOf('function createReplyPreview'), code.indexOf('function addErrorCard')), context);
  vm.runInContext(code.slice(code.indexOf('async function sendMessage'), code.indexOf('function memoryGroup')), context);
  return {context, cards, committed, spoken, deliver: (...args) => deliver(...args), finish};
}

test('the real send handler renders deltas before done, then commits one final reply', async () => {
  const t = setup();
  const pending = t.context.sendMessage();
  t.deliver('delta', {text: 'Hello <script>'});
  assert.equal(t.cards.length, 1);
  assert.equal(t.cards[0].children[1].textContent, 'Hello <script>');
  assert.deepEqual(t.committed.map(x => x.role), ['user']);
  assert.deepEqual(t.spoken, []);
  t.deliver('reset', {});
  assert.equal(t.cards.length, 0);
  t.deliver('delta', {text: 'Final'});
  t.finish({reply: 'Final checked reply'});
  await pending;
  assert.equal(t.cards.length, 0);
  assert.deepEqual(t.committed.map(x => x.content), ['Hello', 'Final checked reply']);
  assert.deepEqual(t.spoken, ['Final checked reply']);
});

test('stop removes preview immediately and ignores a late successful completion', async () => {
  const t = setup();
  const pending = t.context.sendMessage();
  t.deliver('delta', {text: 'Hello'});
  t.context.abortController.abort();
  assert.equal(t.cards.length, 0);
  t.deliver('delta', {text: 'Late text'});
  t.finish({reply: 'Late reply'});
  await pending;
  assert.equal(t.cards.length, 0);
  assert.deepEqual(t.committed.map(x => x.role), ['user']);
  assert.deepEqual(t.spoken, []);
});

test('a late voice response after Stop starts neither audio nor browser fallback', async () => {
  let resolveVoice;
  const response = new Promise(resolve => {resolveVoice = resolve;});
  const events = [];
  const context = {
    AbortController, voiceAbortController: null, cleanVoiceText: text => text,
    AnnieState: {get: () => ({speak: true}), dispatch: event => events.push(event)},
    AnnieApi: {speak: () => response},
    playBridgeAudio: async () => events.push('play'),
    speakInBrowser: async () => events.push('fallback'), announce() {},
  };
  vm.createContext(context);
  vm.runInContext(code.slice(code.indexOf('async function speakReply'), code.indexOf('function stopCurrentActivity')), context);
  const request = new AbortController();
  const pending = context.speakReply('Checked reply', request.signal);
  request.abort();
  context.voiceAbortController.abort();
  resolveVoice({buffer: new ArrayBuffer(0), contentType: 'audio/wav'});
  await pending;
  assert.deepEqual(events, []);
});
