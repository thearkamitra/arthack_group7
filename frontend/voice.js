/* PCM audio stays in memory. The backend owns the permanent provider credential. */
(function () {
  let socket,
    stream,
    context,
    processor,
    source,
    nextTime = 0,
    playing = [];
  let ended = true,
    receive = () => {};
  let outputRate=16000, inputRate=16000;
  let voiceSid=null, speechTimer=null, windowId="", lastScheduledEnd=0;
  function publishSpeech() {
    if(!voiceSid)return;
    const time=context?.currentTime || 0;
    const speaking=!ended && context?.state==='running' && playing.some(n=>n.playbackStart<=time&&n.playbackEnd>time);
    window.LandscapeUnityDemo?.speech(voiceSid,speaking,windowId).catch(()=>{});
  }
  const api = {
    get active() {
      return !ended;
    },
    async start(sessionId, notify) {
      try { await api.connect(sessionId,notify); }
      catch(error){await api.stop();throw new Error(error.name==='NotAllowedError' ? 'Microphone permission was denied. Allow microphone access for this local site, then press Start voice guide.' : error.message);}
    },
    async connect(sessionId, notify) {
      if (!window.isSecureContext)
        throw new Error("Microphone access requires localhost or HTTPS.");
      receive = notify;
      await api.stop();
      // Must be called from the explicit user button after the disclosure.
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
        video: false,
      });
      context = new AudioContext();
      await context.resume();
      outputRate=inputRate=16000;
      nextTime = 0;voiceSid=sessionId;windowId="";lastScheduledEnd=0;
      speechTimer=setInterval(publishSpeech,150);
      const protocol = location.protocol === "https:" ? "wss:" : "ws:";
      socket = new WebSocket(
        `${protocol}//${location.host}/api/sessions/${sessionId}/voice`,
      );
      ended = false;
      socket.onopen = () => {
        socket.send(JSON.stringify({ consent: true }));
        notify("Connecting to ElevenLabs… microphone active.");
      };
      socket.onerror = () => {
        notify("Voice connection failed.");
        api.stop();
      };
      socket.onclose = (event) => {
        api.stop();
        const reasons={4401:'Voice authentication expired. Reload the local workspace.',4403:'Voice origin or consent was rejected.',4409:'Resume the session before starting voice.'};
        notify(reasons[event?.code] || 'Voice disconnected. Press Start voice guide to reconnect.');
      };
      source = context.createMediaStreamSource(stream);
      // Kept small and dependency-free for the prototype; migrate to AudioWorklet
      // when measuring headset/browser latency. Never record these chunks.
      processor = context.createScriptProcessor(4096, 1, 1);
      processor.onaudioprocess = (event) => {
        if (ended || socket.readyState !== WebSocket.OPEN) return;
        const floats = event.inputBuffer.getChannelData(0);
        const ratio=(context.sampleRate || 16000)/inputRate;
        const pcm=new Int16Array(Math.max(1,Math.floor(floats.length/ratio)));
        for(let i=0;i<pcm.length;i++){
          const at=Math.min(floats.length-1,i*ratio),left=Math.floor(at),mix=at-left;
          const sample=floats[left]*(1-mix)+floats[Math.min(left+1,floats.length-1)]*mix;
          pcm[i]=Math.max(-1,Math.min(1,sample))*32767;
        }
        const bytes = new Uint8Array(pcm.buffer);
        let binary = "";
        for (const byte of bytes) binary += String.fromCharCode(byte);
        socket.send(JSON.stringify({ user_audio_chunk: btoa(binary) }));
      };
      source.connect(processor);
      processor.connect(context.destination);
      socket.onmessage = async (event) => {
        const item = JSON.parse(event.data);
        if (item.type === "error") {
          notify(item.message);
          await api.stop();
          return;
        }
        if(item.type==='conversation_initiation_metadata'){
          const metadata=item.conversation_initiation_metadata_event || {};
          const output=/^pcm_(\d+)$/.exec(metadata.agent_output_audio_format || 'pcm_16000');
          const input=/^pcm_(\d+)$/.exec(metadata.user_input_audio_format || 'pcm_16000');
          if(!output||!input){notify('Unsupported voice audio format; connection stopped.');await api.stop();return;}
          outputRate=Number(output[1]);inputRate=Number(input[1]);
          notify('ElevenLabs voice connected · microphone active.');
        }
        if(item.type==='agent_response'){
          const text=item.agent_response_event?.agent_response;
          const label=document.querySelector('#guide-text');if(label&&text)label.textContent=text;
        }
        if (item.type === "interruption") {
          playing.forEach((s) => {
            try {
              s.stop();
            } catch {}
          });
          playing = [];
          nextTime = context?.currentTime || 0;
        }
        if (item.type === "audio" && context && !ended) {
          const encoded = item.audio_event?.audio_base_64;
          if (!encoded) return;
          const bytes = Uint8Array.from(atob(encoded), (c) => c.charCodeAt(0));
          const view = new DataView(bytes.buffer),
            count = Math.floor(bytes.length / 2);
          const buffer = context.createBuffer(1, count, outputRate),
            channel = buffer.getChannelData(0);
          for (let i = 0; i < count; i++)
            channel[i] = view.getInt16(i * 2, true) / 32768;
          const node = context.createBufferSource();
          node.buffer = buffer;
          node.connect(context.destination);
          nextTime = Math.max(nextTime, context.currentTime + 0.03);
          if(!windowId || nextTime-lastScheduledEnd>1)windowId=crypto.randomUUID();
          node.playbackStart=nextTime;node.playbackEnd=nextTime+buffer.duration;
          node.start(nextTime);
          nextTime += buffer.duration;lastScheduledEnd=nextTime;
          playing.push(node);
          node.onended = () => {
            playing = playing.filter((n) => n !== node);publishSpeech();
          };
        }
        if (item.type === "conversation_initiation_metadata") api.update();
      };
    },
    update() {
      if (socket?.readyState === WebSocket.OPEN)
        socket.send(JSON.stringify({ type: "context_request" }));
    },
    async stop() {
      ended = true;publishSpeech();voiceSid=null;
      if(speechTimer)clearInterval(speechTimer);speechTimer=null;
      if (socket) {
        const old = socket;
        socket = null;
        old.onclose = null;
        old.close();
      }
      stream?.getTracks().forEach((t) => t.stop());
      stream = null;
      if (processor) {
        processor.disconnect();
        processor.onaudioprocess = null;
        processor = null;
      }
      source?.disconnect();
      source = null;
      playing.forEach((s) => {
        try {
          s.stop();
        } catch {}
      });
      playing = [];
      if (context) {
        const old = context;
        context = null;
        await old.close();
      }
    },
  };
  window.LandscapeVoice = api;
})();
