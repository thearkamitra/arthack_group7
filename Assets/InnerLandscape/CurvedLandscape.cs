using UnityEngine;

namespace InnerLandscape
{
    [RequireComponent(typeof(MeshFilter), typeof(MeshRenderer), typeof(MeshCollider))]
    public sealed class CurvedLandscape : MonoBehaviour
    {
        [Range(60, 160)] public float arcDegrees = 110;
        public float radius = 3;
        public float height = 2.8f;
        [Range(16, 128)] public int segments = 64;

        public Vector3 Point(Vector2 uv)
        {
            float angle=(uv.x-.5f)*arcDegrees*Mathf.Deg2Rad;
            return transform.TransformPoint(new Vector3(Mathf.Sin(angle)*radius,(uv.y-.5f)*height,Mathf.Cos(angle)*radius));
        }
        void Awake()
        {
            var vertices = new Vector3[(segments + 1) * 2];
            var uv = new Vector2[vertices.Length];
            var triangles = new int[segments * 6];
            for (int i = 0; i <= segments; i++)
            {
                float u = i / (float)segments;
                float angle = (u - .5f) * arcDegrees * Mathf.Deg2Rad;
                float x = Mathf.Sin(angle) * radius, z = Mathf.Cos(angle) * radius;
                vertices[i * 2] = new Vector3(x, -height / 2, z);
                vertices[i * 2 + 1] = new Vector3(x, height / 2, z);
                uv[i * 2] = new Vector2(u, 0); uv[i * 2 + 1] = new Vector2(u, 1);
                if (i < segments)
                {
                    int j = i * 6, k = i * 2;
                    triangles[j] = k; triangles[j + 1] = k + 1; triangles[j + 2] = k + 2;
                    triangles[j + 3] = k + 2; triangles[j + 4] = k + 1; triangles[j + 5] = k + 3;
                }
            }
            var mesh = new Mesh { name = "Inner Landscape curved media surface", vertices = vertices, uv = uv, triangles = triangles };
            mesh.RecalculateNormals(); mesh.RecalculateBounds();
            GetComponent<MeshFilter>().mesh = mesh;
            GetComponent<MeshCollider>().sharedMesh = mesh;
        }
    }
}
