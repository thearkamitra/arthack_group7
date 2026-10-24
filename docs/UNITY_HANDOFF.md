# Unity / Quest handoff

The repository root is the Unity **6000.6.7f1** project. Runtime source lives in
`Assets/InnerLandscape/`, not a second copy under `unity/`.

## Current status

`Assets/Scenes/InnerLandscape.unity` is selected in Build Settings. Its bootstrap
creates the tracked camera, curved image/video surface, world-space pairing and
session controls, optional microphone bridge, and head-ray / trigger interaction.
Android settings select ARM64/IL2CPP and OpenXR with Meta Quest support and Oculus
Touch input. The referenced double-sided unlit shader includes stereo instancing.
Source compilation and the editor configuration entry point now pass in Unity
6000.6.7f1. The scene and XR settings have been saved by Unity itself.

The licensing lock is resolved and the full Android toolchain has been repaired.
The parent Android repair did not install its NDK/CMake child modules; installing
`android-ndk-r27c` and `cmake-3.22.1` explicitly resolved this. Verified Java
17.0.18, NDK r27c (27.2.12479018), and CMake 3.22.1 by running their binaries.

A development APK was built and validated at `outputs/InnerLandscape.apk`
(54,682,134 bytes at this build). Verified: package `com.innerlandscape.demo`, app
label Inner Landscape, ARM64 IL2CPP library, VR launch category, Internet/microphone/
OpenXR permissions, development cleartext LAN permission, APK signature and ZIP
integrity. Local evidence: `work/quest-build/final-manifest.json` and
`work/quest-build/build-network.log`. These generated artifacts remain ignored.

No Quest was listed by `adb devices`, so installation, launch, pairing and physical
rendering/audio/comfort checks remain pending. No hardware pass is claimed.

## Build

1. Open the repository in Unity Hub using **6000.6.7f1**. Ensure the editor license
   is active. Install Android Build Support, SDK/NDK and OpenJDK for this editor.
2. Let packages import and resolve any editor validation messages. Run
   **Inner Landscape → Configure demo project** to regenerate the scene and
   settings through Unity's own APIs. This replaces only the generated demo scene.
3. Select Android and run OpenXR Project Validation. Verify Meta Quest support,
   Oculus Touch profile, microphone permission and Internet permission. The
   microphone is requested only after explicit Start voice.
4. Build a **Development Build** to Quest 2. Development builds allow the trusted
   local HTTP/WS demo; release builds must use HTTPS/WSS. Use fictional data.
   The editor batch entry point `InnerLandscape.Editor.LandscapeSetup.BuildQuest`
   writes `outputs/InnerLandscape.apk` when the Android module is installed.

## Pair and run

1. On Mac: `bash backend/scripts/run.sh --host 0.0.0.0 --demo-lan`.
   Add `--enable-paid` for approved provider testing. Keep provider keys on Mac.
2. Open `http://127.0.0.1:4173`, start a session and click **Pair Unity headset**.
   Use the Mac LAN address and fresh 8-character pairing code in the headset.
   Codes expire in two minutes; session tokens last one hour.
3. Look at a field and press trigger to open the headset keyboard. Enter the URL
   including `http://` and port `4173`; enter the code and press Pair.
   On desktop, click a field and type using the keyboard.
4. The landscape stays anchored in the room. Head direction maps equal UV thirds
   to `sky`, `ridge`, `water`; these are interaction bands, not semantic regions
   and not eye tracking. After 1.5 seconds of dwell, trigger confirms the region.
   The control panel also confirms the last qualified region.
5. Unity owns the 30-second exploration clock after pairing. Press Next cycle
   after the window finishes. Pause/stop hold local playback immediately; resume
   requires the practitioner. No automatic clip looping or smooth locomotion.
6. Start voice explicitly after reading its disclosure. Audio goes through the
   coordinator to ElevenLabs. Pause, stop, tracking loss or application suspension
   ends microphone capture. Garmin remains on Mac; it does not need headset pairing.

## Provider routing

