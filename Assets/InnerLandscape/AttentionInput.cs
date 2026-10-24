using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.XR;
using System.Collections.Generic;
using CommonUsages = UnityEngine.XR.CommonUsages;
namespace InnerLandscape
{
    public sealed class AttentionInput : MonoBehaviour
    {
        public enum Mode { XR, Mouse, Scripted }
        public Mode mode=Mode.Mouse;
        public Camera head;
        public CurvedLandscape surface;
        public RegionZoomTransition transition;
        public Vector2 scriptedPoint=new Vector2(.5f,.5f); // top-left origin
        public bool Valid { get; private set; }
        public Ray LookRay { get; private set; }
        readonly List<XRInputSubsystem> systems=new List<XRInputSubsystem>();
        void Start(){SubsystemManager.GetSubsystems(systems);}
        public string Source => mode==Mode.XR?"xr":mode==Mode.Mouse?"mouse":"scripted";
        float HeightOffset(){foreach(var system in systems)if(system.GetTrackingOriginMode()==TrackingOriginModeFlags.Floor)return 0;return 1.6f;}
        void OnGUI()
        {
            if(mode==Mode.XR)return;
            GUI.Label(new Rect(12,12,550,28),"MOCK HEAD INPUT · right-drag to look · head direction, not eye tracking");
            var session=GetComponent<SessionClient>();
            if(session&&session.spatial.ValidSeconds>0)GUI.Label(new Rect(12,40,600,28),"Longest dwell: cell "+(session.spatial.Winner+1)+" · "+session.spatial.Percentage(session.spatial.Winner).ToString("F1")+"% · valid "+session.spatial.ValidSeconds.ToString("F1")+"s");
            GUI.Label(new Rect(Screen.width/2-6,Screen.height/2-12,20,24),"+");
        }
        void Update()
        {
            if(!head||!surface)return;
            if(mode==Mode.XR)
            {
                var device=InputDevices.GetDeviceAtXRNode(XRNode.Head);
                Valid=device.TryGetFeatureValue(CommonUsages.isTracked,out bool tracked)&&tracked;
                if(Valid){if(device.TryGetFeatureValue(CommonUsages.devicePosition,out Vector3 p))head.transform.localPosition=p+Vector3.up*HeightOffset();if(device.TryGetFeatureValue(CommonUsages.deviceRotation,out Quaternion q))head.transform.localRotation=q;}
                LookRay=new Ray(head.transform.position,head.transform.forward);return;
            }
            Valid=true;
            if(transition&&transition.Busy){LookRay=new Ray(head.transform.position,head.transform.forward);return;}
            if(mode==Mode.Scripted)
            {
                Vector3 target=surface.Point(new Vector2(scriptedPoint.x,1-scriptedPoint.y));
                head.transform.rotation=Quaternion.LookRotation(target-head.transform.position,Vector3.up);
            }
            else if(Mouse.current!=null&&Mouse.current.rightButton.isPressed)
            {
                Vector2 delta=Mouse.current.delta.ReadValue();var angles=head.transform.eulerAngles;
                head.transform.rotation=Quaternion.Euler(Mathf.Clamp(Mathf.DeltaAngle(0,angles.x)-delta.y*.12f,-70,70),angles.y+delta.x*.12f,0);
            }
            LookRay=new Ray(head.transform.position,head.transform.forward);
        }
    }
}
