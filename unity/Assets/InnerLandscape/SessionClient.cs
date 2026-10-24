using System;
using System.Collections;
using System.IO;
using UnityEngine;
using UnityEngine.Networking;
using UnityEngine.Video;
using UnityEngine.XR;

namespace InnerLandscape
{
    // Drop into the teammate's existing OpenXR project. No provider keys in the APK.
    public sealed class SessionClient : MonoBehaviour
    {
        public string serverUrl = "http://192.168.1.10:4173";
        public string pairingCode = "";
        public Camera trackedHead;
        public Collider landscapeCollider;
        public Renderer landscapeRenderer;
        public VideoPlayer videoPlayer;
        public string status = "Not paired";
        public string suggestedRegion = "";
        public string suggestionReason = "";
        public float dwellThreshold = 1.5f;
        public string SessionId => sessionId;
        public string ParticipantToken => token;
        public bool Active => snapshot != null && snapshot.status == "active" && !snapshot.pendingCycle;
        string token, sessionId, currentMedia;
        Snapshot snapshot;
        readonly float[] dwell = new float[3];
        string candidate = "";
        float candidateSeconds, reportAt, cycleSeconds;
        int cycle;
        bool hadTracking = true, sentEnd, busyAttention;
        Texture2D currentTexture;

        [Serializable] class PairRequest { public string code; }
        [Serializable] class PairReply { public string token; public string session_id; }
        [Serializable] public class Media { public string kind; public string url; public float duration; public bool region_map_verified; }
        [Serializable] public class Proposal { public string region; public string reason; }
        [Serializable] public class Snapshot { public string id; public string status; public int cycle; public bool pendingCycle; public string region; public Media media; public Proposal proposal; }
        [Serializable] class Command { public string command_id; public string command; public Payload payload = new Payload(); }
        [Serializable] class Payload { public string source = "head"; public string region; public int cycle; public Dwell dwell = new Dwell(); }
        [Serializable] class Dwell { public float sky; public float ridge; public float water; }

