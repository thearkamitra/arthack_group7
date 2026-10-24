# Unity region-to-video zoom: implementation handover plan

Date: 2026-10-24. Status: approved; implementation in progress. Work on `master`.
This document defines a new subtask of EPIC-08 with dependencies on EPIC-05 and
EPIC-06. Planning did not invoke providers. Implementation authorized on 2026-10-24.

## Requested experience

While the simulated or real guide speaks, accumulate head-directed dwell on the
image. At the end of the speaking window, freeze the highest-percentage region.
Prepare a conversation-informed deeper view of that region using fal. Once ready
and approved, pull back to frame the entire current image, replace it with the
prepared starting frame, play the generated inward-moving clip, then move closer
to the resulting image. Hold its final frame as the next exploration surface.
Repeat with fresh attention counters. Generation latency is a preparation wait,
not part of the camera animation.

Proposed defaults: 3×3 spatial grid, 1-second pullback, 0.35-second dissolve,
5-second generated clip, 1-second approach; expose timings in the Inspector.
Five seconds matches the existing adapter; three seconds is an optional future
provider capability, not an assumed valid request. Head direction is an attention
proxy, not eye tracking or evidence of psychological meaning.

## Inspection findings and image evidence

The agent visually inspected the replacement `Assets/Images/ideal_abstract.jpeg`
(1280×720), supplied by the user from `/Users/arkamitra/Downloads/ideal_abstract.jpeg`.
It is a textured abstract space with luminous blue/cream spires, coral streams,
floating pink/blue ovals and dark brown negative space. The upper-left target is
the pink floating oval at normalized `(0.20,0.08)`, with a blue four-point star
below at `(0.12,0.32)`. Preserve both original image files unchanged. The approved
canonical startup image is now `ideal_abstract.jpeg`; old geometric landmarks
are superseded. Coordinator inputs use a lossless PNG decoded from this JPEG.

`Assets/mainscene.unity` references that texture through its RawImage (GUID
`b90f4e25d86c7418abda98f27b1cccda`). However,
`ProjectSettings/EditorBuildSettings.asset` selects
`Assets/Scenes/InnerLandscape.unity`, whose bootstrap uses
`Assets/InnerLandscape/Landscape.mat` with an empty `_MainTex`. That runtime scene
receives an image only after coordinator media download. Source inspection does
not establish which scene is open in a user's editor or prove Play Mode rendering.

`SessionClient.cs` currently needs an XR device, sums dwell across three horizontal
UV thirds named sky/ridge/water, and confirms the last qualified candidate. It
cannot distinguish upper-left from lower-left. Its clock is a 30-second cycle,
not guide speech. It directly replaces textures and starts video, with no staged
zoom. `CurvedLandscape.cs` creates a 110-degree cylindrical surface at radius 3.
`providers.py` currently edits a vertical crop, composites it back, and requests
locked-camera 5-second video. This differs from entering a selected region.

Some existing cards cite nonexistent `media.py` and `voice.py`: actual media code
is `backend/inner_landscape/providers.py`; voice proxy is in `api.py`.

## Decisions and contract

Use one canonical normalized image coordinate system: origin top-left, x right,
y down. Convert Unity UV `(u,v)` to `(u,1-v)` once at the ray-hit boundary. Grid
row/column IDs are spatial names, not sky/ridge/water semantic labels. Use the
winning cell's dwell-weighted centroid as the crop focus. Percentages divide by
valid on-image sampled time, and also report coverage against total speaking
time. Out-of-image, paused, tracking-lost and transition time cannot win. Use a
minimum 0.5 seconds valid dwell; insufficient coverage requires explicit region
selection. Ties resolve by fixed row-major cell order. Freeze a decision once per
speech-window ID; a later gaze movement cannot alter a generation in flight.

The initial window spans the guide's audible turn, from first played audio sample
to the final drained playback chunk, excluding interruptions and pauses. A later
turn opens a new window; an explicit cycle-complete action freezes the accumulated
speaking windows for that cycle. Do not use transcript arrival as audio timing.
For the scripted tests, end the cycle after the first guide/user exchange.

