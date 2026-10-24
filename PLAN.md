# Inner Landscape — implementation plan

Status: proposed; implementation has not started.
Target: Mac development, Unity application on Meta Quest 2, Garmin Venu 4,
ElevenLabs conversational guide, fal.ai imagery/video, and a therapist web console.
Active branch: `master`. `main` remains empty.

## 1. Experience and scope

Build a therapist-supervised reflective art experience. A client explores an
initially abstract landscape. Head direction, the conversation, explicit choices
and prior exploration influence which region becomes more defined next. The
therapist can observe the session, record notes and override progression.

**Each exploration cycle plays a video of no more than 30 seconds.** Thirty
seconds is the media window, not a promised generation latency or a deadline for
the client to answer. Do not generate five-minute videos. Several cycles can form
a longer session; a five-minute session length is optional, not a requirement.
Use shorter clips if the chosen model's supported durations require it. Verify
actual exported duration before playback; trim longer output to the approved
window only when needed and keep the source intact.

MVP: one client, one therapist, one Quest 2 and one Mac on a trusted local network.
Use synthetic participant records for the hackathon demonstration. This is not
an autonomous treatment or diagnostic system.

## 2. Session journey

### Before the session

1. Therapist opens a client profile and reviews earlier sessions, approved
   summaries, assessment history and their own notes.
2. Add pre-session notes, session aim, allowed topics, excluded topics and visual
   preferences. Keep private therapist notes out of the AI context by default.
3. Client sees a short explanation of voice processing, head-direction tracking,
   optional heart rate and what is saved. Obtain separate recording consent.
4. Complete a brief comfort/readiness check and an optional therapist-selected
   standardized questionnaire. The questionnaire can be skipped or deferred.
5. Confirm headset, audio, network and Garmin status. Missing Garmin must not
   prevent a session; explicitly show that heart-rate input is unavailable.
6. Therapist starts the session. The AI guide asks the opening question, such as
   “Take a moment to look around. What draws your attention?”

### Repeating exploration cycle

1. Show a large landscape image with several named regions. Only part fits in
   the headset view at once; natural head turning reveals more of the composition.
2. Collect head-direction dwell and return visits while the client looks around.
   Let the client confirm interest verbally or with a controller. Looking alone
   is a suggestion, not permission to pursue a sensitive topic.
3. At a conversation boundary, combine attention aggregates, the current answer,
   previous questions, explored regions and therapist constraints.
4. Propose a next region and a brief, non-leading question. The client can choose
   it, choose another, stay, pause or stop. The therapist can override it.
5. Refine the selected region of the current image, retaining the wider scene,
   visual style and stable landmarks. Submit a video job anchored to that image.
6. While generation runs, retain the previous still/last frame with gentle local
   ambient animation. Conversation can continue without pretending video is ready.
7. Validate the completed clip, then play it for up to 30 seconds on the same
   spatial surface. Do not automatically move the camera or the client's body.
8. End on a stable still. Ask what the client noticed, update the session state,
   and offer the next cycle. Never repeat an ended clip as if it were a new result.

### After the session

- Therapist or client ends the session at any point.
- Offer a short immediate comfort check and optional client reflection.
- Show the therapist a chronological interaction history, region journey,
  available heart-rate observations, generation events and client statements.
- Produce an editable AI summary with links to supporting events. Mark it as a
  draft until the therapist reviews it. Do not infer diagnosis or treatment success.
- Save post-session notes separately from AI-generated content. Keep notes and
  assessments available for subsequent sessions within the agreed retention policy.

## 3. Headset presentation and region tracking

Use Unity with OpenXR and a Quest-compatible interaction stack. Pin exact editor
and package versions after a small physical-headset compatibility test.

Quest 2 has no eye tracking. UI, logs and pitch must say **head-directed attention**,
not eye gaze or measured psychological focus.

Initial rendering choice: one large, world-anchored curved image/video surface in
a simple 3D room. It should extend beyond the visible viewport but remain at a
comfortable distance. This provides a 3D viewing space without generating meshes.
Keep the surface stable during head turns and video transitions. Recenter through
an explicit action. No smooth locomotion is required.

- Cast a ray from the tracked head camera's forward direction to the media surface.
- Convert the hit into canonical image UV coordinates and then a region ID.
- Aggregate dwell/visits over the current clip and recent history. Smooth short
  fluctuations and use hysteresis at region boundaries.
