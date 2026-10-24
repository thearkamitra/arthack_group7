# Unity / Quest handoff

The repository root is the Unity **6000.6.7f1** project. Runtime source lives in
`Assets/InnerLandscape/`, not a second copy under `unity/`.

## Current status

`Assets/Scenes/InnerLandscape.unity` is selected in Build Settings. Its bootstrap
creates the tracked camera, curved image/video surface, world-space pairing and
session controls, optional microphone bridge, and head-ray / trigger interaction.
Android settings select ARM64/IL2CPP and OpenXR with Meta Quest support and Oculus
Touch input. The referenced double-sided unlit shader includes stereo instancing.
These source/settings changes are **not yet compile- or headset-verified**.

Local batch compilation stalled before C# compilation because Unity licensing did
not initialize. This Mac also lacks Android Build Support. No APK was produced.

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
