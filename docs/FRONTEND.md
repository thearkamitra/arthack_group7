# Frontend milestone 1

The coordinator connection, gated voice/media controls and Unity pairing were
added subsequently. Optional Garmin session monitoring has also been integrated; see [GARMIN.md](GARMIN.md). See `BACKEND.md` and `UNITY_HANDOFF.md` for their current
setup and limits. The milestone-1 description below covers the static fallback.

The local source of truth is `frontend/`. No npm packages or external visual assets
are required. Open `frontend/index.html` or use the loopback-only preview command
in the README. The implementation makes no paid API calls.

## Structure

- `index.html`: app shell, metadata and local script/style loading.
- `styles.css`: light ivory/sage design, responsive layouts, focus and reduced motion.
- `state.js`: session state, persistence validation and pure interaction rules.
- `app.js`: views, local storage, navigation and desktop session controller.
- `tests/state.test.cjs`: meaningful offline session-rule and persistence tests.

## Implemented

Overview, search across three fictional clients, client history and context notes,
preparation, optional comfort check, explicit demo acknowledgement, three-region
exploration, 30-second simulated windows, deliberate next cycle, pause/resume,
interaction timeline, separate practitioner observations, post-session review,
reviewed status, notes index, client welcome/session/completion and device status.

Local storage key: `inner-landscape-demo-v1`. Saving is explicit for notes/review;
session events save as they occur. An unfinished session restores paused. Inactive
tabs pause; changing to another screen stops clock advancement until the session
screen returns. Text drafts survive same-screen re-renders, but unsaved form drafts
are not guaranteed to survive navigation or closing the page. Save notes before
leaving their view. Only one unfinished session is allowed. Concurrent editing in
multiple tabs is not supported. Storage is scoped to browser and origin.

## Verification performed

- Seven offline Node tests: invalid setup, selected-region isolation and limits,
  pause/resume, cycle boundary/restart, completed-session lock, persistence and
  malformed-storage recovery.
- JavaScript syntax and Git whitespace checks.
- Browser walkthrough: preparation with a pre-note/check-in, select water, reflect,
  add practitioner observation, pause, reload, finish, save post-note/check-in and
  reviewed status, reload, inspect history and save client context.
- Participant preview: welcome acknowledgement, session start and completion.
- 390px responsive check: client welcome/session and therapist overview had no
  horizontal document overflow. Desktop overview and client welcome inspected.
- No browser console errors during the checked desktop workflow.

## Limits

No authentication, backend, Unity, Garmin, ElevenLabs, fal.ai, generated video or
standardized assessments. The 30-second clock is a foreground browser simulator;
this is not a media player. The guide uses fixed prompts and never interprets
reflections. Region detail is procedural SVG. Comfort ratings are personal
check-ins, not validated outcome measures. Client mode is not a security boundary.
Use fictional content only. Browser-local storage is not suitable for real clinical
records. The previous hosted Lovable demo is separate and has not been updated.

Next work should follow the agreed milestones in `PLAN.md`, starting with the
Unity headset foundation and shared session contracts. A broad library of generated
artwork, video latency and headset comfort still require separate verification.
