const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync('src/annie/ui/app.js', 'utf8');

test('modal Tab wraps both ways and excludes unavailable controls', () => {
  let focused = null;
  function control(extra = {}) {const node = {disabled: false, tabIndex: 0, getClientRects: () => [{}], focus: () => {focused = node;}, ...extra}; return node;}
  const first = control();
  const last = control();
  const disabled = control({disabled: true});
  const hidden = control({getClientRects: () => []});
  const context = {document: {activeElement: first}, getComputedStyle: () => ({visibility: 'visible'})};
  vm.createContext(context);
  vm.runInContext(source.slice(source.indexOf('function trapDialogFocus'), source.indexOf('function closeDialog')), context);
  let prevented = false;
  const event = {key: 'Tab', shiftKey: true, currentTarget: {querySelectorAll: () => [first, hidden, disabled, last]}, preventDefault() {prevented = true;}};
  context.trapDialogFocus(event);
  assert.equal(focused, last);
  assert.equal(prevented, true);
  context.document.activeElement = last;
  event.shiftKey = false;
  context.trapDialogFocus(event);
  assert.equal(focused, first);
});
