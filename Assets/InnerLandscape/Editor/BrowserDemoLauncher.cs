using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
namespace InnerLandscape.Editor
{
    [InitializeOnLoad]
    public static class BrowserDemoLauncher
    {
        public static void Prepare(){LandscapeSetup.Configure();}
        static double next;
        static BrowserDemoLauncher(){EditorApplication.update+=Poll;}
        static void Poll()
        {
            if(EditorApplication.timeSinceStartup<next)return;next=EditorApplication.timeSinceStartup+.5;
            string marker=Path.GetFullPath("work/browser_demo/editor-start.json");
            if(!File.Exists(marker)||EditorApplication.isCompiling||EditorApplication.isPlayingOrWillChangePlaymode)return;
            if(UnityEngine.SceneManagement.SceneManager.GetActiveScene().isDirty)return; // Preserve user edits.
            File.Delete(marker);EditorSceneManager.OpenScene("Assets/Scenes/InnerLandscape.unity");EditorApplication.isPlaying=true;
        }
    }
}
