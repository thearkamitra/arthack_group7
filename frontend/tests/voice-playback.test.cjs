const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
test('browser speech gate follows actual scheduled audio and explicitly stops',async()=>{
  const calls=[],timers=new Map(),rates=[],sent=[];let socket,audio,processor,stopped=false,trackStopped=false;
  class Socket {static OPEN=1;constructor(){socket=this;this.readyState=1;}send(item){sent.push(JSON.parse(item));}close(){}}
  class Context {
    constructor(){audio=this;this.currentTime=0;this.sampleRate=48000;this.state='running';this.destination={};}
    async resume(){}async close(){this.state='closed';}
    createMediaStreamSource(){return {connect(){},disconnect(){}};}
    createScriptProcessor(){processor={connect(){},disconnect(){}};return processor;}
    createBuffer(ch,count,rate){rates.push(rate);return {duration:count/rate,getChannelData:()=>new Float32Array(count)};}
    createBufferSource(){return {connect(){},start(){},stop(){stopped=true;}};}
  }
  const context={window:{isSecureContext:true,LandscapeUnityDemo:{speech:async(...args)=>{calls.push(args);}}},navigator:{mediaDevices:{getUserMedia:async()=>({getTracks:()=>[{stop(){trackStopped=true;}}]})}},AudioContext:Context,WebSocket:Socket,location:{protocol:'http:',host:'localhost'},crypto:{randomUUID:()=> 'speech-window'},setInterval(fn){timers.set(1,fn);return 1;},clearInterval(id){timers.delete(id);},Uint8Array,Int16Array,Float32Array,DataView,atob:s=>Buffer.from(s,'base64').toString('binary'),btoa:s=>Buffer.from(s,'binary').toString('base64')};
  vm.runInNewContext(fs.readFileSync('frontend/voice.js','utf8'),context);
  const api=context.window.LandscapeVoice;await api.start('session',()=>{});
  await socket.onmessage({data:JSON.stringify({type:'conversation_initiation_metadata',conversation_initiation_metadata_event:{agent_output_audio_format:'pcm_48000',user_input_audio_format:'pcm_16000'}})});
  processor.onaudioprocess({inputBuffer:{getChannelData:()=>new Float32Array(4800)}});
  assert.equal(Buffer.from(sent.at(-1).user_audio_chunk,'base64').length,3200,'native 48k microphone resamples to provider 16k');
  await socket.onmessage({data:JSON.stringify({type:'audio',audio_event:{audio_base_64:Buffer.alloc(3200).toString('base64')}})});
  assert.equal(rates.at(-1),48000,'provider output format controls PCM decoding');
  [...timers.values()][0]();assert.equal(calls.at(-1)[1],false,'queued audio is not audible');
  audio.currentTime=.05;[...timers.values()][0]();assert.equal(calls.at(-1)[1],true);assert.equal(calls.at(-1)[2],'speech-window');
  audio.currentTime=.2;[...timers.values()][0]();assert.equal(calls.at(-1)[1],false);
  await api.stop();assert.equal(calls.at(-1)[1],false);assert.equal(timers.size,0);assert.equal(trackStopped,true);assert.equal(stopped,true);
});