- Initial tuning proposal: approximately 1.5 seconds of dwell to highlight interest;
  sample observations around 10 Hz and send aggregates around 1 Hz. These are
  prototype values to tune in the headset, not validated attention thresholds.
- Retain image UV coordinates independently of video resolution or screen size.
- Every media version carries a region map. Reject or remap a generated result
  if landmarks moved enough to invalidate that map. A crop must update UV mapping.
- First video prototype animates the whole current composition with restrained
  motion; reliable region-preserving video edits are a feasibility test, not assumed.
- Freeze progression on tracking loss or headset removal. Resume only with a valid
  pose and explicit readiness; do not count missing tracking as attention.
- Desktop simulator uses pointer selection and labels the input as simulated.

## 4. Choosing the next region

Keep one authoritative session coordinator on the Mac. The AI proposes language
and meaning; application rules validate and apply changes.

Decision inputs:

- Current/previous confirmed region, dwell distribution, return visits and confidence.
- Latest client response, concise conversation summary and questions already asked.
- Regions explored and their refinement depth; previous recommendations/declines.
- Client preferences, session goal, allowed/excluded topics and therapist commands.
- Fresh heart-rate observations relative to the session baseline, if available.
- Readiness/comfort check-ins and approved assessment context, if appropriate.

Decision order:

1. Stop/pause requests, therapist intervention and tracking loss take precedence.
2. Respect exclusions and explicit client choices. Never turn avoidance into a
   mandate to explore something uncomfortable.
3. Rank allowed candidates by recent dwell and return visits, conversational
   relevance, continuity and whether the region was recently explored/declined.
4. Use simple documented heuristic weights initially. Return a plain-language
   reason and the observations used; do not present the rank as clinical certainty.
5. Ask a clarifying question when attention is ambiguous or answers conflict.
6. Ask for client confirmation before a new chapter or meaningful topic change.
7. Log the proposal, reason, evidence IDs, confirmation/override and applied result.

Heart rate participates in **pacing/readiness**, not semantic topic selection.
A sustained change can prompt a neutral check-in or surface a therapist cue;
only the response or therapist instruction changes the exploration decision.
Do not derive anxiety, emotional valence, truthfulness or diagnosis from pulse.
No universal medical alert thresholds will be invented for the prototype.

## 5. Garmin Venu 4 connection

Initial route: watch Broadcast Heart Rate → Bluetooth LE → Mac sensor bridge →
session coordinator → therapist console and optional Unity ambient rhythm.

- Test the watch's Bluetooth heart-rate broadcast on the actual Mac first.
- Use a small Python BLE adapter, with a pinned library selected during setup.
  Parse heart-rate measurement format, timestamp receipt and validate readings.
- Record connected/disconnected status, last-sample age and availability. Do not
  invent sensor accuracy/confidence fields the device does not supply.
- Collect a brief seated baseline when possible. Display raw readings and a
  smoothed trend; baseline is context, not a medical reference or score.
- Stop adapting to sensor input when stale. Initial freshness cutoff proposal:
  10 seconds without a sample, configurable after the hardware test.
- Reconnect with bounded retries and show missing sections as gaps, not zero BPM.
- Do not assume HRV, stress, respiration or Body Battery are part of the broadcast.
  Richer metrics are out of MVP scope until device/API support is verified.

## 6. System boundaries and communication

| Component | Responsibility |
| --- | --- |
| Therapist/client frontend | Profiles, notes, checks, session controls and history |
| Python coordinator on Mac | Session state, rules, API credentials, events and media jobs |
| Garmin adapter on Mac | BLE reception and time-stamped heart-rate observations |
| ElevenLabs agent | Spoken guide, transcription and context-aware dialogue |
| fal.ai adapter | Image refinement and asynchronous image-to-video jobs |
| Unity Quest app | Head tracking, media display, audio/input and immediate pause |
| Local session store | Notes, assessments, event log, approved summaries and manifests |

Add `backend/` only during implementation. Use Python 3.10, a newly explicit minimal
virtual environment and pinned dependencies; do not restore the retired ML stack.
A small HTTP/WebSocket service becomes justified by the headset and console.
Use REST for configuration/history/media references and WebSocket for session
events and controls. Start with a minimal Python service and SQLite on the Mac;
choose exact maintained versions during implementation.

