using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
namespace InnerLandscape.Editor
{
    [InitializeOnLoad]
    public static class BrowserDemoLauncher
    {
        public static void Prepare(){LandscapeSetup.Configure();}
        [System.Serializable] class RuntimeStatus
        {
            public string timestamp, scene, sessionStatus;
            public bool playing, paused, compiling, sceneDirty, runInBackground, hasSession, hasBridge, bridgeFresh;
        }
        static double next;
        static BrowserDemoLauncher(){EditorApplication.update+=Poll;}
        static void Poll()
        {
            if(EditorApplication.timeSinceStartup<next)return;next=EditorApplication.timeSinceStartup+.5;
            // Local diagnostics contain no token, conversation or preview data.
            var scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene();
            var session=Object.FindFirstObjectByType<SessionClient>();
            var bridge=session?session.browserDemo:null;
            Directory.CreateDirectory("work/browser_demo");
            File.WriteAllText("work/browser_demo/editor-status.json", JsonUtility.ToJson(new RuntimeStatus {
                timestamp=System.DateTime.UtcNow.ToString("o"), scene=scene.path,
                playing=EditorApplication.isPlaying, paused=EditorApplication.isPaused,
                compiling=EditorApplication.isCompiling, sceneDirty=scene.isDirty,
                runInBackground=Application.runInBackground, hasSession=session,
                hasBridge=bridge, bridgeFresh=bridge&&bridge.Fresh,
                sessionStatus=session?session.status:"No runtime session"
            }));
            string marker=Path.GetFullPath("work/browser_demo/editor-start.json");
            if(!File.Exists(marker)||EditorApplication.isCompiling||EditorApplication.isPlayingOrWillChangePlaymode)return;
            if(UnityEngine.SceneManagement.SceneManager.GetActiveScene().isDirty)return; // Preserve user edits.
            File.Delete(marker);EditorSceneManager.OpenScene("Assets/Scenes/InnerLandscape.unity");EditorApplication.isPlaying=true;
        }
    }
}
