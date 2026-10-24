const test = require('node:test');
const assert = require('node:assert/strict');
const S = require('../state.js');
const make = () => S.create('demo-jamie', {goal:'Explore change',consent:true});
test('session setup rejects unknown clients, blank aims and absent acknowledgement', () => {
  assert.throws(()=>S.create('other',{goal:'test',consent:true}));
  assert.throws(()=>S.create('demo-jamie',{goal:' ',consent:true}));
  assert.throws(()=>S.create('demo-jamie',{goal:'test',consent:false}));
});
test('a reflection advances only the selected region and preserves entered text', () => {
  const s=make();S.select(s,'water');assert.equal(S.reflect(s,'  A calm shore.  '),true);
  assert.deepEqual(s.depth,{sky:0,ridge:0,water:1});
  assert.equal(s.events.find(e=>e.type==='reflection').text,'A calm shore.');
  for(let n=0;n<10;n++) S.reflect(s,'Another thought');
  assert.equal(s.depth.water,3);
});
test('pause blocks time, selection and reflections; resume is explicit', () => {
  const s=make();S.tick(s);S.pause(s);assert.equal(S.tick(s),false);
  assert.equal(S.select(s,'water'),false);assert.equal(S.reflect(s,'test'),false);
  assert.equal(s.remaining,29);assert.equal(S.resume(s),true);assert.equal(S.tick(s),true);
});
test('the 30-second window ends once and next cycle needs confirmation', () => {
  const s=make();assert.equal(S.next(s),false);
  for(let i=0;i<40;i++) S.tick(s);
  assert.equal(s.remaining,0);assert.equal(s.pendingCycle,true);
  assert.equal(s.events.filter(e=>e.type==='cycle').length,1);
  assert.equal(S.reflect(s,'late'),false);assert.equal(S.next(s),true);
  assert.equal(s.remaining,30);assert.equal(s.cycle,2);
});
test('completed sessions cannot resume, reflect, advance or restart a cycle', () => {
  const s=make();S.finish(s);assert.equal(S.resume(s),false);assert.equal(S.tick(s),false);
  assert.equal(S.reflect(s,'test'),false);assert.equal(S.select(s,'water'),false);
  assert.equal(S.next(s),false);assert.equal(S.finish(s),false);
});
test('saved notes, reflections and checks reload; unfinished session restores paused', () => {
  const data=S.fresh(),s=make();s.preNotes='Before';s.postNotes='After';s.before='4';S.reflect(s,'My reflection');
  data.notes['demo-jamie']='Context';data.sessions.push(s);
  const restored=S.load(JSON.stringify(data));
  assert.equal(restored.sessions[0].status,'paused');assert.equal(restored.sessions[0].preNotes,'Before');
  assert.equal(restored.sessions[0].postNotes,'After');assert.equal(restored.notes['demo-jamie'],'Context');
  assert.ok(restored.sessions[0].events.some(e=>e.text==='My reflection'));
});
test('malformed or incompatible saved data falls back to a clean demo', () => {
  for(const raw of ['broken','null','{}','{"version":2,"sessions":[],"notes":{}}']) assert.deepEqual(S.load(raw),S.fresh());
  const data=S.fresh();data.sessions.push({...make(),depth:{sky:7,ridge:0,water:0}});
  assert.deepEqual(S.load(JSON.stringify(data)),S.fresh());
});