Unity runs as a standalone Android build on Quest 2. Build/deploy from the Mac
with Android Build Support, SDK/NDK and OpenJDK. Do not depend on Windows-only
PC VR or assume macOS Quest Link. Validate developer mode, USB deployment,
permissions and local-network connectivity before integrating AI.

Both Quest and therapist browser connect to the Mac service. The headset cannot
use the Mac's `localhost`; pair using the Mac's LAN address and a short-lived
session credential. Do not publicly expose the local service. Use authenticated
connections and secure transport before using real client data off-loopback;
development transport exceptions are limited to synthetic test data.

Prototype voice transport: Quest microphone → Mac voice bridge → ElevenLabs;
stream returned audio to Unity. Start with documented agent WebSocket events and
measure latency/echo behavior on hardware. Speech pauses/interruptions must cancel
pending playback. Never capture microphone audio before user consent/start.
A direct Unity/provider connection is an alternative only after testing supported
transport and short-lived credentials; permanent API keys never ship in the APK.

## 7. Shared event and session model

Define contracts before coding so desktop, Unity, voice and sensor implementations
can be replaced independently.

Core records:

- Client: pseudonymous ID, therapist assignment, consent/preferences.
- Session: client/therapist IDs, goal, status, start/end, active cycle and media.
- Note: pre/during/post phase, author, time, version and visibility.
- Assessment: instrument/version/language, exact responses, completion status,
  validated scoring version, result and therapist review.
- Attention summary: media/region IDs, window, dwell, visits, tracking availability.
- Heart-rate observation: BPM, source, receipt time, connection/freshness state.
- Conversation turn: speaker, text, time, source; audio retention disabled by default.
- Decision: candidate region, reason, input event IDs, confirmation and applied action.
- Media job: input/output hashes, prompt version, provider/model, parameters,
  request ID, duration, region map, status, errors and artifact paths.

Every event includes `event_id`, `session_id`, `cycle_id` where relevant,
`source`, timestamp and schema version. Measure device-clock offset at pairing;
retain local monotonic time for ordering. Use unique command IDs and acknowledgments
for start/pause/stop; deduplicate retried commands and reject outdated cycle results.

Session states: setup → ready → active ↔ paused → completed, with explicit error
and reconnect handling. Media job states are separate: queued → running → validating
→ ready → playing → finished, or failed/cancelled. A completed job never starts a
paused session or replaces a newer cycle. Stop works locally even when disconnected.

## 8. ElevenLabs integration

- Existing API key is configuration; no agent exists yet. Create the reflection
  agent during the voice milestone and record its agent ID separately.
- Resume the official CLI onboarding check before SDK/code setup as instructed.
- Guide behavior: open the conversation, ask one short question at a time, allow
  silence and interruption, avoid diagnosis and suggestive interpretations.
- Send bounded contextual updates at conversation boundaries: confirmed region,
  recent dwell summary, explored topics, preferences and pacing status. Do not
  stream raw head samples or private therapist notes into the prompt.
- Separate permitted actions such as `propose_region`, `request_check_in` and
  `request_pause` from validated application commands. The agent cannot edit
  records or apply an unchecked generation prompt.
- Backend validates all actions against current session, therapist rules and
  schema. System stop/override commands cannot be overridden by model output.
- Explicit approval before a paid speech/conversation integration test.

## 9. fal.ai image and video generation

Use provider adapters so the application is not coupled to one endpoint.
At implementation time discover current image-edit and image-to-video candidates,
inspect exact schemas, supported durations, resolution and pricing. Do not assume
an endpoint accepts 30 seconds or arbitrary crops, masks or video edits.

Pipeline: canonical image + confirmed region + bounded conversation-derived visual
brief → region-preserving image edit → validated image → image-to-video job →
validated clip of at most 30 seconds → Unity playback → stable continuation image.

- Begin with one abstract landscape and curated visual briefs, then introduce
  conversation-driven refinement once the interaction works.
- Prefer reference/mask-based edits when supported. Do not send client identifiers,
  notes or full transcripts to the media provider; use a minimal visual brief.
