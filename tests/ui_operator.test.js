const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const code = fs.readFileSync('src/annie/ui/app.js', 'utf8');

test('offline composer gating is independent of phase and preserves input', () => {
  const nodes = new Proxy({}, {get(o,k) { return o[k] ||= {dataset:{}, value:'Unsaved draft',setAttribute(){}}; }});
  const context = {el:nodes, PHASE_VIEW:{idle:{label:'Ready',copy:''}}, authRequired:false,micSupported:true,activeWaveform:null,AnnieState:{get:()=>({})},renderRuntime(){},companion:null};
  vm.createContext(context);
  vm.runInContext(code.slice(code.indexOf('function renderState'), code.indexOf('function footerMarkup')), context);
  context.renderState({session:{phase:'idle',runtime:{model:{availability:'unavailable'}}}});
  assert.equal(nodes.send.disabled,true);
  assert.equal(nodes.mic.disabled,true);
  assert.equal(nodes.input.disabled,false);
  assert.equal(nodes.openMemoryBtn.disabled,false);
  assert.equal(nodes.input.value,'Unsaved draft');
});

test('local route badge remains unverified and remote routes remain disclosed', () => {
  const nodes = new Proxy({}, {get(o,k) {return o[k] ||= {};}});
  const context = {el:nodes,setBadge:(node,label,tone)=>Object.assign(node,{label,tone})};
  vm.createContext(context);
  vm.runInContext(code.slice(code.indexOf('function renderRuntime'),code.indexOf('function renderState')),context);
  context.renderRuntime({network:{claim:'not_verified',routes:{model:'loopback',voice:'container'}}});
  assert.equal(nodes.networkStatus.label,'Network: local routes, isolation unverified');
  assert.equal(nodes.networkStatus.tone,'warn');
  context.renderRuntime({network:{claim:'remote_configured',routes:{model:'remote'}}});
  assert.equal(nodes.networkStatus.label,'Network: remote route');
  assert.equal(nodes.networkStatus.tone,'bad');
});
