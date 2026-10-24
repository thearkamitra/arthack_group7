# Garmin in the session workspace

The coordinator now uses the Bleak approach from `research/garmin_ble_receiver.py`.
Both paths share the GATT parser in `backend/inner_landscape/garmin_protocol.py`.
The standalone research CLI remains available and keeps its original file logging;
the integrated session connection is ephemeral and does not record files.

## Use it

1. Run `bash backend/scripts/setup.sh` to install the pinned Mac dependencies,
   including Bleak 3.0.2. Stop any standalone Garmin receiver so it releases the watch.
2. Start or restart the coordinator with `bash backend/scripts/run.sh` and open
   http://127.0.0.1:4173. A static preview server cannot receive Garmin data.
3. Wear the Venu 4. On the watch start Settings → Health & Wellness → Wrist Heart
   Rate → Broadcast Heart Rate. Keep it close to the Mac.
4. Open an active session (resume if paused). In **Garmin heart rate**, click
   **Scan for watch**. The scan lasts eight seconds. If macOS asks, allow Bluetooth
   for the terminal/Python process running the coordinator. Select your watch in
   the returned list; other nearby HR devices may also appear.
5. Confirm session-only monitoring and click **Connect watch**. Connection is
   asynchronous; “connecting” does not mean BPM has been received. Confirm a
   fresh numeric reading appears and broadly matches the watch display.
6. Sit comfortably for the baseline. The panel requires at least 30 seconds and
   15 accepted samples. Samples with reported poor contact or malformed payloads
   are ignored. Accepted integer BPM range is 25–240 (input guard, not a medical
   definition of normal). Processing is limited to about one sample per second.
7. Continue the reflection. A sustained rise shows a practitioner check-in cue.
   It does not choose imagery, infer emotion or automatically pause the session.
8. Click **Disconnect & clear**, pause, or finish. Resume requires a new explicit
   connection and baseline. Stop broadcasting on the watch too if you are done;
   disconnecting on the Mac cannot turn off the watch's broadcast setting.

## What “spike” means here

These are prototype engineering defaults, not validated medical thresholds:

- Baseline: median of the initial accepted samples over at least 30 seconds.
- Rise: BPM is at least baseline + max(20 BPM, 25% of baseline).
- Sustain: above the threshold for five seconds and at least three samples.
- Recovery: at least five BPM below the rise threshold for five seconds.
- Freshness: ten seconds without a valid sample removes the current BPM,
  baseline and cue. A returning signal starts a new baseline.
- No valid samples for 30 seconds ends the monitoring lease and BLE connection.

The backend owns this detector. It uses monotonic receipt times, not claimed
sensor acquisition times. Pulse alone cannot establish emotion, attention,
clinical improvement or why the reading changed. The practitioner can offer a
pause and ask the participant what they need.

## Lifecycle, data and access

The browser calls same-origin authenticated coordinator routes; it needs no Web
Bluetooth support or Garmin credentials. Scan results expose names and temporary
selection IDs, not device addresses. Scan selections expire after 60 seconds.
Only the local practitioner can scan/connect/view heart-rate observations.
A connection lease prevents another tab from sending a stop for an active owner.

Live BPM, baseline, watch selection and connection token stay in process/tab
memory. They are absent from SQLite session state, browser local storage,
transcripts, review history, logs, provider context and frontend workspace saves.
Existing research recordings under ignored `runs/garmin/` are preserved.

Pause, completion, navigation away, hiding/closing the receiving tab, explicit
disconnect and coordinator shutdown release monitoring. If the page disappears
without a successful stop request, the backend releases BLE after 15 seconds
without the owner polling (plus up to five seconds for bounded disconnect).
A signal gap ends the connection after 30 seconds. No automatic reconnection is
attempted. On disconnect failure the panel explains that the watch broadcast
should be stopped manually. No code can guarantee physical disconnection after
an OS-level Bluetooth failure or force the watch to stop broadcasting remotely.

## API and verification

- `POST /api/garmin/scan`: bounded scan; returns candidate names and opaque IDs.
- `POST /api/sessions/{id}/heart-rate/start`: `{device_id, consent: true}`;
  returns the memory-only lease token. Session must be active.
- `GET /api/sessions/{id}/heart-rate`: fresh observation; the owning page supplies
  `X-Garmin-Token` to renew its page-presence heartbeat.
- `POST /api/sessions/{id}/heart-rate/stop`: owner token; disconnect and clear.

Normal tests use an injected fake BLE scanner/client; they never activate radios,
download models, call providers or require a watch:

```sh
PYTHONPATH=backend backend/.venv/bin/python -m unittest discover -s backend/tests
node --test frontend/tests/*.test.cjs
node --check frontend/garmin.js
```

The real-device acceptance test is steps 3–8 plus stopping broadcast briefly to
verify stale display and baseline reset. User reports the standalone receiver
works; the integrated implementation has been checked using fake BLE in API and
browser tests, not with an actual watch. No paid service test was run.

## Small broadcast smoke test

With the watch worn and Broadcast Heart Rate enabled, close any other receiver
and disconnect monitoring in the frontend. From the repository root:

```sh
PYTHONPATH=backend backend/.venv/bin/python -m inner_landscape.garmin_check --name venu --seconds 15
```

The test scans for eight seconds, connects to one uniquely matching name, and
waits up to 15 seconds for a valid Heart Rate Measurement notification. Use
`--name garmin` if that matches your advertisement instead. It prints JSON and
returns 0 only after a valid notification; discovering an advertisement alone
never passes. It always disconnects and clears readings. Nothing is recorded.
The scan/connect/cleanup steps have separate bounded timeouts.

In the therapist console, scan, select, consent and connect. The status distinguishes
**Connected · waiting for broadcast** from **Broadcast verified** after a fresh
notification. A stale or disconnected stream clears BPM instead of showing zero.

Offline tests exercise valid notifications, malformed/no-contact packets, missing
notifications, API consent/authorization, stale readings, pause/finish cleanup and
frontend lifecycle. A live scan on 2026-10-24 completed with **zero matching Venu
advertisements**. Physical broadcasting is not yet verified.

Latest hardware retest (2026-10-24): after broadcasting was enabled, the integrated smoke test received a valid live heart-rate notification and returned `passed: true`. Basic broadcast reception is verified. The longer recording and physical interruption trials remain pending.
