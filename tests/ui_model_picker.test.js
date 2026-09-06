const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('src/annie/ui/app.js', 'utf8');

function harness(installed) {
  const nodes = { '#modelHint': {}, '#installedModels': { children: [], replaceChildren() { this.children = []; }, appendChild(n) { this.children.push(n); } }, '#saveMissingModel': { checked: false, focus() {} } };
  const el = { model: { value: 'llama3.2' }, ollamaUrl: { value: 'http://localhost:11434' }, voiceUrl: { value: 'http://localhost:8123' }, temp: { value: '.7' }, toolsToggle: { checked: true }, sys: { value: '' }, speakToggle: { checked: false } };
  let saved = 0;
  const context = { $, el, settings: { model: 'llama3.2', ollama_url: el.ollamaUrl.value }, document: { createElement: () => ({}) }, AnnieApi: { models: async () => ({ model_names: ['llama3.1:8b'], selection: { installed } }), updateSettings: async p => { saved++; return p; } }, AnnieValidators: { validateSettings: () => [] }, AnnieState: { set() {}, setPrefs() {} }, closeDialog() {}, refreshEngine: async () => {}, announce() {}, addErrorCard() {} };
  function $(id) { return nodes[id]; }
  vm.createContext(context);
  vm.runInContext(source.slice(source.indexOf('async function refreshModelPicker'), source.indexOf('function runtimeForSettings')), context);
  vm.runInContext(source.slice(source.indexOf('async function saveSettings'), source.indexOf('function setupRecognition')), context);
  return { context, nodes, saved: () => saved };
}

test('picker lists installed models without overwriting configured name', async () => {
  const h = harness(false);
  await h.context.refreshModelPicker();
  assert.equal(h.context.el.model.value, 'llama3.2');
  assert.equal(h.nodes['#installedModels'].children[0].value, 'llama3.1:8b');
  assert.match(h.nodes['#modelHint'].textContent, /not installed/);
});

test('missing model save requires explicit checkbox; installed model does not', async () => {
  const h = harness(false);
  await h.context.saveSettings();
  assert.equal(h.saved(), 0);
  h.nodes['#saveMissingModel'].checked = true;
  await h.context.saveSettings();
  assert.equal(h.saved(), 1);
  const ready = harness(true);
  await ready.context.saveSettings();
  assert.equal(ready.saved(), 1);
});