Use an aspect-preserving crop centered on the selected point, initially 50% of
image width/height, clamped to source boundaries. The next still is a full-frame
expansion of this crop, rather than an edited patch in the old composition.
Generate the still from a short, approved visual brief derived only from the
consented conversation. Supply that still as the video start image. Prompt fal
for a slow inward journey preserving the selected symbols and palette; replace
the existing locked-camera instruction only for this new transition mode.
Generated motion is approximate: Unity provides deterministic framing and zoom;
provider output must be visually reviewed for continuity before application.

Keep therapist confirmation as the default. A clearly marked synthetic demo
runner may act as the simulated therapist and approve its own fictional session;
that bypass must not be available to ordinary participant requests.

Each decision/media bundle carries session ID, cycle, speech-window IDs,
source-image hash, grid version, cell, centroid, crop rectangle, dwell seconds,
percentages, coverage, input mode, approved brief, job IDs, start/final-frame
hashes and transition ID. No raw pose history or private notes go to providers.

## Ordered implementation checklist

All paths below are repository-relative. New files are explicitly identified.

### 1. Task ownership and baseline

- [x] Read `kanba/README.md`, EPIC-08, EPIC-05, EPIC-06 and completed NEEDME-01; move EPIC-08 to `kanba/progress/`, set In Progress and record this subtask. Repair board and inbound links; leave physical Quest gates separate.
- [x] Correct stale implementation paths and approval status in the EPIC-05/06 cards without claiming their live acceptance criteria complete.
- [x] In `Assets/InnerLandscape/Editor/LandscapeSetup.cs`, assign the inspected source image as the canonical startup texture and expose Editor Mock versus Quest input selection. Save `Assets/Scenes/InnerLandscape.unity` through Unity; preserve `Assets/mainscene.unity`.
- [x] Update `Assets/InnerLandscape/LandscapeApp.cs` and `Landscape.mat` so Play Mode immediately shows that image; seed the coordinator with the same PNG and verify matching hashes before any paid request.
- [x] Capture baseline Game View evidence showing orientation, aspect ratio and the pink upper-left oval and blue star. Confirm the agent sees the actual rendered image, not just the source PNG.

### 2. Interchangeable attention input

- [x] Add `Assets/InnerLandscape/AttentionInput.cs`: common valid ray/tracking interface with XR head, mouse-look and deterministic scripted implementations. Display MOCK HEAD INPUT in mock mode; never silently fall back when Quest tracking fails.
- [x] Add `Assets/InnerLandscape/RegionAttention.cs`: speech-gated, time-weighted 2D histogram, centroid, coverage, tie and insufficient-data rules. Use an injected clock for deterministic tests.
- [ ] Edit `LandscapeApp.cs` to expose input mode, mouse-look controls, scripted scenario selector, reticle and grid/percentage overlay in Game View; keep UI clicks separate from look input.
- [x] Edit `SessionClient.cs` to consume the shared ray, send aggregate spatial attention, freeze cycle decisions, and stop using the last candidate as the longest-dwell winner. Retain legacy fields only through an explicit compatibility adapter.
- [x] Edit `VoiceClient.cs` to expose actual playback turn start/end/interruption events; track gaps between streamed chunks so temporary empty queues cannot prematurely close a turn.

### 3. Coordinator and conversation-to-media integration

- [x] Edit `backend/inner_landscape/domain.py` using the existing generic persistence in `store.py` to validate/version spatial aggregates and frozen decisions, retain them across reloads, and reject stale cycle/source hashes and duplicate transition IDs.
- [x] Edit `backend/inner_landscape/api.py` to accept aggregate windows and serve staged media bundles; preserve role checks, pause/stop priority and authenticated artifact downloads.
- [x] Add `backend/inner_landscape/region_zoom.py` (including the bounded visual brief function) to derive a bounded visual brief from explicitly allowed conversational text and selected image context. Start with a deterministic template; expose it for therapist review. Never include private notes or entire transcripts in fal prompts.
- [x] Edit `providers.py` to add a separate region-entry generation mode with validated 2D crops, expanded next still, image-to-video request, ffprobe checks, extracted first/final frames and hashes. Preserve existing patch-edit behavior.
- [x] Record source/crop/output files and provider request IDs under existing ignored `work/media/{job_id}/` manifests; add per-test manifests under ignored `work/region_zoom_tests/{run_id}/`. Keep source inputs and prior runs.
- [x] Edit `frontend/app.js`, `frontend/backend.js` and `frontend/index.html` to preview selected cell/crop, approved brief, next still and video, with Confirm continuity & use before publishing the bundle.
- [x] Keep one in-flight billable job, four jobs per session, explicit `--enable-paid`, no automatic billable retry, and no duplicate submission after timeout. Existing NEEDME-01 already records bounded demo approval; do not make paid requests as part of this planning task.

