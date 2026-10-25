const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
test('browser speech gate follows actual scheduled audio and explicitly stops',async()=>{
  const calls=[],timers=new Map();let socket,audio,stopped=false,trackStopped=false;
  class Socket {static OPEN=1;constructor(){socket=this;this.readyState=1;}send(){}close(){}}
  class Context {
    constructor(){audio=this;this.currentTime=0;this.state='running';this.destination={};}
    async resume(){}async close(){this.state='closed';}
    createMediaStreamSource(){return {connect(){},disconnect(){}};}
    createScriptProcessor(){return {connect(){},disconnect(){}};}
    createBuffer(ch,count,rate){return {duration:count/rate,getChannelData:()=>new Float32Array(count)};}
    createBufferSource(){return {connect(){},start(){},stop(){stopped=true;}};}
  }
  const context={window:{isSecureContext:true,LandscapeUnityDemo:{speech:async(...args)=>{calls.push(args);}}},navigator:{mediaDevices:{getUserMedia:async()=>({getTracks:()=>[{stop(){trackStopped=true;}}]})}},AudioContext:Context,WebSocket:Socket,location:{protocol:'http:',host:'localhost'},crypto:{randomUUID:()=> 'speech-window'},setInterval(fn){timers.set(1,fn);return 1;},clearInterval(id){timers.delete(id);},Uint8Array,Int16Array,Float32Array,DataView,atob:s=>Buffer.from(s,'base64').toString('binary'),btoa:s=>Buffer.from(s,'binary').toString('base64')};
  vm.runInNewContext(fs.readFileSync('frontend/voice.js','utf8'),context);
  const api=context.window.LandscapeVoice;await api.start('session',()=>{});
  await socket.onmessage({data:JSON.stringify({type:'audio',audio_event:{audio_base_64:Buffer.alloc(3200).toString('base64')}})});
  [...timers.values()][0]();assert.equal(calls.at(-1)[1],false,'queued audio is not audible');
  audio.currentTime=.05;[...timers.values()][0]();assert.equal(calls.at(-1)[1],true);assert.equal(calls.at(-1)[2],'speech-window');
  audio.currentTime=.2;[...timers.values()][0]();assert.equal(calls.at(-1)[1],false);
  await api.stop();assert.equal(calls.at(-1)[1],false);assert.equal(timers.size,0);assert.equal(trackStopped,true);assert.equal(stopped,true);
});