        void Awake()
        {
            if (videoPlayer) { videoPlayer.isLooping = false; videoPlayer.playOnAwake = false; videoPlayer.audioOutputMode = VideoAudioOutputMode.None; }
        }
        public void Pair() { if (string.IsNullOrEmpty(token)) StartCoroutine(PairRoutine()); }
        IEnumerator PairRoutine()
        {
            using (var request = JsonRequest("/api/pair", JsonUtility.ToJson(new PairRequest { code = pairingCode })))
            {
                yield return request.SendWebRequest();
                if (request.result != UnityWebRequest.Result.Success) { status = "Pairing failed. Check code and LAN address."; yield break; }
                var reply = JsonUtility.FromJson<PairReply>(request.downloadHandler.text);
                token = reply.token; sessionId = reply.session_id; status = "Paired";
            }
            StartCoroutine(Poll());
        }
        UnityWebRequest JsonRequest(string path, string json)
        {
            var request = new UnityWebRequest(serverUrl.TrimEnd('/') + path, "POST");
            request.uploadHandler = new UploadHandlerRaw(System.Text.Encoding.UTF8.GetBytes(json));
            request.downloadHandler = new DownloadHandlerBuffer(); request.SetRequestHeader("Content-Type", "application/json");
            if (!string.IsNullOrEmpty(token)) request.SetRequestHeader("Authorization", "Bearer " + token);
            request.timeout = 15; return request;
        }
        IEnumerator Poll()
        {
            while (!string.IsNullOrEmpty(token))
            {
                using (var request = UnityWebRequest.Get(serverUrl.TrimEnd('/') + "/api/sessions/" + sessionId))
                {
                    request.SetRequestHeader("Authorization", "Bearer " + token); request.timeout = 5;
                    yield return request.SendWebRequest();
                    if (request.result != UnityWebRequest.Result.Success)
                    {
                        status = "Disconnected — playback paused"; snapshot = null; if (videoPlayer) videoPlayer.Pause();
                    }
                    else
                    {
                        snapshot = JsonUtility.FromJson<Snapshot>(request.downloadHandler.text); status = snapshot.status;
                        if (snapshot.cycle != cycle) { cycle = snapshot.cycle; cycleSeconds = 0; sentEnd = false; Array.Clear(dwell, 0, dwell.Length); }
                        if (snapshot.status != "active" || snapshot.pendingCycle) { if (videoPlayer) videoPlayer.Pause(); }
                        if (snapshot.proposal != null) { suggestedRegion = snapshot.proposal.region; suggestionReason = snapshot.proposal.reason; }
                        if (snapshot.media != null && snapshot.media.region_map_verified && snapshot.media.url != currentMedia)
                        { currentMedia = snapshot.media.url; yield return LoadMedia(snapshot.media); }
                        if (snapshot.status == "active" && !snapshot.pendingCycle && videoPlayer && videoPlayer.isPrepared && !videoPlayer.isPlaying && videoPlayer.time < videoPlayer.length - .1) videoPlayer.Play();
                        if (snapshot.status == "completed") { token = null; yield break; }
                    }
                }
                yield return new WaitForSeconds(.5f);
            }
        }
        IEnumerator LoadMedia(Media media)
        {
            using (var request = UnityWebRequest.Get(serverUrl.TrimEnd('/') + media.url))
            {
                request.SetRequestHeader("Authorization", "Bearer " + token); request.timeout = 60;
                string file = Path.Combine(Application.temporaryCachePath, "landscape-" + Guid.NewGuid().ToString("N") + ".mp4");
                if (media.kind == "video") request.downloadHandler = new DownloadHandlerFile(file);
                yield return request.SendWebRequest();
                if (request.result != UnityWebRequest.Result.Success) { status = "Media unavailable; previous scene retained"; currentMedia = null; yield break; }
                if (media.kind == "image")
                {
                    var texture = new Texture2D(2, 2);
                    if (texture.LoadImage(request.downloadHandler.data)) { if (currentTexture) Destroy(currentTexture); currentTexture = texture; landscapeRenderer.material.mainTexture = texture; }
                    else { Destroy(texture); status = "Image could not be decoded"; }
                }
                else if (videoPlayer)
                {
                    videoPlayer.source = VideoSource.Url; videoPlayer.url = file; videoPlayer.renderMode = VideoRenderMode.MaterialOverride;
                    videoPlayer.targetMaterialRenderer = landscapeRenderer; videoPlayer.Prepare();
                    float deadline = Time.realtimeSinceStartup + 15;
                    while (!videoPlayer.isPrepared && Time.realtimeSinceStartup < deadline) yield return null;
                    if (videoPlayer.isPrepared && snapshot != null && snapshot.status == "active") videoPlayer.Play();
                    else status = "Video not ready; playback held";
                }
            }
        }
        void Update()
        {
            if (snapshot == null || snapshot.status != "active" || snapshot.pendingCycle || !trackedHead || !landscapeCollider) return;
            bool tracked = false;
            var device = InputDevices.GetDeviceAtXRNode(XRNode.Head);
            device.TryGetFeatureValue(CommonUsages.isTracked, out tracked);
            if (!tracked) { if (hadTracking) { if (videoPlayer) videoPlayer.Pause(); Send("tracking_lost"); } hadTracking = false; return; }
            hadTracking = true;
            cycleSeconds += Time.deltaTime;
            if (cycleSeconds >= 30 && !sentEnd) { sentEnd = true; Send("window_finished"); if (videoPlayer) videoPlayer.Pause(); }
            RaycastHit hit;
            if (landscapeCollider.Raycast(new Ray(trackedHead.transform.position, trackedHead.transform.forward), out hit, 10))
            {
                int index = Mathf.Min(2, Mathf.FloorToInt(Mathf.Clamp01(hit.textureCoord.x) * 3));
                string region = new[] { "sky", "ridge", "water" }[index];
                if (candidate != region) { candidate = region; candidateSeconds = 0; }
                candidateSeconds += Time.deltaTime;
                if (candidateSeconds >= dwellThreshold) dwell[index] += Time.deltaTime;
            }
            else { candidate = ""; candidateSeconds = 0; }
            if (Time.unscaledTime >= reportAt && !busyAttention) { reportAt = Time.unscaledTime + 1; StartCoroutine(ReportAttention()); }
        }
        IEnumerator ReportAttention()
        {
            busyAttention = true;
            var command = NewCommand("attention");
            command.payload.dwell = new Dwell { sky = Mathf.Min(30, dwell[0]), ridge = Mathf.Min(30, dwell[1]), water = Mathf.Min(30, dwell[2]) };
            yield return SendRoutine(command); busyAttention = false;
        }
        Command NewCommand(string name) { return new Command { command_id = Guid.NewGuid().ToString(), command = name, payload = new Payload { cycle = cycle } }; }
        public void ConfirmLookedRegion() { if (!string.IsNullOrEmpty(candidate)) { var cmd = NewCommand("select"); cmd.payload.region = candidate; StartCoroutine(SendRoutine(cmd)); } }
        public void Pause() { if (videoPlayer) videoPlayer.Pause(); Send("pause"); }
        public void StopSession() { if (videoPlayer) videoPlayer.Stop(); Send("stop"); }
        public void NextCycle() { Send("next"); }
        void Send(string name) { if (!string.IsNullOrEmpty(token)) StartCoroutine(SendRoutine(NewCommand(name))); }
        IEnumerator SendRoutine(Command cmd)
        {
            using (var request = JsonRequest("/api/sessions/" + sessionId + "/commands", JsonUtility.ToJson(cmd)))
            {
                yield return request.SendWebRequest();
                if (request.result != UnityWebRequest.Result.Success) status = "Command not acknowledged. Keep playback paused.";
            }
        }
        void OnApplicationPause(bool paused) { if (paused) Pause(); }
        void OnDisable() { if (videoPlayer) videoPlayer.Stop(); token = null; if (currentTexture) Destroy(currentTexture); }
    }
}
