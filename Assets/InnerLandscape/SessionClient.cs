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
        public AttentionInput attentionInput;
        public RegionZoomTransition transition;
        public VoiceClient voice;
        [NonSerialized] public RegionAttention spatial = new RegionAttention();
        public string SourceHash => snapshot?.source_hash ?? "";
        public int Cycle => cycle;
        public bool ImageReady => currentTexture != null;
        public string status = "Not paired";
        public string suggestedRegion = "";
        public string suggestionReason = "";
        public float dwellThreshold = 1.5f;
        public string SessionId => sessionId;
        public string ParticipantToken => token;
        public bool Active => !localHold && snapshot != null && snapshot.status == "active" && !snapshot.pendingCycle;
        public string LookedRegion => spatial.ValidSeconds>=.5f?"cell "+(spatial.Winner+1)+" ("+spatial.Percentage(spatial.Winner).ToString("F0")+"%)":qualifiedCandidate;
        bool localHold;
        string token, sessionId, currentMedia;
        Snapshot snapshot;
        readonly float[] dwell = new float[3];
        string candidate = "", qualifiedCandidate = "";
        float candidateSeconds, reportAt, cycleSeconds;
        int cycle;
        bool hadTracking = true, busyAttention;
        Texture2D currentTexture;
        readonly System.Collections.Generic.List<string> videoFiles=new System.Collections.Generic.List<string>();

        [Serializable] class PairRequest { public string code; }
        [Serializable] class PairReply { public string token; public string session_id; }
        [Serializable] public class Media { public string kind; public string url; public float duration; public bool region_map_verified, entry; public string first_url, final_url, final_hash, job_id; }
        [Serializable] public class Proposal { public string region; public string reason; }
        [Serializable] public class Snapshot { public string id; public string source_hash; public string status; public int cycle; public bool pendingCycle; public string region; public Media media; public Proposal proposal; }
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
                        status = "Disconnected — playback paused"; snapshot = null; if(transition)transition.Hold=true; if (videoPlayer) videoPlayer.Pause();
                    }
                    else
                    {
                        snapshot = JsonUtility.FromJson<Snapshot>(request.downloadHandler.text); status = snapshot.status;
                        if (snapshot.status != "active") localHold = false;
                        if(transition)transition.Hold=!Active;
                        if(snapshot.status=="completed"&&transition)transition.Cancel();
                        if (snapshot.cycle != cycle) { cycle = snapshot.cycle; cycleSeconds = 0; candidate = qualifiedCandidate = ""; candidateSeconds = 0; Array.Clear(dwell, 0, dwell.Length); spatial=new RegionAttention(); }
                        if (snapshot.status != "active" || snapshot.pendingCycle) { if (videoPlayer) videoPlayer.Pause(); }
                        if (snapshot.proposal != null) { suggestedRegion = snapshot.proposal.region; suggestionReason = snapshot.proposal.reason; }
                        if (snapshot.media != null && snapshot.media.region_map_verified && snapshot.media.url != currentMedia)
                        { currentMedia = snapshot.media.url; StartCoroutine(LoadMedia(snapshot.media)); }
                        if ((!transition || !transition.Busy) && snapshot.media != null && !snapshot.media.entry && snapshot.status == "active" && !snapshot.pendingCycle && !localHold && videoPlayer && videoPlayer.isPrepared && !videoPlayer.isPlaying && videoPlayer.time < videoPlayer.length - .1) videoPlayer.Play();
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
                if (media.kind == "video") {videoFiles.Add(file);request.downloadHandler = new DownloadHandlerFile(file);}
                yield return request.SendWebRequest();
                if (request.result != UnityWebRequest.Result.Success) { status = "Media unavailable; previous scene retained"; currentMedia = null; yield break; }
                if (media.kind == "image")
                {
                    if(media.url.Contains("/scene?")&&!string.IsNullOrEmpty(SourceHash))
                    {
                        using(var sha=System.Security.Cryptography.SHA256.Create())
                        {
                            string actual=BitConverter.ToString(sha.ComputeHash(request.downloadHandler.data)).Replace("-","").ToLowerInvariant();
                            if(actual!=SourceHash){status="Source hash mismatch; image retained";currentMedia=null;yield break;}
                        }
                    }
                    var texture = new Texture2D(2, 2);
                    if (texture.LoadImage(request.downloadHandler.data)) { if (videoPlayer) videoPlayer.Stop(); if (currentTexture) Destroy(currentTexture); currentTexture = texture; landscapeRenderer.material.mainTexture = texture; }
                    else { Destroy(texture); status = "Image could not be decoded"; }
                }
                else if (videoPlayer)
                {
                    videoPlayer.source = VideoSource.Url; videoPlayer.url = file; videoPlayer.renderMode = VideoRenderMode.APIOnly;
                    videoPlayer.targetMaterialRenderer = landscapeRenderer; videoPlayer.targetMaterialProperty = "_MainTex"; videoPlayer.Prepare();
                    float deadline = Time.realtimeSinceStartup + 15;
                    while (!videoPlayer.isPrepared && Time.realtimeSinceStartup < deadline) yield return null;
                    if (videoPlayer.isPrepared && media.entry && transition)
                    {
                        Texture2D first=null,final=null;
                        yield return DownloadTexture(media.first_url,t=>first=t);
                        yield return DownloadTexture(media.final_url,t=>final=t);
                        if(first&&final&&Active)
                        {
                            yield return transition.Run(first,final);
                            if(transition.State=="Exploring")
                            {
                                if(currentTexture)Destroy(currentTexture);currentTexture=final;Destroy(first);
                                using(var done=JsonRequest("/api/sessions/"+sessionId+"/transition-complete", "{\"job_id\":\""+media.job_id+"\"}"))
                                {yield return done.SendWebRequest();if(done.result!=UnityWebRequest.Result.Success)status="Transition acknowledgement failed; pause and reconcile";}
                            }
                        }
                        else {if(first)Destroy(first);if(final)Destroy(final);status="Bundle unavailable; previous image retained";currentMedia=null;}
                    }
                    else if (videoPlayer.isPrepared && Active) videoPlayer.Play();
                    else status = "Video not ready; playback held";
                }
            }
        }
        void Update()
        {
            if (localHold || snapshot == null || snapshot.status != "active" || snapshot.pendingCycle || !trackedHead || !landscapeCollider) return;
            bool tracked = attentionInput && attentionInput.Valid;
            if (!tracked) { if (hadTracking) { localHold = true; if(transition)transition.Hold=true; if (videoPlayer) videoPlayer.Pause(); Send("tracking_lost"); } hadTracking = false; return; }
            hadTracking = true;
            if(transition&&transition.Busy)return;
            cycleSeconds += Time.deltaTime;
            // Spatial cycles end explicitly after guide speech; generation wait has no exploration deadline.
            RaycastHit hit;
            if (landscapeCollider.Raycast(attentionInput.LookRay, out hit, 10))
            {
                spatial.Sample(Time.deltaTime,voice&&voice.GuideSpeaking,true,hit.textureCoord,voice?voice.SpeechWindow:"");
                int index = Mathf.Min(2, Mathf.FloorToInt(Mathf.Clamp01(hit.textureCoord.x) * 3));
                string region = new[] { "sky", "ridge", "water" }[index];
                if (candidate != region) { candidate = region; candidateSeconds = 0; }
                candidateSeconds += Time.deltaTime;
                if (candidateSeconds >= dwellThreshold) { qualifiedCandidate = candidate; dwell[index] += Time.deltaTime; }
            }
            else { spatial.Sample(Time.deltaTime,voice&&voice.GuideSpeaking,false,Vector2.zero,voice?voice.SpeechWindow:""); candidate = ""; candidateSeconds = 0; }
            if (string.IsNullOrEmpty(SourceHash) && Time.unscaledTime >= reportAt && !busyAttention) { reportAt = Time.unscaledTime + 1; StartCoroutine(ReportAttention()); }
        }
        IEnumerator ReportAttention()
        {
            busyAttention = true;
            var command = NewCommand("attention");
            command.payload.dwell = new Dwell { sky = Mathf.Min(30, dwell[0]), ridge = Mathf.Min(30, dwell[1]), water = Mathf.Min(30, dwell[2]) };
            yield return SendRoutine(command); busyAttention = false;
        }
        Command NewCommand(string name) { return new Command { command_id = Guid.NewGuid().ToString(), command = name, payload = new Payload { cycle = cycle } }; }
        [Serializable] class ManualPoint {public int cycle;public string source_hash,input_mode;public float x,y;}
        public void FreezeSpatialDecision()
        {
            if(!Active||transition.Busy)return;
            if(spatial.ValidSeconds<.5f)
            {
                if(landscapeCollider.Raycast(attentionInput.LookRay,out RaycastHit hit,20))
                    StartCoroutine(SendSpatialJson(JsonUtility.ToJson(new ManualPoint{cycle=cycle,source_hash=SourceHash,input_mode=attentionInput.Source,x=hit.textureCoord.x,y=1-hit.textureCoord.y}),"spatial_select"));
                else status="Look at the image to explicitly confirm a region";
                return;
            }
            try{var decision=spatial.Freeze(cycle,SourceHash,attentionInput.Source);StartCoroutine(SendSpatialJson(JsonUtility.ToJson(decision),"spatial_decision"));}
            catch(InvalidOperationException e){status=e.Message;}
        }
        IEnumerator SendSpatialJson(string payload,string name)
        {
            string json="{\"command_id\":\""+Guid.NewGuid()+"\",\"command\":\""+name+"\",\"payload\":"+payload+"}";
            using(var request=JsonRequest("/api/sessions/"+sessionId+"/commands",json))
            {yield return request.SendWebRequest();status=request.result==UnityWebRequest.Result.Success?"Spatial decision frozen; review in Media studio":"Spatial decision rejected";}
        }
        IEnumerator DownloadTexture(string url,Action<Texture2D> receive)
        {
            using(var request=UnityWebRequest.Get(serverUrl.TrimEnd('/')+url))
            {
                request.SetRequestHeader("Authorization","Bearer "+token);request.timeout=30;yield return request.SendWebRequest();
                if(request.result!=UnityWebRequest.Result.Success)yield break;
                var texture=new Texture2D(2,2);if(texture.LoadImage(request.downloadHandler.data))receive(texture);else Destroy(texture);
            }
        }
        public void ConfirmLookedRegion() { if(!string.IsNullOrEmpty(SourceHash)){FreezeSpatialDecision();return;} if (Active && !string.IsNullOrEmpty(qualifiedCandidate)) { var cmd = NewCommand("select"); cmd.payload.region = qualifiedCandidate; StartCoroutine(SendRoutine(cmd)); } }
        public void Pause() { localHold = true; if(transition)transition.Hold=true; if (videoPlayer) videoPlayer.Pause(); Send("pause"); }
        public void StopSession() { localHold = true; if(transition)transition.Cancel(); if (videoPlayer) videoPlayer.Stop(); Send("stop"); }
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
        void OnDisable() { if(transition)transition.Cancel(); if (videoPlayer) videoPlayer.Stop(); token = null; if (currentTexture) Destroy(currentTexture); foreach(var file in videoFiles) {try{File.Delete(file);}catch(IOException){}} }
    }
}
