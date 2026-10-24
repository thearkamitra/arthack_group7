using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;
using UnityEngine.Video;
using UnityEngine.XR;
using CommonUsages = UnityEngine.XR.CommonUsages;
using System.Collections.Generic;

namespace InnerLandscape
{
    // Builds a small world-space control panel; head ray + trigger works without locomotion.
    public sealed class LandscapeApp : MonoBehaviour
    {
        public Material landscapeMaterial;
        SessionClient session;
        VoiceClient voice;
        Camera head;
        Canvas canvas;
        Text feedback;
        InputField address, code;
        EventSystem events;
        GraphicRaycaster raycaster;
        bool pressed;
        readonly List<XRInputSubsystem> trackingSystems = new List<XRInputSubsystem>();
        readonly List<RaycastResult> hits = new List<RaycastResult>();
        void Start()
        {
            var cameraObject = new GameObject("Tracked head", typeof(Camera), typeof(AudioListener));
            head = cameraObject.GetComponent<Camera>(); head.tag = "MainCamera";
            head.clearFlags = CameraClearFlags.SolidColor; head.backgroundColor = new Color(.88f,.92f,.88f);
            head.transform.position = new Vector3(0,1.6f,0); head.nearClipPlane = .05f;
            SubsystemManager.GetSubsystems(trackingSystems);
            foreach(var system in trackingSystems)system.TrySetTrackingOriginMode(TrackingOriginModeFlags.Device);
            var landscape = new GameObject("World anchored landscape", typeof(CurvedLandscape));
            landscape.transform.position = new Vector3(0,1.6f,0);
            var renderer = landscape.GetComponent<MeshRenderer>();
            renderer.material = landscapeMaterial ? new Material(landscapeMaterial) : new Material(Shader.Find("Universal Render Pipeline/Unlit"));
            if(renderer.material.HasProperty("_Cull")) renderer.material.SetFloat("_Cull", 0);
            var video = landscape.AddComponent<VideoPlayer>();
            session = gameObject.AddComponent<SessionClient>();
            session.trackedHead = head; session.landscapeCollider = landscape.GetComponent<MeshCollider>();
            session.landscapeRenderer = renderer; session.videoPlayer = video;
            video.isLooping = false; video.playOnAwake = false; video.audioOutputMode = VideoAudioOutputMode.None;
            voice = gameObject.AddComponent<VoiceClient>(); voice.session = session;
            events = new GameObject("UI events", typeof(EventSystem)).GetComponent<EventSystem>();
            canvas = new GameObject("Session controls", typeof(Canvas), typeof(GraphicRaycaster)).GetComponent<Canvas>();
            canvas.renderMode = RenderMode.WorldSpace; canvas.worldCamera = head;
            canvas.transform.position = new Vector3(0,.55f,1.7f); canvas.transform.localScale = Vector3.one * .002f;
            canvas.GetComponent<RectTransform>().sizeDelta = new Vector2(760,480);
            raycaster = canvas.GetComponent<GraphicRaycaster>();
            Label("INNER LANDSCAPE · Head direction, not eye tracking",190);
            address = Field("Mac LAN URL", "http://192.168.1.10:4173",140);
            code = Field("Pairing code", "",85); code.characterLimit = 8;
            Button("Pair", -240,25,()=> { session.serverUrl=address.text.Trim(); session.pairingCode=code.text.Trim(); session.Pair(); });
            Button("Confirm region",0,25,session.ConfirmLookedRegion);
            Button("Next cycle",240,25,session.NextCycle);
            Button("Pause",-240,-30,()=>{session.Pause();voice.StopVoice();});
            Button("Stop",0,-30,()=>{session.StopSession();voice.StopVoice();});
            Button("Start voice",240,-30,voice.StartVoice);
            Label("Voice sends microphone audio to ElevenLabs. Press Start voice to consent.",-85);
            Label("Look at a button and press trigger. Resume is controlled by your practitioner.",-120);
            feedback = Label("Not paired",-170);
        }
        Font font => Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        RectTransform Place(GameObject obj,float x,float y,float w,float h)
        {
            obj.transform.SetParent(canvas.transform,false); var r=obj.GetComponent<RectTransform>();
            r.sizeDelta=new Vector2(w,h);r.anchoredPosition=new Vector2(x,y);return r;
        }
        Text Label(string text,float y)
        {
            var obj=new GameObject("Label",typeof(RectTransform),typeof(Text)); Place(obj,0,y,740,42);
            var t=obj.GetComponent<Text>();t.font=font;t.fontSize=18;t.color=new Color(.12f,.22f,.18f);t.alignment=TextAnchor.MiddleCenter;t.text=text;t.raycastTarget=false;return t;
        }
        InputField Field(string title,string value,float y)
        {
            var obj=new GameObject(title,typeof(RectTransform),typeof(Image),typeof(InputField));Place(obj,0,y,690,45);
            var child=new GameObject("Text",typeof(RectTransform),typeof(Text));child.transform.SetParent(obj.transform,false);
            var r=child.GetComponent<RectTransform>();r.anchorMin=Vector2.zero;r.anchorMax=Vector2.one;r.offsetMin=new Vector2(10,0);r.offsetMax=new Vector2(-10,0);
            var t=child.GetComponent<Text>();t.font=font;t.fontSize=22;t.color=Color.black;t.alignment=TextAnchor.MiddleLeft;
            var field=obj.GetComponent<InputField>();field.textComponent=t;field.text=value;return field;
        }
        void Button(string title,float x,float y,UnityEngine.Events.UnityAction action)
        {
            var obj=new GameObject(title,typeof(RectTransform),typeof(Image),typeof(Button));Place(obj,x,y,220,44);
            obj.GetComponent<Image>().color=new Color(.65f,.79f,.68f);obj.GetComponent<Button>().onClick.AddListener(action);
            var label=Label(title,0);label.transform.SetParent(obj.transform,false);label.rectTransform.sizeDelta=new Vector2(220,44);
        }
        void Update()
        {
            if(!head)return;
            var device=InputDevices.GetDeviceAtXRNode(XRNode.Head);
            float heightOffset=1.6f;
            foreach(var system in trackingSystems)if(system.GetTrackingOriginMode()==TrackingOriginModeFlags.Floor)heightOffset=0;
            if(device.TryGetFeatureValue(CommonUsages.devicePosition,out Vector3 p)) head.transform.localPosition=p+Vector3.up*heightOffset;
            if(device.TryGetFeatureValue(CommonUsages.deviceRotation,out Quaternion q))head.transform.localRotation=q;
            bool down=false;
            foreach(var node in new[]{XRNode.LeftHand,XRNode.RightHand})
            { var hand=InputDevices.GetDeviceAtXRNode(node);hand.TryGetFeatureValue(CommonUsages.triggerButton,out bool trigger);down|=trigger; }
            down|=Mouse.current!=null&&Mouse.current.leftButton.isPressed;
            var pointer=new PointerEventData(events){position=new Vector2(head.pixelWidth/2f,head.pixelHeight/2f)};
            if(!device.isValid&&Mouse.current!=null)pointer.position=Mouse.current.position.ReadValue();
            hits.Clear();raycaster.Raycast(pointer,hits);
            if(down&&!pressed&&hits.Count>0)
            {
                var target=hits[0].gameObject;
                var input=target.GetComponentInParent<InputField>();
                if(input)
                {
#if UNITY_ANDROID && !UNITY_EDITOR
                    keyboard=TouchScreenKeyboard.Open(input.text,TouchScreenKeyboardType.Default,false,false,false,false,input.name);
                    editing=input;
#else
                    editing=input;
#endif
                }
                else ExecuteEvents.ExecuteHierarchy(target,pointer,ExecuteEvents.pointerClickHandler);
            }
            if(down&&!pressed&&hits.Count==0)session.ConfirmLookedRegion();
            pressed=down;
#if UNITY_ANDROID && !UNITY_EDITOR
            if(keyboard!=null&&editing) {editing.text=keyboard.text;if(keyboard.status!=TouchScreenKeyboard.Status.Visible){keyboard=null;editing=null;}}
#else
            if(editing&&Keyboard.current!=null)
            { if(Keyboard.current.backspaceKey.wasPressedThisFrame&&editing.text.Length>0)editing.text=editing.text.Substring(0,editing.text.Length-1); }
#endif
            feedback.text=session.status+" · Looking: "+session.LookedRegion+"\n"+voice.status;
        }
        InputField editing;
#if UNITY_ANDROID && !UNITY_EDITOR
        TouchScreenKeyboard keyboard;
#endif
        void OnEnable(){if(Keyboard.current!=null)Keyboard.current.onTextInput+=Type;}
        void OnDisable(){if(Keyboard.current!=null)Keyboard.current.onTextInput-=Type;}
        void Type(char c){if(editing&&!char.IsControl(c))editing.text+=c;}
    }
}
