# NEEDME-02: Quest 2 Physical Build & LAN Connection Test

- **ID**: `NEEDME-02`
- **Blocks**: [EPIC-02: Quest 2 Hardware Integration](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/needme/EPIC-02-quest2-unity-integration.md)
- **Status**: Waiting on Teammate / Hardware Test
- **Action Required From**: VR Teammate with physical Meta Quest 2

---

## What is Needed from You

The Unity integration scripts and curved display assets are prepared under [Assets/InnerLandscape/](file:///Users/arkamitra/Documents/ChatGPT/arthack/Assets/InnerLandscape/). Because this Mac does not have a physical Quest 2 attached, an in-headset test is required to validate rendering comfort, head-directed raycast tracking, and LAN networking.

### Action Steps
1. **Open Unity**:
   - Open a Unity 6000.6.7f1 project with OpenXR and Android Build Support.
   - Open the repository root; its `Assets/InnerLandscape/` is already in the active project.
2. **Follow Handoff Guide**:
   - Follow the step-by-step setup in [docs/UNITY_HANDOFF.md](file:///Users/arkamitra/Documents/ChatGPT/arthack/docs/UNITY_HANDOFF.md).
3. **Start Mac Coordinator for LAN**:
   - On the Mac: `bash backend/scripts/run.sh --host 0.0.0.0 --demo-lan`.
   - Open therapist console at `http://127.0.0.1:4173` and click **Pair Unity headset** to generate an 8-character pairing code.
4. **Deploy & Pair**:
   - Build and run the APK onto the Quest 2.
   - Enter the Mac LAN IP and pairing code in the headset UI.
   - Check that head turns highlight `sky`, `ridge`, and `water` after 1.5 seconds.
5. **Report Results**:
   - Note down frame rate (fps), comfort distance, and whether any front-face culling issues occur.
   - Once verified, move this card to `kanba/done/`.

Local build prerequisite: Unity license initialization timed out and Android Build Support is missing. Activate/install these or use the teammate's configured editor. No APK exists yet.
