const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function setup(){
  const calls=[],messages=[],timers=[];let authenticated=true,denyBootstrap=false,fail=false,serverError=0;
  const workspace={version:1,sessions:[],notes:{}};
  const context={window:{},location:{protocol:'http:',hostname:'127.0.0.1'},document:{hidden:false},setInterval(fn){timers.push(fn);},crypto:{randomUUID:()=> 'test-command'},async fetch(path,options){
    calls.push({path,options});
    if(fail)throw new Error('offline');
    if(path==='/'){if(!denyBootstrap)authenticated=true;return {ok:!denyBootstrap,status:denyBootstrap?403:200,json:async()=>({})};}
    const status=serverError || (authenticated?200:401);
    return {ok:status===200,status,json:async()=>status!==200?{detail:'Authentication required'}:path==='/api/status'?{service:'inner-landscape'}:{revision:1,workspace}};
  }};
  vm.runInNewContext(fs.readFileSync('frontend/backend.js','utf8'),context);
  return {api:context.window.LandscapeBackend,calls,messages,timers,workspace,expire:()=>authenticated=false,deny:()=>denyBootstrap=true,offline:()=>fail=true,serverError:n=>serverError=n};
}
test('stale cookie after startup is renewed once through existing local bootstrap',async()=>{
  const s=setup();await s.api.start(s.workspace,()=>{},m=>s.messages.push(m));
  s.expire();await s.timers[0]();
  assert.deepEqual(s.calls.slice(-3).map(c=>c.path),['/api/workspace','/','/api/workspace']);
  assert.ok(!s.messages.some(m=>m.includes('unavailable')));
});
test('authentication failure is bounded and distinguished from a network failure',async()=>{
  const s=setup();await s.api.start(s.workspace,()=>{},m=>s.messages.push(m));s.expire();s.deny();await s.timers[0]();
  assert.match(s.messages.at(-1),/authentication expired/);assert.equal(s.calls.filter(c=>c.path==='/').length,1);
  s.offline();await s.timers[0]();assert.match(s.messages.at(-1),/connection failed/);
});
test('a 401 after successful bootstrap is not retried indefinitely',async()=>{
  const s=setup();await s.api.start(s.workspace,()=>{},m=>s.messages.push(m));s.serverError(401);await s.timers[0]();
  assert.deepEqual(s.calls.slice(-3).map(c=>c.path),['/api/workspace','/','/api/workspace']);assert.match(s.messages.at(-1),/authentication expired/);
});
test('paid mutations and workspace writes are never automatically retried',async()=>{
  const s=setup();await s.api.start(s.workspace,()=>{},()=>{});s.expire();const before=s.calls.length;
  await assert.rejects(s.api.generate('s',{kind:'video',brief:'test'}),/not retried/);
  assert.equal(s.calls.length-before,1);assert.equal(s.calls.at(-1).options.method,'POST');
  await assert.rejects(s.api.save(s.workspace),/not retried/);assert.equal(s.calls.at(-1).options.method,'PUT');
  assert.equal(s.calls.filter(c=>c.path==='/').length,0);
});
