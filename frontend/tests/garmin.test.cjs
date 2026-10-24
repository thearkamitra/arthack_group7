const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function setup() {
  const calls = [], timers = new Map(), handlers = {};
  let next = 0, fail = false;
  const context = {
    window: { LandscapeBackend: {flush:async()=>{}}, dispatchEvent() {}, addEventListener(name,fn){handlers[name]=fn;} },
    document: {hidden:false, addEventListener(name,fn){handlers[name]=fn;}},
    CustomEvent: class {}, AbortSignal,
    setInterval(fn){timers.set(++next, fn);return next;}, clearInterval(id){timers.delete(id);},
    async fetch(path, options) {
      calls.push({path,options});
      if (fail) throw new Error('offline');
      const result = path.endsWith('/scan') ? {devices:[{id:'watch1',name:'Test watch'}]} : path.endsWith('/start') ? {token:'lease',observation:{status:'baseline'}} : path.endsWith('/stop') ? {status:'disconnected'} : {status:'tracking',bpm:80};
      return {ok:true,json:async()=>result};
    },
  };
  vm.runInNewContext(fs.readFileSync('frontend/garmin.js','utf8'), context);
  return {api:context.window.LandscapeGarmin, calls, timers, handlers, context, fail:()=>{fail=true;}};
}
test('explicit consent, scan, connect and stop release the in-memory lease', async()=>{
  const {api,calls,timers}=setup();
  await assert.rejects(api.start('s','watch1',false), /Confirm/);
  assert.equal(calls.length,0);
  await api.scan(); assert.equal(api.state.devices.length,1);
  await api.start('s','watch1',true);
  assert.equal(api.state.observation.bpm,80); assert.equal(timers.size,1);
  assert.equal(calls.at(-1).options.headers['X-Garmin-Token'],'lease');
  await api.stop(); assert.equal(api.state.sid,null);assert.equal(timers.size,0);
  assert.equal(api.state.observation.bpm,undefined);assert.equal(api.state.devices.length,0);
  assert.ok(calls.at(-1).path.endsWith('/stop'));
});
test('pause or leaving session stops polling and clears values',async()=>{
  const {api,timers}=setup();await api.start('s','watch1',true);
  api.reconcile({id:'s',status:'paused'},true);
  assert.equal(api.state.sid,null);assert.equal(timers.size,0);
});
test('hidden page releases monitoring',async()=>{
  const {api,handlers,context}=setup();await api.start('s','watch1',true);
  context.document.hidden=true;handlers.visibilitychange();
  assert.equal(api.state.sid,null);
});
test('poll failure stops monitoring instead of retaining old BPM',async()=>{
  const {api,timers,fail}=setup();await api.start('s','watch1',true);
  fail();await [...timers.values()][0]();
  assert.equal(api.state.sid,null);assert.equal(api.state.observation.bpm,undefined);
  assert.match(api.state.message,/offline/);
});
