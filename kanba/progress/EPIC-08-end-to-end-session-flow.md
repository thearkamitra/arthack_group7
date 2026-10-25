# EPIC-08: End-to-End Supervised Reflection Journey & Clinical Workflow

- **ID**: `EPIC-08`
- **Milestone Reference**: Milestone 8 (End-to-end demo)
- **Status**: In Progress
- **Primary Owner**: Full-Stack / Product Engineer & Therapist Role
- **Relevant Files**:
  - [frontend/index.html](file:///Users/arkamitra/Documents/ChatGPT/arthack/frontend/index.html)
  - [frontend/app.js](file:///Users/arkamitra/Documents/ChatGPT/arthack/frontend/app.js)
  - [backend/inner_landscape/api.py](file:///Users/arkamitra/Documents/ChatGPT/arthack/backend/inner_landscape/api.py)
  - [PLAN.md](file:///Users/arkamitra/Documents/ChatGPT/arthack/PLAN.md#L28-L75)

---

## 1. Objective & Scope

Integrate all components into a seamless, therapist-supervised end-to-end experience:
1. **Pre-Session**: Therapist reviews synthetic client profile, sets goals and exclusions, administers consent and optional readiness check / WHO-5 questionnaire.
2. **Session Pairing**: Therapist pairs physical Quest 2 headset via single-use code over LAN.
3. **Exploration Cycles**: Client explores curved landscape with head-directed attention; AI guide engages in voice dialogue; client confirms region; fal.ai generates refined still and 5s clip (≤30s window); therapist supervises with pause/override controls.
4. **Post-Session**: Immediate comfort check, chronological timeline review, draft AI session summary review, and clinical note saving.

### Critical Constraints
- **Data Segregation**: Private therapist notes must remain private to the therapist view and never be fed into AI prompts or shared with client projections.
- **Therapist Authority**: System overrides, pause, and stop controls take absolute precedence over model recommendations.
- **Resilience**: Client or therapist can pause or stop at any moment. Session state must be recoverable after disconnects.
- **Synthetic Demonstration**: Use pseudonymous synthetic records for demonstration; do not claim clinical treatment efficacy or medical device compliance.

---

## 2. Current Implementation State

- **Desktop Slice**: Standalone client and therapist flows run locally in [frontend/](file:///Users/arkamitra/Documents/ChatGPT/arthack/frontend) with full cycle simulation and saved note reloads.
- **Backend Coordinator**: SQLite event store and session API handle session lifecycle, notes, readiness ratings, and event timelines.
- **Pending**: Connecting all physical components (Quest 2 + ElevenLabs voice + fal media + Mac coordinator) in a live multi-cycle session.

---

## 3. Tasks & Stories

- [ ] **Task 8.1 — Pre-Session Setup & Client Intake**:
  - Select synthetic client profile (e.g., "Taylor Reed - Exploring Creative Transitions").
  - Record pre-session therapist note, session goals, and visual preferences.
  - Complete client readiness check and optional WHO-5 well-being questionnaire.
- [ ] **Task 8.2 — Headset Pairing & Session Launch**:
  - Launch session; generate pairing code in console.
  - Pair physical Quest 2; verify session state synchronizes across browser and VR.
- [ ] **Task 8.3 — Supervised Multi-Cycle Exploration (2–3 Cycles)**:
  - Cycle 1: Client looks at `sky` region; guide asks opening question; client confirms; still inpainting refines scene.
  - Cycle 2: Client looks at `water` region; Kling generates 5-second animated clip; playback completes on curved surface.
  - Test therapist intervention: trigger manual pause and resume from the console.
- [ ] **Task 8.4 — Post-Session Review & Clinical Summary**:
  - Complete post-session comfort rating.
  - Review chronological journey timeline: region decisions, attention dwell, and generation events.
  - Review draft AI summary; verify editability and therapist approval badge.
  - Save post-session clinical notes and verify retention in SQLite.

---

## 4. Acceptance Criteria

1. Complete session runs from intake to post-notes without browser reloads or errors.
2. Quest 2 display and therapist console stay synchronized in real time.
3. Pausing from either therapist console or headset halts all media and voice immediately.
4. Saved session, notes, and AI summary reload identically after restarting the Mac server.
5. Zero leakage of private notes into AI prompts or participant API payloads.

## Proposed Unity region-entry subtask (2026-10-24)

Owner: Codex. Approved Unity region-entry implementation started 2026-10-24. See
[Unity region zoom handover plan](../../docs/UNITY_REGION_ZOOM_PLAN.md) for the
inspected image, file-level checklist, mock head input and two live-provider test
scenarios. Scope: Editor mock head input, spatial attention, region-entry media, staged transitions and two bounded integration scenarios. Physical Quest acceptance remains separate.


## Unity region-entry implementation evidence (2026-10-24)

Owner: Codex. This subtask implements the supplied abstract JPEG, mock/XR input
boundary, speech-gated 3×3 longest dwell, manual fallback, validated crop/start
still/video bundles, staged presentation transitions and final-frame promotion.

- [x] Two reproducible scenarios implemented; real ElevenLabs and fal artifacts verified.
- [x] Center transition verified with saved live artifacts and explicit REPLAY provenance.
- [x] Upper-left live test: 69.7% dwell, correct pink-oval/blue-star crop, complete Unity transition.
- [x] Remote pause holds video and position; cancellation restores stable pose/image.
- [x] Unity coordinate/framing checks, 37 backend tests and 19 frontend tests passed.
- [ ] Broader epic acceptance and physical Quest checks remain open; this card stays In Progress.

See [verification report](../../docs/UNITY_REGION_ZOOM_VERIFICATION.md) and
[setup](../../docs/UNITY_HANDOFF.md#region-entry-in-editor-2026-10-24).
Generated evidence stays under ignored `work/region_zoom_tests/`, not Git.

### Review correction: closer object and starting surface

- [x] Replace ambiguous deeper-space prompts with object enlargement and explicit forward macro approach; exclude zoom-out/tunnel expansion.
- [x] Start the surface 0.75 m from the head (formerly 3 m), returning to that distance after playback; move controls in front.
- [x] Generate and inspect a fresh bounded fal pair: the selected pink oval grows to fill the final frame. Unity transition, pause, cancellation and next cycle passed at the close distance.
- [x] Regression evidence: `work/region_zoom_tests/1792878858107020000-upper-left/`; 38 backend tests and 19 frontend tests passed. EPIC-08 remains In Progress for broader acceptance.


### Related-form discovery and final resolution (2026-10-25)

- [x] Reveal new nearby forms related to the selected silhouette/palette while continuing inward; keep multiple distinct shapes in the ending.
- [x] Preserve edited still dimensions and add conservative AI enhancement of the exact final frame; validate its dimensions and include its hash as the next source.
- [x] Count the enhancement call in the existing four-call budget; show the enhanced preview and dimensions before approval.
- [x] Fresh run `work/region_zoom_tests/1792879510944327000-upper-left/` passed: final image 2560×1408, related companion shapes visually inspected, Unity transition and next-cycle promotion verified. 41 backend tests and 19 frontend tests passed. This epic remains In Progress for broader/hardware acceptance.

### Browser-controlled no-headset flow (2026-10-25)

- [x] Frontend voice playback timing gates Unity attention; arrows steer its actual camera and a live JPEG preview replaces the procedural demo view.
- [x] Explicit frontend opt-in auto-pairs the local Editor; tracked headset input has priority. Existing scene images are preserved.
- [x] Frontend confirmation and conversation-prefilled Media studio complete the existing transition flow.
- [x] Bounded integrations passed at `work/browser_demo/1792880492957860000/` and `work/browser_demo/1792880937225415000/`, without paid calls or microphone recording; rendered view changes, clean previews and measured attention verified. Final suites: 47 backend tests and 23 frontend tests.
- [ ] Interactive browser/microphone check remains unverified because the browser tool still reports a saved permission/managed-policy denial for the local origin. Broader epic/hardware acceptance remains open.

See [browser demo handoff](../../docs/BROWSER_UNITY_DEMO.md).


## Current handoff — 2026-10-25

**Column: In Progress.** Implementation is pushed on `master`; the full epic is
not complete because interactive browser/microphone and physical Quest acceptance
remain open.

### Delivered and verified

- [x] `e608e54`: close object approach, 0.75 m initial viewing distance and corrected inward generation prompts.
- [x] `b0655e7`: new related nearby forms and AI-enhanced final image; fresh generated output verified at 2560×1408.
- [x] `910e1a4`: frontend ElevenLabs playback timing, browser arrows driving the actual Unity camera, live Unity preview, local opt-in pairing and headset priority.
- [x] Latest regression suites: 47 backend tests and 23 frontend tests passed. Final Unity compilation passed.
- [x] Local browser-control/Unity integration passed at `work/browser_demo/1792880937225415000/`: automatic pairing, changed camera frames, clean preview and non-manual speech-gated attention decision.

### Open issues and next actions

- [x] **Reported frontend warning diagnosed:** the user supplied a 401 for GET `/api/workspace`, confirming an authentication failure while the backend was reachable. Restart-induced stale-cookie rejection is reproduced by an automated test; the generic connection warning is corrected.
- [x] **Authentication recovery implemented:** read-only status/workspace GETs renew through the existing loopback root bootstrap once, then retry once. Mutations and paid calls are never automatically retried. Tests verify preserved workspace data, bounded renewal, and distinct authentication/network messages.
- [ ] Confirm the affected browser recovers after one page reload to load the updated JavaScript; agent-side browser inspection remains blocked.
- [ ] **Interactive inspection:** the browser tool still denies observing `http://127.0.0.1:4173/`, citing a saved permission or managed policy, including after the user reported enabling access. This is a separate tool-access issue, not proof of a backend or Unity fault. Inspect Settings → Browser for the exact origin or a managed rule; do not work around the denial through another browser surface.
- [ ] **Actual frontend microphone conversation:** verify only after explicit user start/consent; mocked audio timing and prior real provider runs do not establish this live browser microphone check.
- [ ] **Physical Quest acceptance:** retain the existing hardware gates; do not infer a headset pass from Editor rendering.

Untracked `Assets/_Recovery/` and `Assets/_Recovery.meta` are preserved and excluded
from commits. They are not part of the implementation or acceptance evidence.
See [browser demo setup and evidence](../../docs/BROWSER_UNITY_DEMO.md).


### Active follow-up: workspace 401 (2026-10-25)

User supplied a 401 response from `/api/workspace`; the backend is reachable but
the presented cookie is not accepted. Owner: Codex. Implement one bounded
read-only authentication renewal using the existing loopback root bootstrap,
keep writes/paid calls non-retrying, and test restart/cookie behavior without
copying or logging the user's credential.


Authentication follow-up evidence: the new backend restart test reproduces old-
cookie 401 → local root renewal → authorized workspace read, retaining notes and
pausing unfinished sessions. Four JavaScript tests cover bounded recovery and
no automatic POST/PUT retry. The pasted user credential is not used or recorded
in code, tests or logs. No backend restart is needed to serve this frontend fix.

Final authentication regression run: **48 backend tests and 27 frontend tests passed**. Evidence logs: `work/browser_demo/auth-backend-tests.log` and `work/browser_demo/auth-frontend-tests.log` (ignored).

### Active final-demo preparation (2026-10-25)

Owner: Codex. Scope: align a reusable video prompt with the current artwork and
approved inward/related-form transition; inspect the interactive browser demo;
repair the observed scripted-demo/Unity-controller global-name collision; record
a concrete final-demo checklist. Broader epic and hardware acceptance stay open.

Final-demo preparation evidence: corrected the `LandscapeDemo` global collision
by giving the live Unity controller its own `LandscapeUnityDemo` namespace,
including voice speech-gate calls. Scripted and live scripts are now loaded
together in the controller regression tests; all 27 frontend tests passed.
Versioned changed frontend script URLs to refresh cached browser assets.
Interactive browser check now reaches the Unity waiting state instead of
`start is not a function`; Media studio opens and the revised visual brief is
prepared. Screenshot: ignored `work/final_demo/browser-media-studio.png`.
The coordinator was started with the approved paid gate, but no provider job or
microphone capture was started. Unity startup was attempted; app observation
times out and no live preview was verified. This is now a Unity connection
blocker, not the earlier browser-origin denial: browser inspection succeeded.
See [revised prompts and final demo sequence](../../docs/FINAL_DEMO.md).
EPIC-08 stays In Progress: live voice, transition and physical acceptance remain.

### Active heartbeat repair (2026-10-25)

Owner: Codex. Investigate the user-reported paired-but-waiting Unity state;
verify background runtime, pairing and browser preview, preserving session data
and unsaved scenes. Current project disables runInBackground while the browser
requires presence newer than three seconds.

Heartbeat repair verified: Unity had background execution disabled, and its
bridge coroutine used Start even though OnDisable stops it on script reload.
Enabled background execution in bootstrap/Player Settings, restarted the bridge
from OnEnable after a one-frame dependency wait, and replaced the misleading
waiting message with the actual heartbeat condition. Local sanitized Editor
status now distinguishes Play Mode, pause, runtime bridge and freshness.

After user-assisted window focus (native Unity inspection still times out),
Unity recompiled the changes without C# errors. Browser-driven reconnection
succeeded: actual artwork preview, LIVE UNITY DEMO, left turn at -5 degrees,
center control, and fresh presence/frame availability across a five-second
background check. All 27 frontend tests passed. Evidence is ignored under
`work/final_demo/`: `unity-live-left.png`, `unity-live-connected.png`, and
`heartbeat-verification.json`. No provider calls or microphone capture.

This closes the heartbeat subtask only. Runtime still reports a saved-media
download failure while retaining the existing artwork texture; connection success
does not verify generation-source readiness or a live voice/media cycle.
EPIC-08 remains In Progress for the remaining end-to-end/hardware checks.

### Active seamless-demo follow-up (2026-10-25)

Owner: Codex. User authorizes prompt-free confirmation simulation, labelled
synthetic heart rate and voice diagnosis/repair. Plan: generate a deterministic
five-second local entry bundle from the authenticated current Unity preview at
the browser viewport dimensions, retain source/command/output manifests, apply
through the normal interruptible transition, and keep paid generation separate.
Show synthetic BPM only as simulation. Remove redundant voice modal, retain the
inline microphone disclosure, handle provider audio metadata and startup errors,
and verify live provider startup with a bounded test.

### Active real-fal view discovery (2026-10-25)

Owner: Codex. User requests actual new objects during inward motion. Replace
Confirm view's local simulation with the existing real fal image/video/enhancement
pipeline for fictional demo profiles. The click authorizes that bounded automatic
demo sequence; normal Media studio review remains unchanged. Preserve the
current-view snapshot, inherited forms/palette, four-call budget, one in-flight
job, no billable retries, pause/stale-source checks and per-job manifests.

Seamless-demo follow-up evidence: automatic local five-second bundles, sample
pulse, explicit demo presentation, voice startup without the redundant modal,
provider-reported PCM output rate and microphone resampling implemented. The
browser connected to ElevenLabs and recorded guide/participant event types; raw
audio was not exported. The local test promoted its final image and repaired
the previously unavailable saved scene. This path remains available internally,
but Confirm view has now been switched to actual fal as requested below.

Real-fal discovery evidence: new automatic demo pipeline uses the full confirmed
viewport once, inherited-form prompts, three sequential billable units, explicit
fictional-profile autoplay opt-in, source/cycle/pause guards and existing
manifest/transition routes. A real still, video and enhancement succeeded:
image request `01a1727b-9bc3-7570-bc09-6a0df4e8a29c`, video request
`01a1727b-b438-7813-ab14-df94b6893de8`, enhancement request
`01a1727c-d27c-7730-8fef-0de2211ea6e8`. Video is 5.041667 seconds at
1280×716; enhanced final image is 2560×1432. Visual review confirms new layered
forms, floating spheres and facets during the clip. Unity completed and promoted
it to cycle 4. The initial source was 97% flat background, so a tested preflight
now rejects almost-empty views before billing. Provider styling introduced a
symbol-like center; generative adherence remains approximate, and manual Media
studio remains the review-before-playback option.

Verification: full suites passed 58 backend and 28 frontend tests; final targeted
checks passed 16 demo backend tests and four Unity-controller frontend tests.
The UI reports the remaining provider budget and disables another full journey
when fewer than three calls remain. No automatic billable retry or fake fallback.
README startup/use instructions updated. Live screenshots and provider artifacts
remain ignored under `work/final_demo/` and `work/coordinator/media/`.
EPIC-08 remains In Progress for broader and physical-headset acceptance.
