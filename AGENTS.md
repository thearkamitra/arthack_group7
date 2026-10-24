# Project conventions

## Current scope and layout
- Inner Landscape is a guided reflection art experience, initially a large 2D
  image on a Mac. Future integrations are ElevenLabs, fal.ai, Garmin Venu 4 and
  Meta Quest 2/3. Do not assume clinical efficacy or infer emotions from pulse.
- Work on `master`; `main` is intentionally empty. Push authorized completed work.
- Keep frontend code under `frontend/` and documentation under `docs/`.
- The shared Python coordinator, dependencies, setup and tests live under
  `backend/`; use its minimal hidden `.venv` with Python 3.10. Pin direct
  dependencies and retain the installed environment snapshot. Unity teammate
  source stays under `unity/`. Garmin is deferred as an independent workstream.
- The former Auto-MIA pipeline and its environment are retired. Do not restore
  the submodule, mesh dependencies or historical training artifacts by default.

## Task board workflow
- Read `kanba/README.md` and the matching task card before picking up work.
  Use the `arthack-kanban-flow` skill when available (installed locally at
  `/Users/arkamitra/.codex/skills/arthack-kanban-flow/SKILL.md`).
- When taking a task, move its existing card to `kanba/progress/` before
  implementation and set Status to `In Progress`; do not leave a copy behind.
- When all acceptance criteria are verified, move the card to `kanba/done/`,
  set Status to `Done`, and record completion evidence. Partial work stays active.
- Move blocked work with no independent next step to `kanba/needme/`, with the
  blocker and required user/hardware action; resume by moving it back to progress.
- After each move, remove the old board-column entry, add the new one in
  `kanba/README.md`, fix inbound links, and verify one card file per stable ID.

## Implementation
- Plan integrations before implementation. Clearly label mock or simulated
  behavior, disconnected services and limits of attention tracking.
- Keep credentials in ignored `.env` or `.env.local`, never in frontend code,
  logs, chat, Git or VITE_-prefixed variables. `.env.example` is placeholders only.
- Preserve user source inputs and existing runs. If generated files are needed,
  use explicit ignored assets/output/run/cache locations and per-run manifests
  with inputs, parameters, commands, status and output locations.
- Validate inputs before expensive work; propagate failures and retain useful
  logs without secrets. Prefer reusable typed functions and small modules.
- No unnecessary web frameworks or service infrastructure. Use server-side
  credentials and usage controls when integrating paid APIs.

## Verification and communication
- Verify actual behavior and expected artifacts; do not infer success from an
  exit status alone. Report checks actually run and material unverified limits.
- Unit tests must not require network or model downloads. Integration checks
  must be explicit and bounded; paid speech tests require user approval.
- Keep README commands and current code consistent. Avoid unrelated changes,
  destructive Git operations, and committing environments, caches or user data.