- Video guidance: gentle environmental motion, stable framing and landmarks,
  no camera shake, sudden cuts or unintended threatening imagery.
- Use async submission, bounded polling, explicit timeout/cancellation and maximum
  one in-flight generation per session. Generate only after a confirmed decision.
- Record request IDs; do not automatically resubmit a billable job after an
  ambiguous timeout. Reconcile its status first. Set session cost/cycle limits.
- Verify decoding, dimensions, duration, continuity and region alignment. Show
  failed jobs honestly; keep the prior scene and offer retry or still-image mode.
- Prefetch only when the intended next step is confirmed. Cloud latency can exceed
  clip duration; never promise gapless real-time generation.
- A clip is a flat video in a 3D environment, not stereoscopic volumetric video.
  Full 3D generation, Gaussian splats and navigable generated worlds are later work.

## 10. Therapist and client frontend

Build locally under `frontend/`; Lovable is optional and its existing demo is
reference material, not the source of truth. Start with plain TypeScript/Vite
for structured UI and API integration; add a UI framework only if the component
complexity warrants it. Pin package versions during implementation.

Visual language: warm off-white background, soft sage/sky accents, charcoal text,
generous spacing, fine borders, restrained shadows and a clear type hierarchy.
Maintain readable contrast, visible focus, large targets and reduced-motion support.
Use subtle animation, not pulsing dashboards or flashing sensor alarms.

### Therapist views

1. Client list: minimal session history/status, search and start-session action.
2. Client detail: earlier sessions, reviewed notes, assessment trends and preferences.
3. Session preparation: aim, pre-notes, consent, optional questionnaire and device check.
4. Live session: current media/region, conversation timeline, chronological decisions,
   HR trend with gaps, device status, brief notes and pause/stop/override controls.
5. Session review: journey summary, transcript excerpts where consented, pre/post
   check-ins, draft summary, post-notes and explicit therapist approval/save.

Keep the live screen focused on the current conversation and controls. Put detailed
telemetry behind disclosure; do not expose credentials or internal prompt controls
in client flows. Display human-authored notes and AI drafts distinctly.

### Client views

- Welcome, explanation/consent, simple readiness check and selected questionnaire.
- Headset pairing/start instructions; plain alternatives when a device is missing.
- In-headset: artwork, brief guide captions and easy pause/stop; no therapist records.
- Post-session reflection and completion. Full transcript/notes visibility follows
  explicit clinician/client access settings, not a shared browser state.

For the MVP, simulate records locally until persistence and role separation work.
A demo role switch must be labelled as simulation; it is not authentication.

## 11. Questionnaires and check-ins

Implement a configurable assessment workflow, not an AI-invented standardized test.
A therapist chooses the instrument and decides how results inform the next session.
AI may suggest a check-in for review; it must not prescribe treatment from a score.

Candidate for clinician review: WHO-5, a five-item well-being instrument covering
**the past two weeks**. Preserve its validated language, response scale, version
and scoring, and review licensing before embedding. Do not rewrite it as a
30-second mood test or use an immediate repeat as evidence of treatment efficacy.
Do not copy questionnaire text into implementation until selection/reuse is agreed.

For immediate pre/post comparison, use clearly labelled non-standardized comfort
or readiness ratings and an optional free-text reflection. Never call those
validated clinical assessments. Handle missing answers explicitly; do not score
an incomplete form as complete. Any risk-signalling response follows a
therapist-defined review workflow and does not silently trigger deeper content.

## 12. Data access and controls

- Demo uses synthetic clients. Real client use requires an agreed access,
  consent, storage, provider-retention and deletion policy before deployment.
- Separate therapist-only notes, client-entered data and model context.
- Keep permanent fal/ElevenLabs keys on the Mac backend. Explicitly choose which
  of `.env` or `.env.local` supplies each value; validate presence without printing.
- Allow session-only mode. Make saving conversation/attention/heart rate explicit;
  questionnaire and note persistence follow clinician-selected retention settings.
- Persist only necessary aggregates; raw audio/head-pose retention off by default.
- Authenticate therapist sessions and bind headset credentials to one active session.
  Enforce permissions on the backend; hiding a UI section is insufficient.
- Client/therapist can stop immediately. Stop cancels local playback and future
  transitions even if a remote media job cannot be cancelled.
