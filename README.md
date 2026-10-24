# Inner Landscape

An immersive reflection experience: an AI guide will start a conversation while
an abstract landscape becomes defined through words and selected regions.
Development takes place on `master`; `main` is intentionally empty.

Implementation plan: [PLAN.md](PLAN.md). It specifies up-to-30-second media
cycles, Unity/Quest 2, Garmin and the therapist/client platform.

## Connected backend and Unity handoff

```sh
bash backend/scripts/setup.sh
bash backend/scripts/run.sh
```

Open http://127.0.0.1:4173. This starts the Mac session coordinator and serves the
frontend together. Stop any older static server on that port first. Paid provider
operations are **disabled by default**. Garmin live heart rate is available through the Mac Bluetooth receiver,
with session-only baseline/rise cues and automatic disconnect/clear on finish.

- [Backend setup, credentials and verification](docs/BACKEND.md)
- [Unity teammate handoff](docs/UNITY_HANDOFF.md)
- [Garmin connection, spike logic and cleanup](docs/GARMIN.md)

The private ElevenLabs reflection agent is created and verified; its ID is in
ignored `work/elevenlabs-agent.json`. No speech or media-generation smoke test has
run. The voice/media paths are implemented but require bounded live verification.
Unity C# scripts are provided for the teammate; they have not been compiled or
tested on a physical headset here. Use synthetic data only.

## Current frontend

The local frontend is implemented with plain HTML, CSS and
JavaScript. It requires no dependency installation or build step.

Open `frontend/index.html` in a browser, or serve **only** the frontend directory:

```sh
python3 -m http.server 4173 --bind 127.0.0.1 --directory frontend
```

Open http://127.0.0.1:4173. Do not serve the repository root: it contains local
credential files. Python's standard-library server is only for local preview.

### Available flows

- Overview and three fictional client profiles, searchable by name or focus.
- Session preparation: aim, pre-notes, boundaries and optional comfort check.
- Live desktop simulation: select sky/ridges/water, write reflections and reveal
  procedural details only in that region. Each exploration window lasts up to
  30 seconds; starting the next cycle requires a deliberate action.
- Pause/resume, finish, interaction history and practitioner observations.
- Session review, post-notes, comfort check and reviewed status.
- Client presentation mode with welcome, reflection and completion/check-in views.
- Client context notes, session history, notes index and connection status page.

In static mode, notes and sessions use browser-local storage. With the coordinator,
they also persist in SQLite on this Mac. The UI identifies the active mode before
starting. File and HTTP origins may have separate storage. Hidden tabs pause active
sessions; reloading an unfinished session restores it paused. Clear only this
prototype's data through Settings. Storage failure shows a warning.

Use **fictional data only**. This frontend has no authentication or clinical data
protection. Client mode is a presentation preview, not an access boundary. The static preview has no provider connections. The coordinator adds gated
voice/media adapters, Unity pairing and optional local Garmin monitoring. Comfort
checks are not standardized assessments. Static-mode artwork is local SVG. The coordinator can preview and apply provider
media after the paid gate and explicit generation/continuity approval.

The earlier, separate Lovable demo is still available at
https://inner-landscape-dialogue-garden.lovable.app/ . It has not been updated by
this implementation and its source is not synced to this repository.

### Verification

```sh
node --test frontend/tests/*.cjs
node --check frontend/state.js
node --check frontend/app.js
```

Tests cover setup rejection, region isolation/refinement limits, pause, the
30-second boundary, explicit cycle restart, completed-session rules, persistence
and malformed storage recovery. Normal tests need no network or provider keys.

## API setup

See [docs/API_SETUP.md](docs/API_SETUP.md). Local credentials belong in the
Git-ignored root `.env` or `.env.local`, never in frontend code. The frontend
cannot read these files. The private ElevenLabs guide has been configured; its
agent ID is separate from the API key and is kept in ignored local metadata.

### ElevenLabs onboarding

From the repository root:

```sh
npx -y @elevenlabs/cli@latest onboard init
```

Follow the instructions printed by the CLI. When directed:

```sh
npx -y @elevenlabs/cli@latest onboard connect --env-path .env.local
```

Approve browser authorization. The CLI stores `ELEVENLABS_API_KEY` in ignored
`.env.local`. Never print or commit that file. Use the CLI's `onboard check` to
verify credentials rather than reading them. After answering what to build,
follow its next command (currently `onboard check --answered --env-path .env.local`).
Browser authorization has completed on this checkout; SDK installation and private agent creation are complete. Paid voice validation
and physical Unity testing remain pending. The existing manual `.env` and
CLI `.env.local` are separate; the coordinator loads them with the documented
provider-specific precedence. Do not run a paid speech test without approval.

## Layout

- `frontend/`: therapist/client UI and optional coordinator/voice/Garmin connection.
- `backend/`: Python service, pinned dependencies, tests and setup scripts.
- `Assets/`, `Packages/`, `ProjectSettings/`: Unity 6000.6.7f1 project; runtime code in `Assets/InnerLandscape/`.
- `unity/`: Unity entry guide; hardware validation pending.
- `docs/`: API setup, backend instructions and Unity handoff.
- `work/`: ignored local runtime state, agent metadata and generated artifacts.
- `.env.example`: placeholder configuration only; never add real credentials.
- `AGENTS.md`: current project conventions.

The retired mesh application remains in Git history at `8bfaa19`. Legacy local
assets, outputs, caches and the unused Python environment have been moved out of
this workspace. No dependencies are currently required by the local HTML sketch.

## Latest integration verification

Unity runtime code is now inside the root project and the InnerLandscape scene is
selected for builds. See [Unity handoff](docs/UNITY_HANDOFF.md). Unity licensing
is fixed and C# compilation plus editor scene/OpenXR configuration pass. Android
tooling is repaired and a signed development APK is verified at
`outputs/InnerLandscape.apk`. USB deployment and physical Quest checks remain.

Garmin is integrated in the therapist panel and Python coordinator. Run the small
[Garmin broadcast check](docs/GARMIN.md) after enabling broadcast on the watch.
The live Garmin broadcast smoke test now passes; offline tests passed (27 backend,
14 frontend). One authorized ElevenLabs speech check produced a valid 2.8-second
MP3 and the agent signed-URL check passed. Headset conversation and fal generation
remain unverified. Generated check artifacts stay ignored under `work/`.
