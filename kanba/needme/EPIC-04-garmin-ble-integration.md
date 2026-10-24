# EPIC-04: Garmin Venu 4 Live BLE Heart-Rate Receiver & Pacing Integration

- **ID**: `EPIC-04`
- **Milestone Reference**: Milestone 4 (Garmin - deferred / research workstream)
- **Status**: Blocked
- **Primary Owner**: Systems / Hardware Engineer
- **Relevant Files**:
  - [research/garmin_ble_receiver.py](file:///Users/arkamitra/Documents/ChatGPT/arthack/research/garmin_ble_receiver.py)
  - [research/README.md](file:///Users/arkamitra/Documents/ChatGPT/arthack/research/README.md)
  - [backend/inner_landscape/garmin.py](file:///Users/arkamitra/Documents/ChatGPT/arthack/backend/inner_landscape/garmin.py)

---

## 1. Objective & Scope

Establish a Bluetooth Low Energy (BLE) connection from the Mac to a worn Garmin Venu 4 watch actively broadcasting heart rate. Parse standard GATT Heart Rate Service `0x180D` and Measurement Characteristic `0x2A37`. Display real-time BPM and freshness status, handle disconnects with bounded retries, and optionally bridge observations to the Mac coordinator.

### Critical Constraints
- **Pacing & Readiness ONLY, NO Emotion or Diagnostic Inference**: Heart rate participates solely in pacing and neutral check-in prompts (e.g. noticing sustained changes to offer a breath or pause). **Never infer anxiety, emotional valence, truthfulness, stress scores, or clinical diagnoses from pulse.**
- **Missing Sensor Must Not Block Session**: Missing watch or signal loss must never prevent an art session. Disconnections must be shown as gaps on the timeline, never as zero BPM or synthetic defaults.
- **Hardware Broadcast Requirement**: The watch must be worn snugly against the wrist with *Broadcast Heart Rate* turned on. USB connection is strictly for post-session file transfer and cannot deliver live wrist heart rate.

---

## 2. Current Implementation State

- **Receiver Script**: [research/garmin_ble_receiver.py](file:///Users/arkamitra/Documents/ChatGPT/arthack/research/garmin_ble_receiver.py) implemented with Bleak:
  - Subscribes to UUID `00002a37-0000-1000-8000-00805f9b34fb`.
  - Parses 8-bit / 16-bit BPM formats, sensor contact flags, Energy Expended offsets, and R-R interval millisecond arrays.
  - Automatically handles disconnect callbacks.
  - Records session artifacts to `runs/garmin/{run_id}/` (`heart-rate.csv`, `events.csv`, `manifest.json`).
- **Research Guide**: Complete operational procedure documented in [research/README.md](file:///Users/arkamitra/Documents/ChatGPT/arthack/research/README.md).
- **Pending**: Physical hardware broadcast test with a live watch on macOS CoreBluetooth, and optional integration into coordinator API.

---

## 3. Tasks & Stories

- [ ] **Task 4.1 — Physical Watch Broadcast Verification**:
  - Wear charged Venu 4, confirm wrist HR display.
  - Enable **Settings → Health & Wellness → Wrist Heart Rate → Broadcast Heart Rate**.
  - Execute BLE scan: `uv run --with bleak python research/garmin_ble_receiver.py --scan-only`.
  - Verify watch advertisement is discovered by macOS CoreBluetooth.
- [ ] **Task 4.2 — Live Measurement Stream & CSV Logging**:
  - Run live receiver: `uv run --with bleak python research/garmin_ble_receiver.py`.
  - Verify terminal display updates at ~1 Hz with BPM, contact status, and R-R intervals.
  - Complete 2-minute seated baseline run and verify output in `runs/garmin/run_YYYYMMDD_HHMMSS/`.
- [ ] **Task 4.3 — Disconnection & Freshness Handling**:
  - Test moving out of range or disabling broadcast: verify disconnect is logged, terminal reports stale data after 10s cutoff, and reconnect succeeds upon return.
- [ ] **Task 4.4 — Coordinator Ingestion Bridge (Optional Integration)**:
  - Add an HTTP/WebSocket client in the receiver script or background task to POST `HeartRateObservation` events to the Mac coordinator:
    `POST /api/v1/sessions/{session_id}/heart-rate`.
  - Verify therapist live console displays current BPM and fresh indicator.
  - Verify timeline renders data loss as visual gaps without crashing.

---

## 4. Acceptance Criteria

1. BLE connection connects to Venu 4 in < 10 seconds from broadcast initiation.
2. GATT Characteristic `0x2A37` notifications parse correctly with valid BPM values (40–200 BPM).
3. Generated `heart-rate.csv` and `manifest.json` have valid timestamps and sample counts.
4. Signal interruption marks freshness as stale after 10 seconds; reconnection resumes automatically.
5. Zero emotional or clinical labels attached to heart-rate telemetry.

## Current pickup
Owner: Codex. Scope: wire the merged Unity project and verify integrated Garmin broadcast reception; physical acceptance stays pending.

## 2026-10-24 integration evidence and remaining gate

The former optional ingestion story is now implemented directly by
`backend/inner_landscape/garmin_ble.py`, `garmin.py` and `/api/garmin/scan` plus
`/api/sessions/{id}/heart-rate` start/read/stop routes. No `/api/v1` ingestion
endpoint is required. `frontend/garmin.js` and the therapist session panel provide
scan, consent, connect, live BPM/freshness, baseline/check-in cue, and cleanup.
Live values remain in memory; source CSV recording belongs to the separate research CLI.

Added `python -m inner_landscape.garmin_check`: bounded hardware discovery and
notification check, unconditional disconnect, exit 0 only after a valid measurement.
Frontend now distinguishes waiting-for-broadcast from verified fresh reception.

Verification: 27 backend tests and 14 frontend tests passed, including valid
notifications, malformed/no-contact packets, no-notification failure, and cleanup.
A real CoreBluetooth scan outside the sandbox completed with zero matching Venu
advertisements. **This is not a live broadcast pass.**

Required action: wear the Venu, enable Broadcast Heart Rate, allow macOS Bluetooth
access, and run the small check or connect from the therapist panel. Remaining
physical baseline, interruption/reconnect and timing acceptance is unverified.
The integrated receiver currently uses explicit reconnect after disconnection.