- Do not claim medical compliance or clinical validation from a hackathon demo.

## 13. Delivery milestones and acceptance checks

| Stage | Deliverable | Completion evidence |
| --- | --- | --- |
| 0. Contracts and scope | Agreed cycle, region map, events, retention and UI flow | Review this plan; sample events and clear ownership |
| 1. Desktop vertical slice | Light therapist/client UI, simulated sessions and local media | Start/select/respond/pause/finish; notes persist/reload; no fake live sensors |
| 2. Quest foundation | Unity Android app, large still/video surface, region UV tracking | Install on physical Quest 2; head turn selects expected region; stable frame time and stop |
| 3. Shared session service | Mac coordinator, event store, paired console and headset | Same session state/timeline; authorized controls; reconnect/dedup and stale result rejection |
| 4. Garmin | Live BLE heart rate and freshness display | Venu 4 data visible on Mac/console; disconnect becomes a gap; no emotion labels |
| 5. AI guide | Created ElevenLabs agent and streamed conversation | After test approval: AI opens; region context affects follow-up; interruption/pause works |
| 6. Still generation | fal image editing on confirmed region | Expected artifact decodes; continuity reviewed; original retained; failure keeps prior scene |
| 7. Video cycle | Async clip generation and Unity playback, each ≤30 seconds | Duration checked; head-directed regions remain valid; no forced waiting or stale playback |
| 8. End-to-end demo | Therapist preparation → repeated cycles → review/notes | One complete synthetic session on real headset; summary and notes reload correctly |

Priority: achieve a complete still-image/voice/headset loop before adding generated
video. Keep a prepared clip as an explicitly labelled demo fallback. Garmin can
remain unavailable without blocking the core experience. Do not rebuild the old
mesh pipeline to satisfy this scope.

Verification includes meaningful unit tests for region mapping/dwell, precedence,
stale sensors, cycle deduplication, assessment scoring and incomplete forms,
role-restricted notes, media validation and job failures. Use mocked providers
for normal tests; hardware/API checks are separate, bounded and reported honestly.
Measure actual clip-generation time, voice latency and Quest frame time; choose
supported encoding/resolution from a physical playback test, not desktop success.

## 14. Open decisions before dependent implementation

- Available hackathon time and how much Unity setup already exists.
- Exact Unity/OpenXR versions supported by the team's Quest 2 setup.
- Who operates the therapist role in the demo; whether any clinician is advising.
- Session length/cycle budget and whether every clip needs therapist approval or
  client confirmation within pre-approved constraints is sufficient.
- Which standardized questionnaire, language and permitted reuse are appropriate.
- Whether this version remains LAN-only or needs authenticated remote access.
- Final media endpoint selection, per-session spend cap and acceptable wait time.
- Which env file is authoritative for each provider; agent creation is still pending.

These choices do not block the first local UI prototype with synthetic records,
but hardware, paid calls and clinical assessment work wait for their relevant gates.

## 15. References and assumptions

Verified references (24 October 2026); hardware behavior and compatibility still
require local testing. Prototype timing thresholds and stack choices above are
engineering proposals, not provider guarantees or clinical recommendations.

- Meta tracking compatibility (Quest 2 has no eye tracking):
  https://developers.meta.com/vr/documentation/unity/move-overview/
- Meta OpenXR support and physical-device testing:
  https://developers.meta.com/vr/documentation/unity/unity-openxr-settings-quest/
- Garmin Venu 4 broadcast instructions:
  https://www8.garmin.com/manuals-apac/webhelp/venu4/EN-SG/GUID-54BDBD11-B809-4503-B99B-B15E366F777B-1577.html
- Garmin Bluetooth broadcast compatibility:
  https://support.garmin.com/in-ID/?faq=Zj1947s6pqAHzBCAhLhrC9
- ElevenLabs contextual updates/voice transport:
  https://elevenlabs.io/docs/eleven-agents/libraries/web-sockets
- ElevenLabs tools:
  https://elevenlabs.io/docs/eleven-agents/customization/tools
- WHO-5 description and two-week reference period:
  https://www.who.int/publications/m/item/WHO-UCN-MSD-MHE-2024.01
- fal generation API starting point (model-specific duration/schema to verify):
  https://fal.ai/docs/documentation/quickstart
