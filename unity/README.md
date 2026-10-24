# Unity project

The merged Unity project lives at the repository root (`Assets/`, `Packages/`,
`ProjectSettings/`), pinned to Unity 6000.6.7f1. Runtime code now lives in
`Assets/InnerLandscape/`; do not maintain a second copy here.

Open the repository in Unity Hub. Run **Inner Landscape → Configure demo project**
to generate `Assets/Scenes/InnerLandscape.unity`, select it as the build scene,
and configure Android/OpenXR. See `docs/UNITY_HANDOFF.md` for deployment.

For the canonical abstract image, Editor mock head controls, region-entry flow
and the two real-provider test scenarios, see [Unity handoff](../docs/UNITY_HANDOFF.md#region-entry-in-editor-2026-10-24).
