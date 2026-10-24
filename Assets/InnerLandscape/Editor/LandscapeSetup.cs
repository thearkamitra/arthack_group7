using UnityEditor;
using UnityEditor.Build;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.XR.OpenXR;
using UnityEngine.XR.OpenXR.Features;
using UnityEngine.XR.Management;
using UnityEditor.XR.Management;
using UnityEditor.XR.Management.Metadata;

namespace InnerLandscape.Editor
{
    public static class LandscapeSetup
    {
        [MenuItem("Inner Landscape/Configure demo project")]
        public static void Configure()
        {
            var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            var app=new GameObject("Inner Landscape",typeof(LandscapeApp)).GetComponent<LandscapeApp>();
            var material=AssetDatabase.LoadAssetAtPath<Material>("Assets/InnerLandscape/Landscape.mat");
            if(!material){material=new Material(Shader.Find("Universal Render Pipeline/Unlit"));material.SetFloat("_Cull",0);AssetDatabase.CreateAsset(material,"Assets/InnerLandscape/Landscape.mat");}
            material.mainTexture=AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/Images/ideal_abstract.jpeg");
            EditorUtility.SetDirty(material);
            app.landscapeMaterial=material;
            app.mockHeadInput=true;
            EditorSceneManager.SaveScene(scene,"Assets/Scenes/InnerLandscape.unity");
            EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene("Assets/Scenes/InnerLandscape.unity",true)};
            var desktop=XRGeneralSettingsPerBuildTarget.XRGeneralSettingsForBuildTarget(BuildTargetGroup.Standalone);
            if(desktop!=null){desktop.InitManagerOnStart=false;EditorUtility.SetDirty(desktop);}
            PlayerSettings.productName="Inner Landscape";
            PlayerSettings.companyName="Inner Landscape";
            PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android,"com.innerlandscape.demo");
            PlayerSettings.Android.targetArchitectures=AndroidArchitecture.ARM64;
            PlayerSettings.SetScriptingBackend(NamedBuildTarget.Android,ScriptingImplementation.IL2CPP);
            PlayerSettings.Android.forceInternetPermission=true;
            PlayerSettings.insecureHttpOption=InsecureHttpOption.DevelopmentOnly;
            var settings=XRGeneralSettingsPerBuildTarget.XRGeneralSettingsForBuildTarget(BuildTargetGroup.Android);
            if(settings==null)
            {
                var all=AssetDatabase.LoadAssetAtPath<XRGeneralSettingsPerBuildTarget>("Assets/XR/XRGeneralSettingsPerBuildTarget.asset");
                settings=ScriptableObject.CreateInstance<XRGeneralSettings>();
                AssetDatabase.AddObjectToAsset(settings,all);
                var manager=ScriptableObject.CreateInstance<XRManagerSettings>();AssetDatabase.AddObjectToAsset(manager,all);
                settings.Manager=manager;settings.InitManagerOnStart=true;
                all.SetSettingsForBuildTarget(BuildTargetGroup.Android,settings);EditorUtility.SetDirty(all);
            }
            XRPackageMetadataStore.AssignLoader(settings.Manager,"UnityEngine.XR.OpenXR.OpenXRLoader",BuildTargetGroup.Android);
            var xr=OpenXRSettings.GetSettingsForBuildTargetGroup(BuildTargetGroup.Android);
            if(xr!=null){foreach(var feature in xr.GetFeatures<OpenXRFeature>())
                if(feature.GetType().Name=="OculusTouchControllerProfile" || feature.GetType().Name=="MetaQuestFeature") feature.enabled=true;
                EditorUtility.SetDirty(xr);}
            EditorUtility.SetDirty(settings);EditorUtility.SetDirty(settings.Manager);
            AssetDatabase.SaveAssets(); Debug.Log("Inner Landscape scene and Android OpenXR configured.");
        }
        public static void BuildQuest()
        {
            Configure();
            var result=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{"Assets/Scenes/InnerLandscape.unity"},locationPathName="outputs/InnerLandscape.apk",target=BuildTarget.Android,options=BuildOptions.Development});
            if(result.summary.result!=UnityEditor.Build.Reporting.BuildResult.Succeeded)throw new System.Exception("Quest build failed");
        }
    }
}
