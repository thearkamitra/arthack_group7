# Inner Landscape

An immersive reflection experience: an AI guide will start a conversation while
an abstract landscape becomes defined through words and selected regions.
Development takes place on `master`; `main` is intentionally empty.

## Current frontend

Open `frontend/index.html` in a browser. No installation or server is required.
Choose a local image, select a region, and write a reflection. Three scripted
turns sharpen the whole image. This local sketch does not generate imagery,
interpret text, measure gaze, or connect to voice or heart-rate services.

The separate Lovable demo is at:
https://inner-landscape-dialogue-garden.lovable.app/
Its source is not synced to this repository. Local frontend development continues
here. Meta Quest 2/3 and Garmin Venu 4 integration will be planned later.

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
