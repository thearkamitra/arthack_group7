# Inner Landscape

An immersive reflection experience: an AI guide will start a conversation while
an abstract landscape becomes defined through words and selected regions.
Development takes place on `master`; `main` is intentionally empty.

Implementation plan: [PLAN.md](PLAN.md). It specifies up-to-30-second media
cycles, Unity/Quest 2, Garmin and the therapist/client platform.

## Current frontend

The first local frontend milestone is implemented with plain HTML, CSS and
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

Notes and sessions are saved in browser-local storage. The UI explains this before
starting. File and HTTP origins may have separate storage. Hidden tabs pause active
sessions; reloading an unfinished session restores it paused. Clear only this
prototype's data through Settings. Storage failure shows a warning.

Use **fictional data only**. This frontend has no authentication or clinical data
protection. Client mode is a presentation preview, not an access boundary. There
are no real microphone, AI, generation, headset or heart-rate connections. Comfort
checks are not standardized assessments. All generated-looking artwork is local
SVG; the 30-second window does not play a generated video.

The earlier, separate Lovable demo is still available at
https://inner-landscape-dialogue-garden.lovable.app/ . It has not been updated by
this implementation and its source is not synced to this repository.

### Verification

```sh
node --test frontend/tests/state.test.cjs
node --check frontend/state.js
node --check frontend/app.js
```

Tests cover setup rejection, region isolation/refinement limits, pause, the
30-second boundary, explicit cycle restart, completed-session rules, persistence
and malformed storage recovery. Normal tests need no network or provider keys.

## API setup

See [docs/API_SETUP.md](docs/API_SETUP.md). Local credentials belong in the
Git-ignored root `.env` or `.env.local`, never in frontend code. The frontend
cannot read these files. No ElevenLabs agent has been configured yet; an agent ID
is separate from an API key and will be created during implementation.

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
Browser authorization has completed on this checkout; SDK installation, agent
creation and voice integration remain pending. The existing manual `.env` and
CLI `.env.local` are separate; future backend code must explicitly load the
chosen file. Do not run a paid speech test without approval.

## Layout

- `frontend/`: current local interaction sketch.
- `docs/`: API setup documentation; implementation plan to follow.
- `.env.example`: placeholder configuration only; never add real credentials.
- `AGENTS.md`: current project conventions.

The retired mesh application remains in Git history at `8bfaa19`. Legacy local
assets, outputs, caches and the unused Python environment have been moved out of
this workspace. No dependencies are currently required by the local HTML sketch.
