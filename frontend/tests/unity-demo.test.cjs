const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function setup(){
  const calls=[],handlers={};let state={enabled:true,connected:true,headset:false,busy:false,yaw:0,pitch:0};
  const window={LandscapeBackend:{flush:async()=>{},canonical:async()=>{throw new Error('Existing image must be preserved');}}};
  const document={hidden:false,querySelector:selector=>selector==='[data-demo-session]'?{dataset:{demoSession:'s'}}:selector==='#unity-demo-frame'?{getBoundingClientRect:()=>({width:668,height:376})}:selector==='#unity-demo-status'?{textContent:''}:null,querySelectorAll:()=>[],addEventListener:(name,fn)=>handlers[name]=fn};
  const context={window,document,Date,setInterval(){},async fetch(url,options){calls.push({url,options});return {ok:true,json:async()=>url.endsWith('/start')||url.endsWith('/input')?state:{status:'active',media:{url:'/existing.png'},demo:state}};}};
  vm.runInNewContext(fs.readFileSync('frontend/unity-demo.js','utf8'),context);
  vm.runInNewContext(fs.readFileSync('frontend/demo-script.js','utf8'),context);
  assert.equal(typeof window.LandscapeDemo.steps, 'object');
  return {api:window.LandscapeUnityDemo,calls,handlers,set:(change)=>Object.assign(state,change)};
}
test('arrow commands preserve the existing source image and send real demo controls',async()=>{
  const {api,calls}=setup();await api.start('s');await api.move('left');
  assert.equal(calls.at(-1).url,'/api/sessions/s/demo/input');assert.equal(JSON.parse(calls.at(-1).options.body).action,'left');
});
test('headset priority, disconnection and transitions block arrow requests',async()=>{
  const {api,calls,set}=setup();await api.start('s');
  for(const state of [{headset:true},{headset:false,connected:false},{connected:true,busy:true}]){
    set(state);const before=calls.length;await api.move('right');assert.equal(calls.length,before);
  }
});
test('speech reports have increasing sequence numbers',async()=>{
  const {api,calls}=setup();await api.speech('s',true,'window');await api.speech('s',false,'window');
  const [first,second]=calls.map(c=>JSON.parse(c.options.body));assert.ok(second.sequence>first.sequence);assert.equal(second.speaking,false);
});

test('confirmation automatically requests real fal generation from the visible viewport without a prompt',async()=>{
  const {api,calls}=setup();await api.start('s');await api.move('freeze');
  const simulation=calls.find(c=>c.url.endsWith('/demo/generate'));
  assert.deepEqual(JSON.parse(simulation.options.body),{width:668,height:376,autoplay:true});
  assert.equal(calls.some(c=>c.url.endsWith('/media')||c.url.endsWith('/region-entry')),false);
});
