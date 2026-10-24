# Unity spatial region-entry verification — 2026-10-24

The Editor implementation uses the supplied `Assets/Images/ideal_abstract.jpeg`.
The agent inspected the source, actual Unity camera captures, selected crops,
generated start images and final views. It preserves the prior geometric image
and `Assets/mainscene.unity`; the runtime scene remains
`Assets/Scenes/InnerLandscape.unity`.

## Results

| Check | Result | Local evidence (ignored) |
|---|---|---|
| Real ElevenLabs synthetic participant TTS + conversational guide, center | Passed: participant audio, real transcription event, guide audio | `work/region_zoom_tests/1792877410456200000-center/` |
| Real fal center still + video | Both artifacts decoded; five-second video probed; first/final PNGs extracted | `work/region_zoom_tests/1792877534665411000-center/` |
| Center Unity staged transition and remote pause | Passed with saved live media explicitly labelled REPLAY; all vertices fit, final source promoted to cycle 2 | `work/region_zoom_tests/1792877927032316000-center/` |
| Upper-left full live scenario | Passed: real ElevenLabs exchange, two real fal jobs, Unity playback, remote pause and cycle 2 | `work/region_zoom_tests/1792877975401879000-upper-left/` |
| Final cancellation and upper-left regression | Passed with saved media labelled REPLAY; cancelling an externally owned coroutine restored image/pose without completing | `work/region_zoom_tests/1792878228971054000-upper-left/` |
| Unity attention/framing self-checks | Passed: top-left UV conversion, audible-speech gating, every curved vertex inside view at aspects 0.6, 16:9 and 2.4 | `work/region_zoom_tests/unity-checks.json` |
| Backend unit/service suite | 37 passed; no network/model downloads | `work/region_zoom_tests/backend-final.log` |
| Frontend suite | 19 passed | `work/region_zoom_tests/frontend-final.log` |

Each successful camera run contains `unity-transition.mp4`, before/fit/starting/
final PNGs, `fit.json`, `unity-states.jsonl` and pause pose samples. The final
regression adds `cancel-check.json`. Manifests retain source hashes, attention,
actual provider request IDs, artifact paths and clear LIVE/REPLAY provenance.

Upper-left dwell was 69.7%, center 20.4%, lower-right 10.0% (rounding applies),
with final gaze at center. The winner's centroid was approximately `(0.20,0.08)`;
the crop was `[0,0,0.5,0.5]`, pixels `(0,0,640,360)`. The inspected crop and new
still contain the pink oval and blue star. The held video end view develops
those forms into a deeper abstract space. Center selects cell 4; upper-left
selects cell 0 (zero-based row-major IDs). Pullback fits within approximately
x=0.03–0.97; vertical margins depend on the view.

Both videos were approximately 5.04 seconds. The decoded first-frame mean absolute
RGB difference from the approved still was 0.0086 (center) and 0.0108 (upper-left)
on a 0–1 scale; this measures visual continuity, not pixel identity. Generation is asynchronous and took
minutes rather than the clip's playback duration; the current image stays visible
while waiting. The generated image/video preserve recognizable selected forms
and broad palette, but alter fine texture and invent depth. They are not pixel-
identical crops. Provider charges were bounded to two fal jobs per live scenario;
actual invoice totals were not retrieved.

## Fixes exposed by actual runs

Initial failures remain in their original manifests. The checks exposed and fixed
an invalid new-texture importer, capture before image decode, an exploration timer
expiring during generation, VideoPlayer event registration before its reference
was assigned, preparation overriding the stable texture with black, mock gaze
following the moving surface, unwanted presentation roll, and cancellation of
nested coroutines. Failed Unity runs reused saved live artifacts for further
checks; they did not resubmit billable fal jobs.

Live ElevenLabs sends user text under `user_transcription_event`. The old proxy
expected `user_transcript_event`; the compatibility boundary now handles both and
has a regression test. The upper-left live visual brief used the actual guide
response about the pink oval and blue light. The final runner also incorporates
the actual participant transcript into its reviewed excerpt. Private notes are
never read for these briefs.

## Limits and remaining checks

No physical Quest was available. Stereo, actual head pose/tracking loss, microphone
echo, headset performance and motion comfort are not verified. Editor mock input
does not close those gates. API authority and stale-state checks have offline
tests; remote pause during video and cancellation during pullback have rendered
Play Mode evidence. Exhaustive pause/stop injection at every transition stage,
network failure at every download boundary, and long multi-session stress checks
remain follow-up work. Live conversational audio was collected through the
coordinator and played in Unity for deterministic simulated gaze; this does not
establish real-time Unity microphone streaming quality.

See [setup and commands](UNITY_HANDOFF.md#region-entry-in-editor-2026-10-24) and
[the implementation checklist](UNITY_REGION_ZOOM_PLAN.md). EPIC-08 remains
In Progress because its broader workflow/hardware acceptance is not complete.

## Object-approach correction (prompt version 2)

User review identified that the original generated clip looked like a zoom out.
The new prompt requests a close-up of the existing selected object, followed by
continuous forward magnification until the object's surface fills the frame.
It explicitly excludes tunnel expansion, pullback and shrinking subjects.
Unity now starts and finishes with the image center **0.75 m** ahead of the head
instead of 3 m. The temporary full-frame pullback is retained.

A fresh bounded image/video pair was generated and played successfully in
`work/region_zoom_tests/1792878858107020000-upper-left/`, reusing the previously
verified synthetic voice exchange (clearly recorded in its manifest). The agent
inspected the first and final video frames: the pink oval grows from an object
within the composition into a frame-filling pink surface. This supersedes the
older tunnel-like clip as evidence for the intended generated zoom direction.
Unity framing, cancellation, pause/resume and next-source acknowledgement passed
at the closer viewing distance. Recording: `unity-transition.mp4` in that run.
The backend suite now has 38 passing tests; the frontend suite retains 19 passes.
