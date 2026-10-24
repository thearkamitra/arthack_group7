using System;
using System.Collections;
using UnityEngine;
using UnityEngine.Video;
namespace InnerLandscape
{
    public sealed class RegionZoomTransition : MonoBehaviour
    {
        public Camera head; public Renderer surface; public VideoPlayer video;
        public float pullbackSeconds=1, approachSeconds=1;
        public string State { get; private set; }="Exploring";
        public bool Busy { get; private set; }
        public bool Hold;
        public event Action<string> Changed;
        public event Action Completed;
        bool videoEnded, videoFailed;
        int epoch;
        Vector3 home; Quaternion homeRotation;
        Texture stable;
        void Set(string state){State=state;Changed?.Invoke(state);}
        public void Cancel()
        {
            ++epoch;bool wasBusy=Busy;
            StopAllCoroutines();if(video)video.Stop();
            if(Busy){surface.transform.position=home;surface.transform.rotation=homeRotation;if(stable)surface.material.mainTexture=stable;surface.material.SetFloat("_Blend",0);}
            Busy=false;if(wasBusy)Set("Cancelled");
        }
        void End(VideoPlayer p){videoEnded=true;}
        void Failed(VideoPlayer p,string error){videoFailed=true;}
        void Awake(){if(video){video.loopPointReached+=End;video.errorReceived+=Failed;}}
        public IEnumerator Run(Texture first,Texture final)
        {
            if(Busy)yield break;
            video.loopPointReached-=End;video.errorReceived-=Failed;
            video.loopPointReached+=End;video.errorReceived+=Failed;
            int generation=++epoch;Busy=true;home=surface.transform.position;homeRotation=surface.transform.rotation;stable=surface.material.mainTexture;
            // Rotate presentation around the viewer, preserving the current tracked pose.
            Quaternion targetRotation=Quaternion.LookRotation(head.transform.forward,head.transform.up);
            surface.transform.rotation=targetRotation;
            Vector3 retreat=head.transform.forward*LandscapeFraming.Pullback(head,surface.GetComponent<MeshFilter>());
            surface.transform.rotation=homeRotation;
            Set("PullBack");yield return Move(home,home+retreat,pullbackSeconds,generation,homeRotation,targetRotation);
            if(generation!=epoch)yield break;
            Set("SwapStartFrame");surface.material.SetTexture("_NextTex",first);
            float wait=0;while(wait<.35f&&generation==epoch){if(!Hold)wait+=Time.unscaledDeltaTime;surface.material.SetFloat("_Blend",Mathf.Clamp01(wait/.35f));yield return null;}
            if(generation!=epoch)yield break;
            surface.material.mainTexture=first;surface.material.SetFloat("_Blend",0);
            Set("PlayVideo");videoEnded=videoFailed=false;
            video.Play();float elapsed=0;
            while(generation==epoch&&!videoEnded&&!videoFailed&&elapsed<video.length+5)
            {
                if(Hold){video.Pause();}else{if(!video.isPlaying)video.Play();if(video.texture)surface.material.mainTexture=video.texture;elapsed+=Time.unscaledDeltaTime;}
                yield return null;
            }
            if(generation!=epoch)yield break;
            if(videoFailed||!videoEnded){Cancel();Set("Failed; previous image retained");yield break;}
            video.Stop();surface.material.mainTexture=final;stable=final;
            Set("Approach");yield return Move(home+retreat,home,approachSeconds,generation);
            if(generation!=epoch)yield break;
            Busy=false;Set("Exploring");Completed?.Invoke();
        }
        IEnumerator Move(Vector3 from,Vector3 to,float duration,int generation,Quaternion? fromRotation=null,Quaternion? toRotation=null)
        {
            float t=0;while(t<duration&&generation==epoch){if(!Hold)t+=Time.unscaledDeltaTime;float eased=Mathf.SmoothStep(0,1,t/Mathf.Max(.01f,duration));surface.transform.position=Vector3.Lerp(from,to,eased);if(fromRotation.HasValue)surface.transform.rotation=Quaternion.Slerp(fromRotation.Value,toRotation.Value,eased);yield return null;}
            if(generation==epoch)surface.transform.position=to;
        }
        void OnDisable(){Cancel();if(video){video.loopPointReached-=End;video.errorReceived-=Failed;}}
    }
}