### 4. Framing and transition state machine

- [x] Add `Assets/InnerLandscape/RegionZoomTransition.cs`: Exploring → DecisionFrozen → Preparing → AwaitingApproval → PullBack → SwapStartFrame → PlayVideo → Approach → Exploring. Expose progress/errors and make every step interruptible.
- [x] Add `Assets/InnerLandscape/LandscapeFraming.cs`: compute full-image fit using actual curved-mesh vertices, camera aspect and horizontal/vertical FOV with a small margin. Fit all boundary points in the viewport rather than treating the cylinder as a flat quad.
- [x] Edit `LandscapeApp.cs` to separate a presentation rig from tracked head pose. Animate the rig in Editor; for Quest preserve runtime head tracking and apply the equivalent presentation movement to the image surface. Never write animations onto the tracked camera transform.
- [x] Edit `SessionClient.cs` to download and decode the whole bundle before movement, prepare VideoPlayer without auto-playing from Poll, and hand sole playback ownership to the transition controller.
- [x] At full-frame fit, dissolve old image to decoded generated start frame, play once, hold the extracted final texture, then approach the new surface. Use fixed projection/FOV; avoid double-counting Unity movement and generated inward motion. Keep UI anchored separately.
- [x] Set final texture before stopping/releasing VideoPlayer; promote its hash as the next cycle's source. Rebuild attention mapping/reset counters only after transition completion is acknowledged.
- [ ] Freeze animation/video/attention on pause or disconnect, cancel on stop, and reject late media after cycle changes. Retain the previous stable image on generation/download/decode failures; provide explicit recovery without resubmitting paid jobs.

## Two requested integration tests

These are two reproducible scenarios, supported by offline contract and Play Mode
checks. Both use Editor mock head input and fictional dialogue. Real provider
results must be labelled LIVE; cached playback is a separate REPLAY result and
cannot establish live provider success.

### Test 1 — General zoom with live fal and ElevenLabs

- [x] Add `backend/scripts/test_region_zoom_live.py` with embedded synthetic session/dialogue fixtures. Preflight credentials by presence only, server paid switch, ffmpeg/ffprobe, reachable Unity session, image hash and remaining job budget before billing.
- [x] Add `Assets/InnerLandscape/Editor/RegionZoomTestRunner.cs` and `Assets/InnerLandscape/RegionZoomDemo.cs` to launch the paired Game View scenario and export screenshots/state evidence.
- [x] Simulate participant speech with a bounded ElevenLabs TTS audio fixture generated live, then feed its decoded PCM through the existing coordinator voice socket as user audio. Receive real conversational guide audio and transcripts; play guide audio in Unity. No real microphone is needed. Record separate evidence for TTS and conversational interaction.
- [x] Script central-cell gaze for 8 of 10 valid guide-speaking seconds and another cell for 2 seconds (80%/20%); schedule against audible playback, scaling the pattern to actual turn length. Assert the center wins and out-of-window samples do not count.
- [x] Build/review the brief from the actual synthetic exchange, generate one still and one 5-second video through real fal, then let the simulated therapist approve. Limit to two fal jobs and one bounded dialogue exchange; enforce a 60-second voice cap and a bounded media wait. Timeout is a recorded failure, never a resubmit.
- [ ] Assert ordered pullback/swap/video/approach states, all image corners inside the fitted viewport, duration from ffprobe, decoded playable media, final-frame hold, hash promotion and a fresh next cycle. Capture before/fit/start/mid-video/final/next-cycle frames plus a Game View recording.
- [x] Compare returned first video frame to the approved still and visually inspect continuity. Record actual similarity and review outcome; do not assume prompt adherence or exact pixel equality from generative video.

