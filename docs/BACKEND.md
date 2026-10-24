# Shared coordinator, voice and media

## Run

```sh
bash backend/scripts/setup.sh
bash backend/scripts/run.sh
```

Open http://127.0.0.1:4173. This serves only `frontend/`, not the repository root.
Stop the earlier static server first if the port is occupied. Python 3.10 lives in
hidden `backend/.venv`; this is a small service environment, not the retired ML
stack. `requirements.txt` pins direct dependencies and `requirements.lock.txt`
records the installed environment. Generated state is under ignored `work/`.

- Local desktop still works without a backend. With this server, the browser
  connects automatically and seeds an empty store from its existing local demo.
- SQLite persists sessions/notes and restores unfinished sessions paused after
  a server restart. A revision check rejects conflicts. The browser rebases
  nonconflicting note edits over headset/voice events; same-field conflicts require
  a reload. No last-write-wins overwrite of a remote stop.
- The root page issues a process-local, HttpOnly, SameSite practitioner cookie
  only on loopback. This is a single-practitioner demo bootstrap, not user accounts.
  Browser role preview still isn't a separate authenticated identity.
- Pairing codes are single-use, two-minute codes; participant bearer tokens are
  session-scoped and expire after one hour. Participant responses omit private
  notes. Origin checks block cross-site browser API mutations. No CORS wildcard.
- Do not use this prototype for real clinical records or public hosting. Production
  identity, encryption-at-rest, deletion/retention workflows and audit review remain.

## Credentials

The server reads env files without printing them. Process env wins; ElevenLabs
uses `.env.local` before `.env`, and fal uses `.env` before `.env.local`.
`ELEVENLABS_AGENT_ID`, if provided, wins over the locally created agent metadata in
`work/elevenlabs-agent.json`. That ID is not an API key.

The private reflection guide was created and verified using the official SDK.
Creation does not start a conversation. Repeat safely with:

```sh
PYTHONPATH=backend backend/.venv/bin/python -m inner_landscape.agent
```

Existing local agent configuration is reused; do not delete its metadata casually.
The guide uses English Flash v2 because the account rejected Flash v2.5 during
configuration. No paid speech test has been performed. Raw audio is not saved by
this application; provider retention and consent still require review.

## Paid integration gate

Paid speech tests require user approval. No media-generation tests have run either.
Normal service startup disables paid operations, even with credentials present.
After agreeing a bounded test, use:

```sh
bash backend/scripts/run.sh --enable-paid
```

Voice still requires the explicit Start voice button and microphone consent. Pause,
stop, tab hiding, or coordinator session pause terminates capture/playback. The
browser uses PCM16/16kHz through a backend WebSocket bridge; permanent keys never
reach frontend or Unity. The bridge handles provider pings and forwards bounded
region/cycle context without private pre/post notes. There is no paid end-to-end
voice validation yet; latency, echo and interruption quality remain unverified.

## Media studio

A practitioner provides a short visual brief and explicitly generates a preview.
The current scene is exported as PNG. Only this image/brief is sent to fal; no
profile, pre/post notes or full transcript is sent. Models were schema-checked:

- `fal-ai/flux-kontext/dev`: edit the selected vertical region crop, composite it
  into the original, preserving other RGB pixels. PNG output validated with Pillow.
- `fal-ai/kling-video/v2.5-turbo/standard/image-to-video`: 5-second silent clip
  from the current still. The endpoint supports 5 or 10 seconds, not 30. This
  short clip fits the up-to-30-second exploration window; the last frame holds.

Pricing checked 24 October 2026: image $0.025/megapixel (provider rounding applies),
video $0.042/second. A 5-second video is approximately $0.21 before other fees.
These are rates, not a guarantee of final cost. Four generation jobs maximum per
session; one pending/unknown job blocks another submission. No automatic billable
retry after ambiguous submission or timeout.