Use the Python coordinator's existing authenticated voice/media endpoints and
therapist media preview/approval controls. `backend/fal-image-server/` is a separate
teammate prototype and is not launched or used by this integration. Do not run it
as a second generation path for the session demo. Still images and generated clips
are authenticated downloads; clips are cached locally for Unity VideoPlayer.

## Required acceptance checks

Compile first, then test on physical Quest: pairing on shared Wi-Fi, both-eye
rendering and image orientation, head pose/height, UV region ordering, dwell and
trigger confirmation, UI keyboard, 30-second completion, authenticated still/video
download, video end frame, pause/resume/stop, headset removal, network loss,
Android microphone permission, voice interruption/echo and comfort/performance.
The scripts and configuration do not prove these pass. Temporary video cache
cleanup remains manual between demo runs.

## Coordinator contract

- `POST /api/pair` body `{ "code": "..." }` returns token and session_id.
- `GET /api/sessions/{id}` uses `Authorization: Bearer <token>`; private notes
  and client identifiers are omitted.
- `POST /api/sessions/{id}/commands` takes unique `command_id`, `command`,
  `payload`. Commands: attention, select, pause, stop, tracking_lost,
  window_finished, next. Participant resume is denied.
- Attention: `{ "source":"head", "cycle":1,
  "dwell":{"sky":3.2,"ridge":4.0,"water":1.0} }`.
  Only aggregates are sent, about once per second; no raw poses.
- Voice WebSocket `/api/sessions/{id}/voice` starts with
  `{ "token":"...", "consent":true }`.
- Never put tokens in URLs, logs or screenshots; never package provider keys.

## Prepared local build and coordinator

The Mac coordinator was restarted with `--host 0.0.0.0 --demo-lan --enable-paid`.
Its local status check confirms voice and media credentials configured with paid
features enabled. No voice/media request is sent merely by enabling the server.

To deploy the existing APK after USB debugging approval:

```sh
"/Applications/Unity/Hub/Editor/6000.6.7f1/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb" devices
"/Applications/Unity/Hub/Editor/6000.6.7f1/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb" install -r outputs/InnerLandscape.apk
```

`AndroidDemoNetwork.cs` sets `usesCleartextTraffic` only for Development Build;
release builds explicitly disable it. The local HTTP/WS demo is synthetic only.

## Region entry in Editor (2026-10-24)

The approved startup artwork is `Assets/Images/ideal_abstract.jpeg` (the supplied
textured abstract space). Run **Inner Landscape → Configure demo project** to
assign it to the runtime scene. Existing `Assets/mainscene.unity` is preserved.
The build scene remains `Assets/Scenes/InnerLandscape.unity`.

In Editor, `LandscapeApp.mockHeadInput` selects mouse look: hold right mouse and
drag. A center reticle is the head-direction proxy. Quest builds use XR input;
missing tracking pauses instead of silently substituting mouse input. The
presentation surface moves for transitions; the tracked head is not animated.
Editor head look and synthetic tests are explicitly labelled MOCK HEAD INPUT.

Start the coordinator with `bash backend/scripts/run.sh --enable-paid`. Start a
fictional session in its browser and click **Pair Unity headset**; this loads the
same canonical artwork into the coordinator. Enter the code and loopback URL in
Unity. Start voice explicitly for live microphone use. After the guide has spoken,
**Confirm region** freezes the spatial grid decision for review. The spatial
cycle has no automatic 30-second cutoff; it completes when region entry finishes.
Legacy desktop timers are unchanged.

Open Media studio, select **Enter frozen spatial region**, and supply an approved
short conversational excerpt (600 characters maximum). Review the generated
start image; **Approve start image & generate entry video** spends the second
job. Review the video and click **Confirm continuity & use**. Unity preloads its
frames/video, pulls back, dissolves to the starting frame, plays the 5-second
inward journey, holds the extracted final frame, approaches, and acknowledges the
next cycle. Generation latency leaves the current image visible. No paid request
is retried automatically. A timeout needs provider reconciliation by request ID.

