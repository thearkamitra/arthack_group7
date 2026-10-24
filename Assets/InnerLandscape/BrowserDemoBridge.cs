using System;
using System.Collections;
using UnityEngine;
using UnityEngine.Networking;
namespace InnerLandscape
{
    // Only runtime JPEG previews and control heartbeats; no audio or credentials in frames.
    public sealed class BrowserDemoBridge : MonoBehaviour
    {
        public SessionClient session;
        [Serializable] public class State {public bool enabled,connected,headset,busy,speaking,frame_ready,voice_frontend;public float yaw,pitch;public int freeze;public string window_id;}
        [Serializable] class Offer {public string code;}
        [Serializable] class Presence {public string input_mode,frame;public bool busy;}
        public State state=new State();
        public bool Remote => state.enabled&&!state.headset&&session.attentionInput.mode!=AttentionInput.Mode.XR;
        public bool GuideSpeaking => state.voice_frontend&&state.speaking;
        public string SpeechWindow => state.window_id;
        int frozen; float received;
        public bool Fresh => Time.realtimeSinceStartup-received<1;
        RenderTexture target;Texture2D capture;
        void Start(){StartCoroutine(Loop());}
        UnityWebRequest Post(string path,string json,bool auth=true)
        {
            var r=new UnityWebRequest(session.serverUrl.TrimEnd('/')+path,"POST");
            r.uploadHandler=new UploadHandlerRaw(System.Text.Encoding.UTF8.GetBytes(json));r.downloadHandler=new DownloadHandlerBuffer();r.SetRequestHeader("Content-Type","application/json");
            if(auth)r.SetRequestHeader("Authorization","Bearer "+session.ParticipantToken);r.timeout=2;return r;
        }
        IEnumerator Loop()
        {
            while(true)
            {
                if(string.IsNullOrEmpty(session.ParticipantToken))
                {
#if UNITY_EDITOR
                    using(var request=Post("/api/demo/editor-offer","{}",false))
                    {
                        yield return request.SendWebRequest();
                        if(request.result==UnityWebRequest.Result.Success){session.pairingCode=JsonUtility.FromJson<Offer>(request.downloadHandler.text).code;session.Pair();}
                    }
#endif
                    yield return new WaitForSecondsRealtime(1);continue;
                }
                var input=session.attentionInput;
                bool xr=input.mode==AttentionInput.Mode.XR&&input.Valid;
                string frame="";
                if(state.enabled&&!xr)
                {
                    if(!target){target=new RenderTexture(960,540,24);capture=new Texture2D(960,540,TextureFormat.RGB24,false);}
                    var camera=session.trackedHead;var oldTarget=camera.targetTexture;var oldActive=RenderTexture.active;
                    camera.targetTexture=target;camera.Render();RenderTexture.active=target;
                    capture.ReadPixels(new Rect(0,0,960,540),0,0);capture.Apply();frame=Convert.ToBase64String(capture.EncodeToJPG(75));
                    camera.targetTexture=oldTarget;RenderTexture.active=oldActive;
                }
                using(var request=Post("/api/sessions/"+session.SessionId+"/demo/presence",JsonUtility.ToJson(new Presence{input_mode=xr?"xr":"editor",busy=session.transition.Busy,frame=frame})))
                {
                    yield return request.SendWebRequest();
                    if(request.result==UnityWebRequest.Result.Success)
                    {
                        state=JsonUtility.FromJson<State>(request.downloadHandler.text);received=Time.realtimeSinceStartup;
                        if(Remote&&state.freeze!=frozen){frozen=state.freeze;session.FreezeSpatialDecision();}
                    }
                    else {state.speaking=false;}
                }
                yield return new WaitForSecondsRealtime(.2f);
            }
        }
        void OnDisable(){StopAllCoroutines();if(target){target.Release();Destroy(target);}if(capture)Destroy(capture);}
    }
}
