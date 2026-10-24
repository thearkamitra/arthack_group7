using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.Networking;
namespace InnerLandscape
{
    // Test harness only: fictional dialogue and scripted rays. No provider keys.
    public sealed class RegionZoomDemo : MonoBehaviour
    {
        [Serializable] public class Request { public string server, code, audio, directory, scenario; }
        [Serializable] class Evidence { public string state; public float time; public int winner; public float valid_seconds; }
        [Serializable] class Pose { public string state;public bool hold;public float x,y,z;public double video_time; }
        public Request request;
        SessionClient session; VoiceClient voice; Camera head;
        readonly List<string> states=new List<string>();
        float captureAt; int frame;
        IEnumerator Start()
        {
            yield return null;
            session=FindAnyObjectByType<SessionClient>();voice=FindAnyObjectByType<VoiceClient>();head=Camera.main;
            yield return CheckCancel();
            session.serverUrl=request.server;session.pairingCode=request.code;session.Pair();
            session.attentionInput.mode=AttentionInput.Mode.Scripted;
            session.attentionInput.scriptedPoint=Point(0);
            float deadline=Time.realtimeSinceStartup+30;
            while(!session.Active&&Time.realtimeSinceStartup<deadline)yield return null;
            while((string.IsNullOrEmpty(session.SourceHash)||!session.ImageReady)&&Time.realtimeSinceStartup<deadline)yield return null;
            if(!session.Active||string.IsNullOrEmpty(session.SourceHash)){Record("PairFailed");yield break;}
            using(var audio=UnityWebRequestMultimedia.GetAudioClip(new Uri(request.audio).AbsoluteUri,AudioType.WAV))
            {
                yield return audio.SendWebRequest();
                if(audio.result!=UnityWebRequest.Result.Success){Record("AudioFailed");yield break;}
                var clip=DownloadHandlerAudioClip.GetContent(audio);
                Record("Baseline");yield return Capture("baseline");
                voice.PlaySyntheticGuide(clip);
                float start=Time.time;
                while(voice.GuideSpeaking)
                {
                    session.attentionInput.scriptedPoint=Point((Time.time-start)/clip.length);
                    yield return null;
                }
            }
            yield return null;
            Record("AttentionComplete");yield return Capture("attention-complete");
            File.WriteAllText(Path.Combine(request.directory,"unity-attention.json"),JsonUtility.ToJson(session.spatial.Freeze(session.Cycle,session.SourceHash,"scripted"),true));
            session.FreezeSpatialDecision();
            session.transition.Changed+=Transition;
            session.transition.Completed+=()=>{session.attentionInput.scriptedPoint=new Vector2(.5f,.5f);File.WriteAllText(Path.Combine(request.directory,"unity-complete.json"),"{\"transition_complete\":true}");};
        }
        IEnumerator CheckCancel()
        {
            var surface=session.landscapeRenderer;var position=surface.transform.position;var rotation=surface.transform.rotation;var image=surface.material.mainTexture;
            bool completed=false;Action observer=()=>completed=true;session.transition.Completed+=observer;
            session.StartCoroutine(session.transition.Run(image,image));yield return new WaitForSecondsRealtime(.05f);
            session.transition.Cancel();yield return new WaitForSecondsRealtime(.1f);session.transition.Completed-=observer;
            if(session.transition.Busy||completed||Vector3.Distance(position,surface.transform.position)>.0001f||Quaternion.Angle(rotation,surface.transform.rotation)>.001f||surface.material.mainTexture!=image)
                throw new InvalidOperationException("Cancel must restore the stable image and presentation pose without completion");
            File.WriteAllText(Path.Combine(request.directory,"cancel-check.json"),"{\"restored_pose_and_image\":true,\"no_completion\":true}");
        }
        Vector2 Point(float fraction)
        {
            if(request.scenario=="upper-left")return fraction<.7f?new Vector2(.2f,.08f):fraction<.8f?new Vector2(.84f,.84f):new Vector2(.5f,.5f);
            return fraction<.8f?new Vector2(.5f,.5f):new Vector2(.84f,.84f);
        }
        void Update()
        {
            if(!session||!session.transition.Busy||Time.unscaledTime<captureAt)return;
            captureAt=Time.unscaledTime+.1f;
            var p=session.landscapeRenderer.transform.position;
            File.AppendAllText(Path.Combine(request.directory,"pose-samples.jsonl"),JsonUtility.ToJson(new Pose{state=session.transition.State,hold=session.transition.Hold,x=p.x,y=p.y,z=p.z,video_time=session.videoPlayer.time})+"\n");
            Directory.CreateDirectory(Path.Combine(request.directory,"frames"));
            StartCoroutine(Capture("frames/frame-"+(frame++).ToString("D4")));
        }
        void Transition(string state){Record(state);StartCoroutine(Capture(state));if(state=="Exploring")StartCoroutine(Finish());}
        IEnumerator Finish()
        {
            yield return new WaitForSecondsRealtime(2);
#if UNITY_EDITOR
            UnityEditor.EditorApplication.isPlaying=false;
#endif
        }
        void Record(string state)
        {
            states.Add(state);
            if(state=="SwapStartFrame")
            {
                float minX=1,minY=1,maxX=0,maxY=0;
                foreach(var vertex in session.landscapeRenderer.GetComponent<MeshFilter>().sharedMesh.vertices)
                {
                    var point=head.WorldToViewportPoint(session.landscapeRenderer.transform.TransformPoint(vertex));
                    minX=Mathf.Min(minX,point.x);maxX=Mathf.Max(maxX,point.x);minY=Mathf.Min(minY,point.y);maxY=Mathf.Max(maxY,point.y);
                }
                File.WriteAllText(Path.Combine(request.directory,"fit.json"),"{\"min_x\":"+minX.ToString(System.Globalization.CultureInfo.InvariantCulture)+",\"max_x\":"+maxX.ToString(System.Globalization.CultureInfo.InvariantCulture)+",\"min_y\":"+minY.ToString(System.Globalization.CultureInfo.InvariantCulture)+",\"max_y\":"+maxY.ToString(System.Globalization.CultureInfo.InvariantCulture)+"}");
            }
            File.AppendAllText(Path.Combine(request.directory,"unity-states.jsonl"),JsonUtility.ToJson(new Evidence{state=state,time=Time.realtimeSinceStartup,winner=session.spatial.Winner,valid_seconds=session.spatial.ValidSeconds})+"\n");
        }
        IEnumerator Capture(string name)
        {
            yield return null;
            var target=new RenderTexture(1280,720,24);head.targetTexture=target;head.Render();
            var previous=RenderTexture.active;RenderTexture.active=target;
            var image=new Texture2D(1280,720,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,1280,720),0,0);image.Apply();
            File.WriteAllBytes(Path.Combine(request.directory,name.Replace(' ','_')+".png"),image.EncodeToPNG());
            head.targetTexture=null;RenderTexture.active=previous;target.Release();Destroy(target);Destroy(image);
        }
    }
}
