using UnityEngine;
namespace InnerLandscape
{
    public static class LandscapeFraming
    {
        // Camera local +Z is forward. Fit every vertex, including bowed edges.
        public static float Pullback(Camera camera, MeshFilter surface, float margin=.94f)
        {
            float vertical=Mathf.Tan(camera.fieldOfView*.5f*Mathf.Deg2Rad)*margin;
            float horizontal=vertical*camera.aspect, distance=0;
            foreach(var vertex in surface.sharedMesh.vertices)
            {
                var p=camera.transform.InverseTransformPoint(surface.transform.TransformPoint(vertex));
                distance=Mathf.Max(distance,Mathf.Abs(p.x)/horizontal-p.z,Mathf.Abs(p.y)/vertical-p.z,camera.nearClipPlane-p.z);
            }
            return Mathf.Max(0,distance);
        }
    }
}
