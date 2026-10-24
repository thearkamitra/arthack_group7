# EPIC-02: Quest 2 Hardware Deployment & Head-Directed Spatial Attention

- **ID**: `EPIC-02`
- **Milestone Reference**: Milestone 2 (Quest foundation) & Milestone 7 (Video playback in VR)
- **Status**: Blocked
- **Primary Owner**: Unity / VR Developer
- **Relevant Files**:
  - [Assets/InnerLandscape/CurvedLandscape.cs](file:///Users/arkamitra/Documents/ChatGPT/arthack/Assets/InnerLandscape/CurvedLandscape.cs)
  - [Assets/InnerLandscape/SessionClient.cs](file:///Users/arkamitra/Documents/ChatGPT/arthack/Assets/InnerLandscape/SessionClient.cs)
  - [Assets/InnerLandscape/VoiceClient.cs](file:///Users/arkamitra/Documents/ChatGPT/arthack/Assets/InnerLandscape/VoiceClient.cs)
  - [docs/UNITY_HANDOFF.md](file:///Users/arkamitra/Documents/ChatGPT/arthack/docs/UNITY_HANDOFF.md)

---

## 1. Objective & Scope

Deploy the standalone Android Unity app to physical Meta Quest 2 hardware. Render the large, world-anchored curved image/video screen at a comfortable distance (`(0, 1.6, 0)`) without smooth locomotion or mesh generation. Cast head forward rays to sample head-directed attention across three canonical regions (`sky`, `ridge`, `water`), aggregate dwell at 10 Hz / send at 1 Hz, and allow controller confirmation of candidate regions. Download media from the Mac coordinator and play ≤30-second clips.

### Critical Constraints
- **Head-directed attention, NOT eye tracking**: Quest 2 has no eye-tracking hardware. All logs, UI captions, and documentation must state "head-directed attention".
- **Immediate Local Pause/Stop**: Stopping or tracking loss must pause media playback immediately on the headset, without waiting for network round-trips.
- **No Hardcoded Credentials**: Permanent API keys must never be packaged into the Unity APK. The headset pairs over LAN via an 8-character single-use pairing code and receives an hourly session bearer token.
- **Media Window**: Videos must be ≤30 seconds. Video ends on a stable still frame; never loop video clips automatically.

---

## 2. Current Implementation State

The runtime source now lives under [Assets/InnerLandscape/](file:///Users/arkamitra/Documents/ChatGPT/arthack/Assets/InnerLandscape):
- `CurvedLandscape.cs`: Procedural curved mesh, mesh collider, and UV coordinates mapping left-to-right (`sky`, `ridge`, `water`).
- `SessionClient.cs`: Pairing via LAN REST API, 1.5s dwell thresholding, 1Hz aggregate attention reporting, media download, and Unity `VideoPlayer` control.
- `VoiceClient.cs`: PCM16 microphone recording and playback bridge skeleton.

What remains is compiling in Unity, deploying to a physical Quest 2, and verifying real-world ergonomics, latency, and networking.

---

## 3. Tasks & Stories

- [ ] **Task 2.1 — Unity Project Configuration**:
  - Open the root Unity 6000.6.7f1 project with Android Build Support and run the configuration menu.
  - Set Android manifest permissions: `android.permission.INTERNET` and `android.permission.RECORD_AUDIO`.
  - Configure Android Network Security config for trusted cleartext LAN IP development (HTTP/WS for demo only).
- [ ] **Task 2.2 — Visual & Spatial Validation**:
  - Position `CurvedLandscape` GameObject at `(0, 1.6, 0)` with unlit two-sided material.
  - Test in headset: verify front-face visibility, natural FOV coverage, comfort distance, and ensure no dizziness/motion sickness.
- [ ] **Task 2.3 — Head-Directed Raycast & Region Tracking**:
  - Verify raycast from XR Origin CenterEye camera onto the curved mesh collider.
  - Verify UV-to-region mapping (`sky`: U ∈ [0, 0.33], `ridge`: U ∈ [0.33, 0.66], `water`: U ∈ [0.66, 1.0]).
  - Verify dwell threshold (1.5s) triggers visual highlight candidate.
  - Verify 10 Hz sampling and 1 Hz aggregate HTTP report payload.
- [ ] **Task 2.4 — Pairing & LAN Network Connectivity**:
  - Launch Mac coordinator with `bash backend/scripts/run.sh --host 0.0.0.0 --demo-lan`.
  - Obtain 8-character pairing code from therapist console.
  - Enter Mac LAN IP and pairing code in Quest UI; verify successful token acquisition and session sync.
- [ ] **Task 2.5 — Video Playback & Continuity**:
  - Test download of 5-second video clip to local Android cache (`Application.temporaryCachePath`).
  - Verify `VideoPlayer` playback on the curved mesh surface.
  - Verify video playback completes, stops on the last frame, and reports `window_finished` back to the coordinator.
- [ ] **Task 2.6 — Safety & Tracking Loss Handling**:
  - Test removing headset or tracking loss: verify attention aggregation freezes and playback pauses immediately.
  - Test controller pause/stop button: verify immediate local halt.

---

## 4. Acceptance Criteria

1. APK builds cleanly with zero errors on Unity Android target.
2. App runs on Quest 2 at a stable 72+ FPS without frame drops or jitter.
3. Natural head turns reliably highlight the expected region (`sky`, `ridge`, `water`) after 1.5s dwell.
4. Controller trigger confirms the highlighted region and notifies the Mac coordinator.
5. Headset pairs to Mac coordinator over LAN within 5 seconds using an 8-character code.
6. 30-second media cycle plays smoothly and ends on a stable still frame.

## Current pickup
Owner: Codex. Scope: wire the merged Unity project and verify integrated Garmin broadcast reception; physical acceptance stays pending.

## 2026-10-24 integration evidence and remaining gate

- Moved the scripts into the actual root Unity project; committed a bootstrap scene
  selected in Build Settings, world-space pairing/session controls, head-ray +
  trigger confirmation, stereo unlit material, and Android/OpenXR settings.
- Added an editor setup/build entry point; one Python coordinator owns providers.
- Immediate local pause now holds playback while the network command is pending;
  still-image transitions stop old video, and video uses the material's texture slot.
- Batch Unity runs stalled in license initialization before compilation. Android
  Build Support is absent on this Mac. **No compile pass or APK is claimed.**
- Required action: activate Unity license and install Android module, or use the
  teammate's configured 6000.6.7f1 editor. Compile, deploy and complete the physical
  checks in docs/UNITY_HANDOFF.md. Full acceptance remains unverified.

Current pickup: Codex — verify newly pulled changes and live hardware availability.

## Master synchronization review

Pulled teammate commit 3712817 by fast-forward. Its Android profile correctly
inherits the global InnerLandscape scene list, but had Development Build disabled.
Enabled Development Build to match the development-only LAN HTTP/WS setting.
AndroidPlayer support is now installed on this Mac. Unity batch verification still
stalls at licensing initialization; its helper reports another licensing instance
holding the global mutex. C# compilation, APK output and Quest behavior remain
unverified. Stopped only this task's stalled batch editor.