Two bounded synthetic scenarios (open this project in Unity; exit prior Play Mode):

```sh
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/test_region_zoom_live.py --scenario center
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/test_region_zoom_live.py --scenario upper-left
```

The runner uses an isolated loopback coordinator on port 4174 and a fresh ignored
run directory. It uses real ElevenLabs TTS as fictional participant audio, real
conversational guide audio, and two real fal jobs per scenario. Unity consumes a
local test request and reports scripted spatial attention. Only this synthetic
runner acts as a simulated approving therapist. Ordinary participant APIs cannot
submit or approve media. `--reuse-dialogue RUN_DIRECTORY` reuses saved live audio
for a Unity retry and explicitly records that provenance; it is not a fresh
ElevenLabs check. Evidence includes manifests, dialogue audio, grid aggregates,
job IDs, crop/still/video/final frames and rendered camera captures under
`work/region_zoom_tests/`. Never commit these generated runs or pairing files.

Editor contract checks are available through the batch entry point
`InnerLandscape.Editor.RegionZoomChecks.Run`; this verifies top-left UV conversion,
speech gating and all curved-mesh vertices at three viewport aspects. Hardware
stereo, head pose, acoustic echo and motion comfort remain unverified without Quest.

If no audible guide attention is available, **Confirm region** explicitly selects
the reticle's image point. The decision is labelled manual and has zero dwell;
it is never presented as measured attention. This permits controlled manual demos.
For a provider-free replay after an initial live run, pass both
`--reuse-dialogue LIVE_VOICE_RUN` and `--reuse-media LIVE_MEDIA_RUN`; the resulting
manifest is explicitly REPLAY. Each successful Unity scenario also exports
`unity-transition.mp4`, `fit.json` and pose samples proving remote pause holds both
presentation position and video time.


### Object close-up correction

`LandscapeApp.viewingDistance` defaults to **0.75 m**, measured from the initial
head position to the image center. It is editable in the scene Inspector and
preserved as the close endpoint after each transition. The curved surface keeps
its large dimensions, so the initial view is intentionally immersive and cropped;
the pullback temporarily fits the whole image. Controls sit in front at 0.55 m.

Region-entry prompt version 2 centers the selected object within the crop and
asks for a forward macro approach: the object grows until its luminous surface
fills the frame. It excludes tunnel/room expansion and camera pullback. Previous
saved clips do not change when prompts change; generate a new preview to see the
corrected motion. Continue to review provider motion before applying.

### Related new forms and high-resolution final image (2026-10-25)

Prompt version 3 keeps moving toward the selected shape while revealing new
nearby companion forms that share its contours, colors and material. It ends on
a detailed composition of distinct shapes instead of a featureless macro surface.

After the video, the backend enhances its exact last frame with Clarity Upscaler
(low creativity, high resemblance), targeting a **2560-pixel long edge** while
preserving aspect ratio. The unenhanced frame remains `final-original.png`.
Unity gently blends from the video end into the enhanced PNG, holds that image,
and promotes its actual hash as the next source. Video playback retains the
video model's native resolution; the held still is higher resolution.

Region entry now reserves **three provider calls**: starting still, video and
final-frame enhancement. The existing four-call session ceiling is unchanged;
a fresh full transition needs three remaining calls. Preview and approve both
the clip and the high-resolution final image in Media studio. The dimensions
shown there come from decoding the actual output, not an assumed resize. Failed
or ambiguous enhancement leaves the bundle unapplied and is never resubmitted
automatically. Manifests include the separate enhancement request ID and settings.

### Frontend conversation and arrow control

See [Browser-controlled Unity demo](BROWSER_UNITY_DEMO.md) for the complete
no-headset flow. **Use browser + Unity demo** starts the open Editor and pairs
locally. The frontend shows the live Unity camera and sends arrow controls, while
frontend ElevenLabs playback gates Unity attention. The browser does not start
Unity's microphone. A tracked headset takes priority over browser arrows.
