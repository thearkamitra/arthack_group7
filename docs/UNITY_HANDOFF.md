# Unity teammate handoff

Status: source integration kit; **not compiled or tested on Quest** on this Mac.
Garmin is deliberately excluded. The Mac owns session state and provider keys.
Use fictional data only for LAN development. This is not a clinical deployment.

## On the Mac

1. Follow `backend/scripts/setup.sh`, then `bash backend/scripts/run.sh --host
   0.0.0.0 --demo-lan`. Open the practitioner workspace at http://127.0.0.1:4173.
   The LAN binding is opt-in and uses cleartext HTTP only for synthetic testing.
   Use a trusted isolated network. Do not expose/port-forward it to the Internet.
2. Start a session and click **Pair Unity headset**. This uploads only the displayed
   procedural scene snapshot to this Mac; no provider generation is requested.
3. Give the headset the Mac's LAN address and the 8-character pairing code. Codes
   expire after two minutes and redeem once. Participant tokens expire after one
   hour and can read only their paired session's participant projection.
4. Keep the therapist console open to pause/resume or finish. The browser stops
   its desktop cycle clock once Unity is paired; the Unity client owns the
   up-to-30-second exploration window and reports its completion.

## In the teammate's Unity project

1. Use a Quest-2-compatible Unity editor and OpenXR XR Origin. Pin the versions
   your team verifies. Add Android Build Support, SDK/NDK and OpenJDK through Hub.
2. Copy `unity/Assets/InnerLandscape` into `Assets/`. There are no provider keys or
   native third-party libraries in these scripts. Target standalone Android/Quest 2;
   do not rely on macOS Quest Link. Set Internet Access to Require.
3. Add a GameObject at approximately `(0, 1.6, 0)` with `CurvedLandscape`. It creates
   MeshFilter, MeshRenderer and MeshCollider geometry in Awake. Assign an unlit
   material compatible with your renderer. Verify front-face visibility in headset;
   if the chosen pipeline's culling differs, use a two-sided material.
4. Add a `VideoPlayer` and `SessionClient`. Assign the tracked XR camera,
   landscape collider, renderer and VideoPlayer in the Inspector. Set `serverUrl`
   to the Mac's LAN URL, enter the pairing code and call `Pair()` from a UI button.
5. Wire controller/UI actions to `ConfirmLookedRegion()`, `Pause()`, `NextCycle()`
   and `StopSession()`. Resume is practitioner-only after pause or tracking loss.
   Stopping pauses/stops playback immediately, before the network round trip.
6. Add `VoiceClient` with an AudioSource and reference SessionClient if testing
   voice. Show an explicit audio/provider disclosure and a **Start voice** button
   calling `StartVoice()`. Never start a microphone in Awake or on scene load.
   Voice remains disabled on the backend until a paid test is approved. Start it
   with `--enable-paid` only after that agreement. StopVoice on exit/pause.
7. Configure microphone permission and Android network security for the synthetic
   HTTP/WS LAN demo only. HTTPS/WSS is required before real-client off-loopback use.
   These settings depend on the teammate's Unity version; no unchecked manifest
   override is bundled. Never disable certificate verification.

## What the kit implements

- Stable curved media surface; raycast against its UVs. Three equal U bands map
  left-to-right to `sky`, `ridge`, `water`, matching the desktop controls. These are
  interaction regions, not image-semantic segmentation.
- Dwell highlight candidate after 1.5 seconds, reports accumulated dwell once per
  second. This is head direction, not eye tracking. Controller confirmation changes
  the chosen region; dwell alone returns a proposal without changing the scene.
- REST polling for session state at 0.5 seconds, with bearer-token authorization.
  A WebSocket state feed is also available, but the kit avoids a networking package.
- Texture download with auth; video download to temporary local storage before
  VideoPlayer playback (VideoPlayer cannot add the bearer header itself).
- Tracking loss pauses the coordinator; missing network state pauses local playback.
- Optional microphone PCM16 mono/16kHz bridge to the Mac voice WebSocket, with
  interruption handling. Audio buffering and echo behavior need physical testing.

## API contract

- `POST /api/pair` with `{ "code": "..." }` → token, session_id, expiry.
- `GET /api/sessions/{id}` with `Authorization: Bearer <token>` → public session
  state. Practitioner notes, client identifiers and profile records are omitted.
- `POST /api/sessions/{id}/commands` with a unique `command_id`, `command`, `payload`.
  Allowed commands: `attention`, `select`, `pause`, `stop`, `tracking_lost`,
  `window_finished`, `next`. Participant resume is intentionally denied.
- Attention payload: `{ "source":"head", "cycle":1,
  "dwell":{"sky":3.2,"ridge":4.0,"water":1.0} }`. Dwell must sum to at most 31
  seconds; stale cycles are rejected. Do not send raw pose samples.
- `window_finished` payload carries current `cycle`; the client does not invent
  a new cycle ID. `next` requires active state and a completed exploration window.
- `/api/sessions/{id}/events` WebSocket: first send `{ "token":"..." }`, then
  receive revisioned state snapshots. Voice uses the same first-message token
  plus `consent:true` at `/api/sessions/{id}/voice`.
- No tokens in URLs, logs, source files or screenshots. Never ship provider keys.

## Required physical acceptance tests

Pair, display still/video correctly in both eyes, verify U mapping while turning,
check dwell borders and controller confirmation, test lost tracking/headset removal,
network interruption, pause/resume/stop, media expiry and authenticated download.
Check video motion and stereo comfort, frame time, texture memory and battery.
Test voice permission, sample rate, audio ordering, interruption and echo on Android.
The scripts are not proof that any of these checks pass. Remove old temporary
video files between demo runs; production asset cache eviction is not implemented.