Video needs `ffprobe` before a paid request is submitted. Download sizes are
bounded, provider hosts restricted, durations checked (≤30 seconds), and artifacts
stored locally with hashes, model/request IDs, parameters, prompt version, status
and output locations in per-job manifests. Failed generation keeps the prior scene.
Unknown provider requests must be reconciled on the provider dashboard; automated
reconciliation/cancellation is not implemented. Restarted in-flight jobs need the
same manual reconciliation, not a new paid submission.

A ready preview does not apply itself. **Confirm continuity & use** records a
practitioner confirmation and rejects paused/completed/stale cycles. This is a
human visual check, not an automated VR/region-map validation. Generated video can
move landmarks; do not claim preserved geometry or stereo depth.

## Verification

```sh
PYTHONPATH=backend backend/.venv/bin/python -m unittest discover -s backend/tests -v
node --test frontend/tests/*.cjs
```

Normal tests are offline and use temporary SQLite stores. API checks cover
practitioner/participant isolation, single-use pairing, conflict detection,
command deduplication, tracking-loss pause, stale media, paid gates, persistence,
input validation and preserving original image data. Provider generation and
microphone calls remain untested live. See `UNITY_HANDOFF.md` for hardware checks.

## Garmin

**Optional local BLE integration.** The Mac coordinator scans and connects using
Bleak, with explicit frontend consent, baseline and sustained-rise pacing cues,
and automatic disconnect/data clearing. See [GARMIN.md](GARMIN.md) for steps,
thresholds, lifecycle and verification limits. The shared parser is also used by
the working research CLI. Garmin Connect/cloud APIs are not used. Sessions still
work without a watch.

### Spatial region-entry API

`POST /api/sessions/{id}/canonical-scene` (therapist) loads the checked-in Unity
JPEG as lossless PNG and records its SHA256. Pairing in the browser uses this
source. `spatial_decision` participant command accepts cycle/source_hash,
input_mode (`xr`, `mouse`, `scripted`), speaking_seconds, distinct window_ids and
nine row-major cells `{seconds,x,y}` in top-left normalized coordinates. The
coordinator validates and freezes the longest-dwell cell, percentages, coverage
and aspect-preserving clamped 50% crop once per cycle. This is head direction,
not eye tracking. Raw head poses are neither stored nor sent to providers.

`POST /api/sessions/{id}/region-entry` is therapist-only, with an explicitly
approved `excerpt` of 1–600 characters. It creates a new scene from the selected
crop using the existing fal image endpoint. Calling again with `parent_job` from
the ready image creates a 5-second inward-motion video. It cannot resubmit an
existing decision/job. Existing patch-edit generation remains available. Video
validation extracts authenticated `/media/{job}/frame/first` and `/frame/final`
PNG artifacts with hashes. The usual media apply endpoint approves the complete
video bundle; Unity's `transition-complete` acknowledgement promotes the final
PNG as the next source and advances the cycle idempotently. Pause/completion,
stale source and stale cycle checks remain enforced. Each entry consumes two of
the four allowed jobs; one billable job can be pending at a time.

`spatial_select` explicitly confirms `{cycle,source_hash,input_mode,x,y}` when no
audible guide attention exists. It is recorded as `manual:true`, with zero dwell
and zero coverage. It shares the same once-per-cycle and stale-source checks.

Region-entry v3 adds a sequential `fal-ai/clarity-upscaler` call to each video
bundle. `billable_units` is 1 for image and 2 for an entry video (video plus final
image enhancement). Legacy jobs default to one unit. Budget checks sum units;
three units must remain before starting a new transition. The final PNG must
have a long edge of at least 2560 pixels, preserve aspect ratio, and stay within
the existing eight-million-pixel bound. PNG upload limits allow up to 32 MB of
encoded image data for high-resolution next-cycle sources; video inputs use a
quality-95 JPEG derivative with a separate hash, retaining the source PNG.
The provider's native edited still is preserved instead of shrinking it to a crop
and enlarging it again. The clip's original final PNG remains alongside the
AI-enhanced final PNG; the latter is the approved next source.