### Test 2 — Upper-left region wins and controls the entry

- [x] Reuse the same runner and original inspected image in a fresh session; script top-left cell for 70%, center for 20%, lower-right for 10% of valid guide-speaking time. Finish looking at center to prove selection uses accumulated dwell rather than latest gaze.
- [x] Target image point `(0.20,0.08)` near the pink oval and blue star, equivalent to Unity UV `(0.20,0.92)`. Assert top-left row/column, centroid tolerance and clamped crop rectangle; show a debug marker over the original pink-oval area.
- [x] Run the same live ElevenLabs/fal route with an approved brief preserving the pink oval, blue star, coral glow and textured brown palette. Use a separate two-job fal budget; keep each test at one generated transition.
- [x] Inspect saved crop and approved next still: they must derive from the upper-left source, not a center crop or the entire left vertical band. Assert crop coordinates/hashes; visually verify the distinctive shapes in generated output before approval.
- [x] Capture full-frame pullback and the new start frame/video/approach. Verify no vertical flip, off-image sampling or clipping, and that a subsequent offline exploration cycle uses the held final frame as its source. Do not claim two-cycle live generation from a single transition.

## Supporting verification and handover

- [x] Add `backend/tests/test_region_zoom.py` reusing the existing service fixtures for spatial validation, percentages/ties, stale bundles, duplicate IDs, privacy, budgets and failure handling with fake providers. Unit tests must not use network/model downloads.
- [ ] Add `Assets/InnerLandscape/Editor/RegionZoomChecks.cs` for uneven frame rates, speech boundaries, UV inversion, upper-left crop, wide/tall viewport fits and curved-surface boundary projections; use the Unity batch self-check entry point without adding runtime test-package dependencies.
- [ ] Extend Play Mode checks for pause during every animation stage, stop during generation, missing tracking, failed media preparation, and duplicate poll responses. These checks use local fixture media and make no paid calls.
- [x] Run backend tests with `backend/.venv/bin/python -m unittest discover -s backend/tests`, existing frontend tests with `node --test frontend/tests/*.test.cjs`, and Unity batch contract/Play Mode scenarios with installed Unity 6000.6.7f1. Verify available commands against the repository before documenting exact batch invocations.
- [x] Agent visually reviews actual Unity screenshots and test recordings plus crop/start/final artifacts; save a report with observed results, provider IDs, durations, costs when available, commands, and failures under the ignored per-run directory. A successful process exit alone is insufficient.
- [x] Update `docs/UNITY_HANDOFF.md`, `docs/BACKEND.md`, `unity/README.md` and root `README.md` with input modes, controls, two test commands, evidence paths, timing and recovery behavior.
- [ ] Record this subtask's results on EPIC-08. Keep broader EPIC-08 acceptance open until its separate requirements pass; keep Quest deployment/comfort checks blocked on hardware. Commit only scoped changes and push completed authorized work on `master`.

## Review boundary

This plan proposes grid-based longest dwell, explicit cycle completion after
spoken windows, a five-second clip and preview approval. The user approved implementation and supplied the replacement JPEG. Physical Quest stereo, tracked motion, microphone,
performance and comfort require later hardware validation; Editor success cannot
close those gates.


## Implementation notes

The editor tests use `RegionZoomChecks.Run` and the `RegionZoomDemo` Play Mode
harness rather than adding a Unity Test Framework package and assembly hierarchy.
The live runner supports explicit `--reuse-dialogue` and `--reuse-media` inputs;
reusing media labels the run REPLAY and retains links to actual paid-job evidence.
No-data confirmation is stored as `manual=true` with zero dwell, never invented
attention. Camera captures wait for decoded source readiness; VideoPlayer prepares
in APIOnly mode so preparation cannot replace the stable image with black.
Remote polling continues independently throughout transitions so pause can work.

Verified outcomes and remaining checks are recorded in [the verification report](UNITY_REGION_ZOOM_VERIFICATION.md).
