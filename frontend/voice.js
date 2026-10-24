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
  const api = {
    get active() {
      return !ended;
    },
    async start(sessionId, notify) {
      if (!window.isSecureContext)
        throw new Error("Microphone access requires localhost or HTTPS.");
      receive = notify;
      await api.stop();
      // Must be called from the explicit user button after the disclosure.
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
        video: false,
      });
      context = new AudioContext({ sampleRate: 16000 });
      await context.resume();
      nextTime = 0;
      const protocol = location.protocol === "https:" ? "wss:" : "ws:";
      socket = new WebSocket(
        `${protocol}//${location.host}/api/sessions/${sessionId}/voice`,
      );
      ended = false;
      socket.onopen = () => {
        socket.send(JSON.stringify({ consent: true }));
        notify("Voice connected. Microphone active.");
      };
      socket.onerror = () => {
        notify("Voice connection failed.");
        api.stop();
      };
      socket.onclose = () => {
        api.stop();
        notify("Voice disconnected.");
      };
      source = context.createMediaStreamSource(stream);
      // Kept small and dependency-free for the prototype; migrate to AudioWorklet
      // when measuring headset/browser latency. Never record these chunks.
      processor = context.createScriptProcessor(4096, 1, 1);
      processor.onaudioprocess = (event) => {
        if (ended || socket.readyState !== WebSocket.OPEN) return;
        const floats = event.inputBuffer.getChannelData(0),
          pcm = new Int16Array(floats.length);
        for (let i = 0; i < floats.length; i++)
          pcm[i] = Math.max(-1, Math.min(1, floats[i])) * 32767;
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
          const buffer = context.createBuffer(1, count, 16000),
            channel = buffer.getChannelData(0);
          for (let i = 0; i < count; i++)
            channel[i] = view.getInt16(i * 2, true) / 32768;
          const node = context.createBufferSource();
          node.buffer = buffer;
          node.connect(context.destination);
          nextTime = Math.max(nextTime, context.currentTime + 0.03);
          node.start(nextTime);
          nextTime += buffer.duration;
          playing.push(node);
          node.onended = () => {
            playing = playing.filter((n) => n !== node);
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
      ended = true;
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
