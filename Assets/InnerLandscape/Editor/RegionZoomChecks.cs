using System;
using System.IO;
using UnityEditor;
using UnityEngine;
namespace InnerLandscape.Editor
{
    public static class RegionZoomChecks
    {
        public static void Run()
        {
            var a=new RegionAttention();
            a.Sample(7,true,true,new Vector2(.2f,.92f),"turn");a.Sample(1,true,true,new Vector2(.84f,.16f),"turn");a.Sample(2,true,true,new Vector2(.5f,.5f),"turn");
            a.Sample(20,false,true,new Vector2(.5f,.5f),"outside");
            var d=a.Freeze(1,"source","scripted");
            Require(a.Winner==0&&Mathf.Abs(d.cells[0].y-.08f)<.0001f,"Upper-left UV conversion and longest dwell");
            Require(Mathf.Abs(a.ValidSeconds-10)<.001f,"Speech gating");
            var obj=new GameObject("fit test",typeof(CurvedLandscape));obj.transform.position=Vector3.up*1.6f;
            // Awake is not invoked by AddComponent outside play mode; enter temporary play is unnecessary for pure vertex geometry.
            var mesh=new Mesh();var points=new Vector3[130];
            for(int i=0;i<=64;i++){float angle=(i/64f-.5f)*110*Mathf.Deg2Rad;points[i*2]=new Vector3(Mathf.Sin(angle)*3,-1.4f,Mathf.Cos(angle)*3);points[i*2+1]=points[i*2]+Vector3.up*2.8f;}
            mesh.vertices=points;obj.GetComponent<MeshFilter>().sharedMesh=mesh;
            var camera=new GameObject("fit camera",typeof(Camera)).GetComponent<Camera>();camera.transform.position=Vector3.up*1.6f;
            foreach(float aspect in new[]{.6f,16f/9f,2.4f})
            {
                camera.aspect=aspect;camera.transform.position=Vector3.up*1.6f;
                camera.transform.position-=Vector3.forward*LandscapeFraming.Pullback(camera,obj.GetComponent<MeshFilter>());
                foreach(var p in points){var v=camera.WorldToViewportPoint(obj.transform.TransformPoint(p));Require(v.x>=0&&v.x<=1&&v.y>=0&&v.y<=1&&v.z>0,"All curved boundary vertices fit");}
            }
            UnityEngine.Object.DestroyImmediate(camera.gameObject);UnityEngine.Object.DestroyImmediate(obj);UnityEngine.Object.DestroyImmediate(mesh);
            Directory.CreateDirectory("work/region_zoom_tests");File.WriteAllText("work/region_zoom_tests/unity-checks.json","{\"upper_left\":true,\"speech_gating\":true,\"curved_fit_aspects\":[0.6,1.7777778,2.4]}");
        }
        static void Require(bool value,string message){if(!value)throw new Exception(message);}
    }
}
