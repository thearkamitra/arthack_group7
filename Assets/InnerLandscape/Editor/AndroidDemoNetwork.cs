#if UNITY_ANDROID
using System.IO;
using System.Xml;
using UnityEditor.Android;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;

namespace InnerLandscape.Editor
{
    // The synthetic LAN demo uses HTTP/WS. Release APKs keep cleartext disabled.
    public sealed class AndroidDemoNetwork : IPreprocessBuildWithReport, IPostGenerateGradleAndroidProject
    {
        public int callbackOrder => 1000;
        static bool development;
        public void OnPreprocessBuild(BuildReport report)
        {
            development = (report.summary.options & UnityEditor.BuildOptions.Development) != 0;
        }
        public void OnPostGenerateGradleAndroidProject(string path)
        {
            string manifest = Path.Combine(path, "src", "main", "AndroidManifest.xml");
            var document = new XmlDocument();
            document.Load(manifest);
            var application = document.SelectSingleNode("/manifest/application") as XmlElement;
            if (application == null) throw new BuildFailedException("Android manifest has no application element");
            application.SetAttribute("usesCleartextTraffic", "http://schemas.android.com/apk/res/android", development ? "true" : "false");
            document.Save(manifest);
        }
    }
}
#endif
