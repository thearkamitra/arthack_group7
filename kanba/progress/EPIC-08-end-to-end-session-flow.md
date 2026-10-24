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

- [ ] **Reported frontend warning:** “Coordinator unavailable. Reload before continuing on another device.” Investigate the actual `/api/workspace` response status from the affected browser. The coordinator was confirmed listening on port 4173, and Unity was running. No root cause or fix has yet been verified.
- [ ] **Authentication hypothesis:** server restarts generate a fresh in-memory practitioner token, invalidating the old browser cookie. Reloading the root page is the existing local authentication bootstrap. Check whether the failing request is 401 before treating this as the cause; distinguish authentication loss from transport/backend errors in the UI if confirmed. Preserve current session data and drafts.
- [ ] **Interactive inspection:** the browser tool still denies observing `http://127.0.0.1:4173/`, citing a saved permission or managed policy, including after the user reported enabling access. This is a separate tool-access issue, not proof of a backend or Unity fault. Inspect Settings → Browser for the exact origin or a managed rule; do not work around the denial through another browser surface.
- [ ] **Actual frontend microphone conversation:** verify only after explicit user start/consent; mocked audio timing and prior real provider runs do not establish this live browser microphone check.
- [ ] **Physical Quest acceptance:** retain the existing hardware gates; do not infer a headset pass from Editor rendering.

Untracked `Assets/_Recovery/` and `Assets/_Recovery.meta` are preserved and excluded
from commits. They are not part of the implementation or acceptance evidence.
See [browser demo setup and evidence](../../docs/BROWSER_UNITY_DEMO.md).
