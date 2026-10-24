using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
namespace InnerLandscape.Editor
{
    [InitializeOnLoad]
    public static class RegionZoomTestRunner
    {
        static string Pending=>Path.GetFullPath("work/region_zoom_tests/unity-request.json");
        public static void Batch() { AssetDatabase.Refresh(); LandscapeSetup.Configure(); RegionZoomChecks.Run(); }
        static RegionZoomTestRunner(){EditorApplication.update+=Poll;EditorApplication.playModeStateChanged+=ModeChanged;}
        static void Poll()
        {
            if(EditorApplication.isPlayingOrWillChangePlaymode||EditorApplication.isCompiling||!File.Exists(Pending))return;
            File.Copy(Pending,Pending+".active",true);File.Delete(Pending);
            EditorSceneManager.OpenScene("Assets/Scenes/InnerLandscape.unity");
            EditorApplication.isPlaying=true;
        }
        static void ModeChanged(PlayModeStateChange state)
        {
            if(state!=PlayModeStateChange.EnteredPlayMode||!File.Exists(Pending+".active"))return;
            var request=JsonUtility.FromJson<RegionZoomDemo.Request>(File.ReadAllText(Pending+".active"));
            new GameObject("Synthetic region zoom test",typeof(RegionZoomDemo)).GetComponent<RegionZoomDemo>().request=request;
            File.Delete(Pending+".active");
        }
        [MenuItem("Inner Landscape/Open region zoom demo")]
        public static void Open(){EditorSceneManager.OpenScene("Assets/Scenes/InnerLandscape.unity");}
    }
}
