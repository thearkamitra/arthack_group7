# Inner Landscape

An immersive reflection experience: an AI guide starts a conversation while an
abstract landscape gradually becomes defined through words and selected regions.
Active development is on `master`. The first target is a large 2D image on a Mac;
Meta Quest 2/3 support comes later, using head direction rather than eye tracking.

## Run the interaction sketch

Open `frontend/index.html` in a browser (double-click it in Finder). No server,
installation, API keys or Python dependencies are needed.

Choose a local PNG, JPEG or WebP landscape, select left/centre/right, and write a
reflection. Three scripted turns progressively sharpen the whole image. Reset
starts a fresh preview. Nothing is uploaded or persisted. Original files are
unchanged. This is an interaction sketch, not an AI or image-generation demo.

## Next implementation steps

1. Connect ElevenLabs for the guide's opening question and voice conversation.
2. Add a Python backend under `backend/` for API credentials and generation jobs.
   Record inputs, parameters, commands, status and outputs in per-run manifests.
3. Use fal.ai image editing to refine selected regions while retaining continuity.
   Transition between completed images; keep the current image if generation fails.
4. Test Venu 4 Bluetooth heart-rate reception on the Mac, then map readings to
   subtle visual rhythm. Do not infer emotions from heart rate. Richer Garmin
   metrics are a separate integration, not part of the basic heart-rate broadcast.
5. Move the large artwork into Quest VR once the desktop interaction works.

Voice, generation, heart rate, region-specific edits and VR are not connected yet.
The current sharpening effect does not use the meaning of typed reflections.

## Repository layout

- `frontend/`: framework-free desktop interaction sketch.
- `backend/`: future Python application, dependencies, setup and tests.
- `assets/`: preserved source inputs from the earlier experiment.
- `outputs/`, `runs/`, `work/`: ignored deliverables, generated runs and scratch data.
- `external/Auto-MIA`: retained pinned submodule; unused by this prototype.

The old Borrowed Eyes application is available in Git history at `8bfaa19`.
The existing root `.venv` is preserved; do not reinstall the retired mesh stack.
See `AGENTS.md` for project conventions. Never put API credentials in frontend code.
