# Inner Landscape — Kanban Board

This board tracks the implementation milestones defined in [PLAN.md](file:///Users/arkamitra/Documents/ChatGPT/arthack/PLAN.md) across four columns:
- [`kanba/done/`](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/done): Completed and verified epics.
- [`kanba/needme/`](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/needme): Epics and gates currently blocked on user action, credentials, or physical hardware.
- [`kanba/progress/`](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/progress): Epics currently in active implementation.
- [`kanba/backlog/`](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/backlog): Epics and tasks queued for development.

---

## Card lifecycle

When picking up work, move the existing card to `kanba/progress/` and set its
status to **In Progress**. On verified completion, move that same card to
`kanba/done/` and set it to **Done**. Remove the old column entry, add the new one,
and repair links after each move; never leave duplicate card files behind.
Blocked work belongs in `kanba/needme/` until it can resume. A partially completed
epic stays in progress or blocked until its full acceptance criteria are met.

See `AGENTS.md` and the installed `arthack-kanban-flow` skill for the workflow.

## Board Overview

| Done | In Progress | Need Me | Backlog |
| :--- | :--- | :--- | :--- |
| [EPIC-00: Contracts](done/EPIC-00-contracts-and-scope.md) | — | [EPIC-02: Unity compile and headset checks](needme/EPIC-02-quest2-unity-integration.md) | [EPIC-05: ElevenLabs live conversation](backlog/EPIC-05-elevenlabs-voice-integration.md) |
| [EPIC-01: Desktop](done/EPIC-01-desktop-vertical-slice.md) | | [EPIC-04: Garmin physical broadcast](needme/EPIC-04-garmin-ble-integration.md) | [EPIC-06: fal media](backlog/EPIC-06-fal-media-pipeline.md) |
| [EPIC-03: Coordinator](done/EPIC-03-shared-coordinator-service.md) | | [NEEDME-02: Quest deployment](needme/NEEDME-02-quest2-hardware-deployment.md) | [EPIC-08: End-to-end demo](backlog/EPIC-08-end-to-end-session-flow.md) |
| [NEEDME-01: API approval received](done/NEEDME-01-paid-api-approval.md) | | [NEEDME-03: Watch test](needme/NEEDME-03-garmin-watch-broadcast-test.md) | |

---

## Milestone Traceability (PLAN.md Section 13)

- **Milestone 0**: Agreed cycle, contracts, and boundaries ➔ [EPIC-00](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/done/EPIC-00-contracts-and-scope.md)
- **Milestone 1**: Desktop vertical slice (HTML/CSS/JS + tests) ➔ [EPIC-01](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/done/EPIC-01-desktop-vertical-slice.md)
- **Milestone 2**: Quest 2 foundation & spatial surface ➔ [EPIC-02](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/needme/EPIC-02-quest2-unity-integration.md) + [NEEDME-02](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/needme/NEEDME-02-quest2-hardware-deployment.md)
- **Milestone 3**: Shared session service on Mac ➔ [EPIC-03](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/done/EPIC-03-shared-coordinator-service.md)
- **Milestone 4**: Garmin Venu 4 BLE heart rate (deferred/research) ➔ [EPIC-04](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/needme/EPIC-04-garmin-ble-integration.md) + [NEEDME-03](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/needme/NEEDME-03-garmin-watch-broadcast-test.md)
- **Milestone 5**: ElevenLabs voice guide live testing ➔ [EPIC-05](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/backlog/EPIC-05-elevenlabs-voice-integration.md) + [NEEDME-01](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/done/NEEDME-01-paid-api-approval.md)
- **Milestone 6 & 7**: fal.ai still & video cycles (≤30s) ➔ [EPIC-06](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/backlog/EPIC-06-fal-media-pipeline.md) + [NEEDME-01](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/done/NEEDME-01-paid-api-approval.md)
- **Milestone 8**: End-to-end therapist-guided session ➔ [EPIC-08](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/backlog/EPIC-08-end-to-end-session-flow.md)
