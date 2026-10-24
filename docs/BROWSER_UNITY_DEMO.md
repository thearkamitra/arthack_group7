# Browser-controlled Unity demo

The no-headset demo uses the frontend for the conversation, camera controls,
region confirmation and media review. The image shown in the browser is a live
Unity camera preview, not a second simulation of the landscape. Arrows rotate
the actual Unity camera; its head ray produces spatial attention aggregates.
This remains mock head input, not eye tracking.

## Start

1. Start the coordinator with `bash backend/scripts/run.sh --enable-paid`.
   Existing approved voice/media credentials stay on the Mac.
2. Open this repository in Unity 6000.6.7f1. Leave it open; save any unsaved scene
   edits. The browser launcher deliberately does not replace a dirty scene.
3. In the frontend, create or resume a fictional session and click **Use browser
   + Unity demo**. This preserves the current session image, loading the canonical
   image only when no image exists. The explicit button publishes a single-use,
   local-only Editor pairing offer, expiring in two minutes. The open Editor
   enters Play Mode and pairs without typing a code. An already-running Editor
   in Play Mode can accept the offer too.
4. The main image area becomes the live Unity view. Click the arrow buttons or
   use the arrow keys; keys do not steer while typing into a form. Center resets
   the mock head to world-forward. A tracked paired headset takes precedence and
   disables browser arrows. Disconnected Unity shows a waiting state.
5. Click **Start voice guide**, accept its disclosure and the browser microphone
   permission. Talk and listen through the frontend. Audio uses the existing
   coordinator/ElevenLabs connection; Unity's microphone is not started. Audible
   playback timing gates Unity's dwell measurement. Queued chunks, transcript
   arrival and silence do not count as speaking. This applies in both the main
   session page and its Client view.
6. Click **Confirm most-looked region** when ready. Open **Media studio**: the
   visual brief is prefilled only from recent ElevenLabs guide/reflection events,
   never private notes. Review/edit it and generate the starting still. Approve
   the start image, generate the video plus enhanced final image, then approve
   continuity. Unity runs the existing transition and promotes the final image.
   These steps retain the three-call transition/four-call session budget.

Camera arrows and confirmation are disabled during transitions or session pause.
Pause/stop and hiding the browser stop frontend voice; stale speech reports expire
within one second. Unity's normal session connection hold still applies.

## Connection and privacy boundaries

- Demo state, yaw/pitch and preview JPEGs stay in coordinator memory and expire
  from the live view after disconnection. They are not written into session data.
- The local Editor offer requires a prior therapist-authenticated button click,
  a loopback client and no browser Origin header; it is single-use and short-lived.
  The usual participant token is then used for Unity's presence and frame uploads.
- Frames are bounded to 1280×720 and 700 KB encoded; the current sender uses
  960×540 JPEGs around four times per second. The preview is intentionally lower
  resolution than the held final scene image to limit local traffic.
- Browser controls, speech gates and camera previews require the therapist
  session cookie. Participant tokens cannot drive the arrows or read the preview.
- A recent tracked XR heartbeat prevents an Editor heartbeat or browser command
  from displacing the headset. Real Quest tracking and microphone quality still
  require physical hardware checks.

## Verification

```sh
PYTHONPATH=backend backend/.venv/bin/python -m unittest discover -s backend/tests
node --test frontend/tests/*.test.cjs
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/check_browser_demo.py
```

The last command opens a bounded batch Unity Editor on the same project and uses
an isolated coordinator on port 4175. Close another Editor instance for this
project first. It makes no provider calls and captures no microphone audio.
Evidence is stored under ignored `work/browser_demo/{run_id}/`: center and
left/up JPEGs, a frozen non-manual attention decision and a run manifest.

The initial run at `work/browser_demo/1792880492957860000/` passed: automatic
pairing, live frame upload, rendered view change after arrows and confirmation of
about 2.1 seconds of attention gated by frontend speech heartbeats. The final
run `work/browser_demo/1792880937225415000/` also passed and confirms a clean
artwork preview with native Unity controls hidden in browser-controlled mode.
The final suites passed 47 backend tests and 23 frontend tests. Backend tests
cover headset priority, disconnect expiry, authorization, single-use offers and
out-of-order speech. JavaScript tests verify queued audio does not start the
speaking window, stop releases audio/microphone resources, and unavailable/headset
controls do not issue movement requests. Interactive browser visual inspection
and an actual microphone conversation have not been verified in this task:
the browser tool's saved origin permission remained denied after authorized
retries. Earlier live ElevenLabs/provider checks remain documented separately.


## Reported coordinator refresh warning

The frontend warning “Coordinator unavailable. Reload before continuing on another
device” currently covers any failed `/api/workspace` refresh, including an HTTP
error. A live coordinator process alone does not prove that the affected browser
request is authorized. Server restarts replace the in-memory practitioner token,
so a previously open tab may retain a stale cookie; loading the root page is the
existing local authentication bootstrap. This is a hypothesis for the reported
warning, not a verified diagnosis. Next check the affected request's HTTP status
and preserve drafts/session data while investigating. The agent browser tool's
saved-origin denial is separate from this application-level warning.
