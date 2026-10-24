# EPIC-06: fal.ai Generative Media Studio & Visual Continuity Review

- **ID**: `EPIC-06`
- **Milestone Reference**: Milestone 6 (Still generation) & Milestone 7 (Video cycle)
- **Status**: Blocked on Paid API Approval Gate ([NEEDME-01](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/needme/NEEDME-01-paid-api-approval.md))
- **Primary Owner**: Backend / Media Engineer
- **Relevant Files**:
  - [backend/inner_landscape/media.py](file:///Users/arkamitra/Documents/ChatGPT/arthack/backend/inner_landscape/media.py)
  - [backend/inner_landscape/api.py](file:///Users/arkamitra/Documents/ChatGPT/arthack/backend/inner_landscape/api.py)
  - [frontend/app.js](file:///Users/arkamitra/Documents/ChatGPT/arthack/frontend/app.js)
  - [docs/BACKEND.md](file:///Users/arkamitra/Documents/ChatGPT/arthack/docs/BACKEND.md#L67-L97)

---

## 1. Objective & Scope

Integrate the asynchronous fal.ai generative media pipeline into the reflection cycle. When a region is confirmed and a visual brief is submitted, generate an in-painted still refinement (`fal-ai/flux-kontext/dev`), followed by an animated 5-second silent video clip (`fal-ai/kling-video/v2.5-turbo/standard/image-to-video`). Ensure strict validation of duration (≤30 seconds), dimensions, and continuity, with full therapist review before applying new media.

### Critical Constraints
- **Strict Media Window**: Exploration cycles play clips of ≤30 seconds. Kling video generates 5-second clips; the last frame holds stable for the remaining exploration. Do not generate multi-minute videos.
- **Explicit Cost Bounding**: Limit to maximum 4 generation jobs per session. Enforce maximum one in-flight generation job at any time.
- **No Automatic Billable Retries**: On timeout or ambiguous status, never automatically re-submit a billable request. Reconcile provider status manually or fallback to prior still image.
- **Therapist Review Gate**: Generated media is presented as a preview. It is only applied to the live session after the therapist clicks **Confirm continuity & use**.
- **Privacy Minimization**: Only the cropped scene image and visual brief are sent to fal.ai. Never send client identifiers, notes, or transcripts.

---

## 2. Current Implementation State

- **Provider Adapters**: [backend/inner_landscape/media.py](file:///Users/arkamitra/Documents/ChatGPT/arthack/backend/inner_landscape/media.py) implements:
  - `generate_image_edit()`: Sends vertical region crop to `fal-ai/flux-kontext/dev` and composites the edited crop back into the full composition, preserving surrounding pixels. Validated with Pillow.
  - `generate_video_clip()`: Submits 5s image-to-video job to `fal-ai/kling-video/v2.5-turbo/standard/image-to-video`. Validates resulting MP4 duration and dimensions with `ffprobe`.
- **Manifest Logging**: Generates per-job manifests with input/output hashes, parameters, prompt versions, and artifact paths in `work/media_jobs/`.
- **Pending**: Live API execution with credentials, latency benchmarking, and visual continuity evaluation across sequential cycles.

---

## 3. Tasks & Stories

- [ ] **Task 6.1 — Prerequisites & Cost Approval**:
  - Verify `ffmpeg` / `ffprobe` installed on Mac host (`which ffprobe`).
  - Verify `FAL_KEY` in `.env` or process environment.
  - Obtain user sign-off for paid media generation ([NEEDME-01](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/needme/NEEDME-01-paid-api-approval.md)).
  - Launch coordinator with `bash backend/scripts/run.sh --enable-paid`.
- [ ] **Task 6.2 — Still Inpainting Validation (`flux-kontext`)**:
  - Trigger image refinement from therapist console with a test brief (e.g., *"Sunlight filtering through morning mist"*).
  - Verify successful asynchronous polling and download of PNG artifact.
  - Verify composite image: region crop is updated while adjacent regions remain identical.
  - Verify job manifest generated in `work/media_jobs/{job_id}/manifest.json`.
- [ ] **Task 6.3 — Video Clip Generation & Probe Validation (`kling-video`)**:
  - Submit image-to-video job from refined still.
  - Verify downloaded MP4 artifact with `ffprobe`: duration = 5.0s (strictly ≤ 30.0s), valid codec and dimensions.
  - Verify video plays smoothly and holds on final frame.
- [ ] **Task 6.4 — Failure & Timeout Fallback**:
  - Test simulated provider error / timeout: verify coordinator logs error, retains prior scene unchanged, and returns graceful error to therapist console.
  - Verify that a failed job does NOT block the session or trigger duplicate billing.
- [ ] **Task 6.5 — Therapist Review Workflow**:
  - Verify generated preview appears in Therapist Media Studio.
  - Verify clicking **Confirm continuity & use** updates active session media for both console and connected Quest headset.

---

## 4. Acceptance Criteria

1. Still image inpainting completes and decodes with valid dimensions matching canonical resolution.
2. Video clip duration verified via `ffprobe` as ≤ 30 seconds.
3. Media manifests record request IDs, input/output SHA256 hashes, and timestamps.
4. Total generation cost stays within session budget limits (max 4 jobs / session).
5. Paused or completed sessions reject incoming media applications.
