using System;
using System.Collections;
using System.Collections.Generic;
using System.Collections.Concurrent;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

namespace InnerLandscape
{
    // Explicit StartVoice() button only, after showing provider/cost disclosure.
    // PCM bridge requires physical Android microphone/echo testing by the Unity owner.
    [RequireComponent(typeof(AudioSource))]
    public sealed class VoiceClient : MonoBehaviour
    {
        public SessionClient session;
        public string status = "Voice stopped";
        ClientWebSocket socket;
        CancellationTokenSource cancellation;
        AudioClip microphone;
        AudioSource speaker;
        string microphoneDevice;
        int cursor;
        bool running, starting;
        public bool GuideSpeaking => speaker && speaker.isPlaying;
        public string SpeechWindow { get; private set; } = "";
        bool turnOpen; float lastChunk;
        public void PlaySyntheticGuide(AudioClip clip)
        {
            speaker=GetComponent<AudioSource>();speaker.clip=clip;SpeechWindow=Guid.NewGuid().ToString();speaker.Play();
        }
        readonly Queue<AudioClip> audioQueue = new Queue<AudioClip>();
        readonly ConcurrentQueue<string> incoming = new ConcurrentQueue<string>();
        [Serializable] class Hello { public string token; public bool consent = true; }
        [Serializable] class Chunk { public string user_audio_chunk; }
        [Serializable] class AudioEvent { public string audio_base_64; }
        [Serializable] class Message { public string type; public string message; public AudioEvent audio_event; }

        public async void StartVoice()
        {
            if (running || starting || session == null || !session.Active || string.IsNullOrEmpty(session.ParticipantToken)) return;
            if (!Application.HasUserAuthorization(UserAuthorization.Microphone))
            { StartCoroutine(RequestMicrophone()); status = "Approve microphone, then press Start voice again."; return; }
            if (Microphone.devices.Length == 0) { status = "No microphone available"; return; }
            starting = true;
            cancellation = new CancellationTokenSource(); socket = new ClientWebSocket();
            try
            {
                string url = session.serverUrl.TrimEnd('/').Replace("http://", "ws://").Replace("https://", "wss://") + "/api/sessions/" + session.SessionId + "/voice";
                await socket.ConnectAsync(new Uri(url), cancellation.Token);
                await Send(JsonUtility.ToJson(new Hello { token = session.ParticipantToken }));
                speaker = GetComponent<AudioSource>(); speaker.playOnAwake = false;
                microphoneDevice = Microphone.devices[0]; microphone = Microphone.Start(microphoneDevice, true, 2, 16000);
                cursor = 0; running = true; status = "Microphone active · ElevenLabs";
                _ = ReceiveLoop(); StartCoroutine(Capture());
            }
            catch { status = "Voice unavailable. Check coordinator status."; StopVoice(); }
            finally { starting = false; }
        }
        IEnumerator RequestMicrophone() { yield return Application.RequestUserAuthorization(UserAuthorization.Microphone); }
        async Task Send(string json)
        {
            byte[] bytes = Encoding.UTF8.GetBytes(json);
            await socket.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, cancellation.Token);
        }
        IEnumerator Capture()
        {
            while (running)
            {
                if (!session.Active) { StopVoice(); yield break; }
                int position = Microphone.GetPosition(microphoneDevice);
                int available = (position - cursor + microphone.samples) % microphone.samples;
                if (available >= 1600)
                {
                    var values = new float[1600]; microphone.GetData(values, cursor);
                    cursor = (cursor + 1600) % microphone.samples;
                    byte[] bytes = new byte[values.Length * 2];
                    for (int i = 0; i < values.Length; i++)
                    { short sample = (short)(Mathf.Clamp(values[i], -1, 1) * 32767); bytes[i * 2] = (byte)(sample & 255); bytes[i * 2 + 1] = (byte)((sample >> 8) & 255); }
                    Task send = Send(JsonUtility.ToJson(new Chunk { user_audio_chunk = Convert.ToBase64String(bytes) }));
                    while (!send.IsCompleted && running) yield return null;
                    if (send.IsFaulted) { StopVoice(); yield break; }
                }
                yield return null;
            }
        }
        async Task ReceiveLoop()
        {
            byte[] buffer = new byte[65536];
            try
            {
                while (running && socket.State == WebSocketState.Open)
                {
                    var text = new StringBuilder(); WebSocketReceiveResult received;
                    do
                    {
                        received = await socket.ReceiveAsync(new ArraySegment<byte>(buffer), cancellation.Token);
                        if (received.MessageType == WebSocketMessageType.Close) return;
                        text.Append(Encoding.UTF8.GetString(buffer, 0, received.Count));
                        if (text.Length > 2000000) throw new InvalidOperationException();
                    } while (!received.EndOfMessage);
                    incoming.Enqueue(text.ToString());
                }
            }
            catch { incoming.Enqueue("{\"type\":\"error\",\"message\":\"Voice disconnected\"}"); }
            finally { incoming.Enqueue("{\"type\":\"closed\"}"); }
        }
        void Update()
        {
            while (incoming.TryDequeue(out string raw))
            {
                var msg = JsonUtility.FromJson<Message>(raw);
                if (msg.type == "error" || msg.type == "closed") { status = msg.message ?? "Voice disconnected"; StopVoice(); }
                if (msg.type == "interruption" && speaker) { turnOpen=false; speaker.Stop(); while (audioQueue.Count > 0) Destroy(audioQueue.Dequeue()); }
                if (msg.type == "audio" && running && msg.audio_event != null)
                {
                    if(!turnOpen){SpeechWindow=Guid.NewGuid().ToString();turnOpen=true;}
                    lastChunk=Time.unscaledTime;
                    byte[] bytes = Convert.FromBase64String(msg.audio_event.audio_base_64);
                    float[] samples = new float[bytes.Length / 2];
                    for (int i = 0; i < samples.Length; i++) samples[i] = (short)(bytes[i * 2] | bytes[i * 2 + 1] << 8) / 32768f;
                    var clip = AudioClip.Create("Guide chunk", samples.Length, 1, 16000, false); clip.SetData(samples, 0);
                    audioQueue.Enqueue(clip);
                }
            }
            if (running && speaker && !speaker.isPlaying && audioQueue.Count > 0) { if (speaker.clip) Destroy(speaker.clip); speaker.clip = audioQueue.Dequeue(); speaker.Play(); }
            if(turnOpen && speaker && !speaker.isPlaying && audioQueue.Count==0 && Time.unscaledTime-lastChunk>1)turnOpen=false;
            if (running && !session.Active) StopVoice();
        }
        public void StopVoice()
        {
            running = false; turnOpen=false;
            if (microphone) { Microphone.End(microphoneDevice); Destroy(microphone); microphone = null; }
            if (speaker) speaker.Stop(); while (audioQueue.Count > 0) Destroy(audioQueue.Dequeue()); cancellation?.Cancel(); socket?.Dispose(); socket = null;
        }
        void OnApplicationPause(bool paused) { if (paused) StopVoice(); }
        void OnDisable() { StopVoice(); }
    }
}
