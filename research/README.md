# Collecting Garmin data for Inner Landscape

Researched: 24 October 2026. Assumption: your watch is the **Garmin Venu 4**, as named in the project plan. If it is another model, check its manual before following the broadcast instructions.

## Choose the route

**For heart rate during the art session, wear the watch and use Bluetooth heart-rate broadcast to the Mac.** USB is useful afterward for syncing saved recordings. You are right that taking the watch off to plug it in prevents useful wrist measurements during the session. Garmin documents USB as a sync/file-transfer route, not a live heart-rate feed.

| What you want | Route | What you need to do |
| --- | --- | --- |
| Live BPM during a session | Watch → Bluetooth LE → Mac receiver/logger | Follow A; receiver software still needs implementation/verification |
| A saved session with heart-rate samples | Record activity → Garmin Connect → original FIT export | Follow B; available without building an integration |
| Previous days of wellness data | Garmin Connect wellness/account export | Follow C |
| Sync saved activities without the phone | USB → Garmin Express → Garmin Connect | Follow D |
| Automated richer data later | Garmin Health API or mobile SDK | Follow E; approval and device-specific checks required |

A broadcast connection alone does not save a file. Garmin Connect phone pairing alone also does not deliver a live stream into this project. This document is a collection plan; no watch connection or recording has been tested here.

## A. Live heart rate while wearing the watch

### 1. Prepare the watch and Mac — you

- Charge the watch first, then unplug it and wear it snugly with the sensor against your skin.
- Confirm that a BPM value appears on the watch. In **Settings → Health & Wellness → Wrist Heart Rate**, ensure monitoring is enabled.
- Enable Bluetooth on the Mac. Keep the watch near the Mac for the first test.
- Note the watch model, firmware, macOS version and test start time. Use your own data for this initial check.

**Ready when:** the watch itself shows heart rate. If it does not, resolve this before testing the connection.

### 2. Enable broadcast — you

On the Venu 4, open **Settings → Health & Wellness → Wrist Heart Rate → Broadcast Heart Rate**, then press the watch button to start broadcasting. Follow the on-screen indication. Leave the watch on your wrist.

Garmin lists Venu 4 as supporting Bluetooth heart-rate broadcast; Bluetooth-capable Garmin broadcasts also transmit over ANT+. Broadcasting uses extra battery. [Garmin broadcast instructions](https://www8.garmin.com/manuals/webhelp/GUID-2CF5620C-E585-4E0A-9CC3-9565533EEE4D/EN-US/GUID-D8D363C2-0690-48D4-95E2-A3557E7D53C2.html), [Bluetooth model compatibility](https://support.garmin.com/en-US/?faq=Zj1947s6pqAHzBCAhLhrC9).

**Ready when:** the watch indicates broadcasting has started. This is separate from receiving data on the Mac.

### 3. Connect a receiver — research script available

A standalone receiver script is available at [garmin_ble_receiver.py](file:///Users/arkamitra/Documents/ChatGPT/arthack/research/garmin_ble_receiver.py). It connects to a Garmin watch broadcasting BLE Heart Rate, parses GATT characteristic `0x2A37`, displays live readings, and records session runs into ignored `runs/garmin/<run_id>/`.

**Run commands:**
```bash
# 1. Listen and connect to an actively broadcasting Garmin watch:
uv run --with bleak python research/garmin_ble_receiver.py

# 2. Or scan nearby BLE devices without connecting:
uv run --with bleak python research/garmin_ble_receiver.py --scan-only

# 3. Live terminal display only without writing to runs/:
uv run --with bleak python research/garmin_ble_receiver.py --no-save
```

**Developer requirements satisfied:** subscribes to Heart Rate service `0x180D`, measurement characteristic `0x2A37`; parses flags (8/16-bit BPM, contact flags, Energy Expended offset, R-R intervals); timestamps reception; handles disconnects; and outputs `heart-rate.csv`, `events.csv`, and `manifest.json`.

### 4. Run a short capture — you

1. Start saving in the receiver; write down the start time.
2. Sit comfortably for about two minutes, then continue a short reflection session for about three minutes. These durations are a practical test, not a validated assessment.
3. Note session start/end and any watch movement or poor contact.
4. Stop watch broadcasting briefly to test a dropout. The receiver should show missing/stale data, then allow reconnection.
5. Stop collection and explicitly save/export the recording before closing the receiver.

**Check:** open the export and confirm timestamps, multiple real BPM samples, session duration and a visible disconnect gap. Do not fill gaps with zero or treat repeated old values as fresh. Start with the project's proposed 10-second stale cutoff and validate it against actual notification timing. Mac timestamps are reception times, not guaranteed sensor acquisition times; do not promise fixed 1 Hz sampling or exact alignment with watch exports.

### 5. Save each run — you and the receiver

Use ignored `runs/garmin/<unique-run-id>/` under the repository (the existing `.gitignore` already ignores `runs/`). Keep research documents here, and personal measurements there.

The receiver should save `heart-rate.csv` (receipt time in UTC, elapsed time, BPM), `events.csv` (connect/disconnect and session markers), and `manifest.json` (model/firmware, receiver version, input/source, parameters, commands or UI actions, start/end, status, errors and output paths). Preserve original files and put derived results in separate files. Record RR intervals only if actually present; never manufacture them from BPM.

### If it does not connect

- **No BPM on watch:** check skin contact and wrist-heart-rate settings first.
- **BPM on watch, watch absent from scan:** confirm broadcasting actually started, keep it close, check Mac app permissions, and stop other apps that may already be connected to its HR broadcast. Retry before changing existing phone pairing.
- **Connected, no readings:** check notification subscription and Heart Rate service availability; record the failure rather than showing simulated values as live.
- **Intermittent values:** keep the Mac awake and the receiving app active during the test; inspect gaps and signal/contact conditions.
- **Bluetooth still fails:** validate model/firmware and receiver independently. ANT+ with a compatible USB receiver is an alternative requiring its own software support; a watch charging cable is not an ANT+ receiver. Do not buy hardware until the BLE test identifies a need.

## B. Collect a recorded session now, without a custom receiver

1. Wear the watch and confirm BPM appears.
2. Start a suitable timed activity on the watch, such as an available indoor/Other activity. Avoid GPS for a seated test if it is unnecessary. Note the chosen activity type.
3. Record a short session, then stop and **save** it on the watch.
4. Open Garmin Connect on your paired phone and sync. Alternatively use USB/Express after recording (D).
5. On the Mac, sign in to [Garmin Connect](https://connect.garmin.com/). Open **Activities → All Activities**, select the recording, then the settings gear → **Export Original**.
6. Keep the downloaded archive and original FIT file in a unique ignored run folder. Record activity start/end, local timezone and export actions in a manifest.
7. Check the activity's heart-rate graph in Connect. Before using the exported data, decode FIT locally with a suitable tool and confirm that timestamped heart-rate records really exist. Export success alone does not prove this.

FIT is a structured binary recording, not a spreadsheet. The activities-list CSV is a summary and is not a replacement for sample-level heart rate. An original export normally preserves more of the device's recorded fields. [Garmin export instructions](https://support.garmin.com/en-US/?faq=W1TvTPW8JZ6LfJSfK512Q8).

**Result:** retrospective data; it will not drive the artwork live. Record-on-watch and live broadcast may be useful together, but verify their simultaneous behavior on your watch before relying on both.

## C. Collect previous wellness data

1. Sync the watch to Garmin Connect first.
2. In Connect web, open your profile → **Account Settings → Account Information**; select a day in the wellness-export section and export it.
3. Preserve the downloaded ZIP/FIT files in an ignored run folder; note the requested date and timezone.
4. For a broader archive, use Garmin Account Data Management → **Export Your Data → Request Data Export**. Download the archive when Garmin sends the link; delivery is asynchronous.
5. Inspect the actual files and fields before planning analysis. Wellness availability and sampling are different from a timed activity and from a live broadcast.

Garmin documents daily wellness exports and full account exports in its [export guide](https://support.garmin.com/en-US/?faq=W1TvTPW8JZ6LfJSfK512Q8). Whole-account archives can contain location and other personal information; keep them out of Git and public frontend folders.

## D. Use USB for recordings you already saved

1. Finish and save the activity while the watch is still on your wrist.
2. Connect it to the Mac with a data-capable Garmin cable.
3. Install/open [Garmin Express](https://www.garmin.com/express/), choose **Add Device**, and follow its account/sync prompts.
4. Confirm the activity appears in Garmin Connect, then export it using B.

The [Venu 4 manual](https://www8.garmin.com/manuals/webhelp/GUID-2CF5620C-E585-4E0A-9CC3-9565533EEE4D/EN-US/Venu_4_OM_EN-US.pdf) documents this upload workflow. A watch missing from Finder does not necessarily mean a bad cable: MTP/music devices may not appear as normal Mac drives. Prefer Express plus Connect export over depending on Finder access. [Garmin Mac file-access guidance](https://support.garmin.com/en-US/?faq=4NnyLlu0o5ASH4BVZ6QWPA).

## E. Richer or automated integration later

| Option | Your next action | Limits |
| --- | --- | --- |
| Health API | Apply through Garmin's developer program, describe the intended data and consent flow, confirm current access terms | Data becomes available after upload to Connect; not the direct live BPM route |
| Companion SDK | Request an evaluation from Garmin Health and explicitly ask about Venu 4 and the desired metrics | Android/iOS integration; requires a mobile app and Garmin access, not a drop-in Mac library |
| Standard SDK | Discuss only if the project needs control of the wearable and a different account/data flow | Larger scope; not the initial recommendation |

Confirm approval, current pricing/terms, exact model/firmware support and metric availability with Garmin before implementation. [Health API](https://developer.garmin.com/gc-developer-program/health-api/), [Health SDKs](https://developer.garmin.com/health-sdk/).

Ordinary HR broadcast does not imply access to raw optical waveforms, ECG, HRV, stress, sleep, respiration or Body Battery. Garmin SDK capabilities do not establish that every metric works on this particular watch. Heart rate alone does not identify emotion, attention or clinical improvement.

## What to do first

1. Confirm your watch is a Venu 4 and enable heart-rate broadcast while wearing it.
2. For a file today, record and export a short activity using B.
3. For live data in Inner Landscape, the next implementation milestone is the minimal Mac BLE receiver/logger in A3, followed by the actual watch test in A4. Artwork integration should follow that verified capture.

Research checked official Garmin, Chrome and Bluetooth documentation. No hardware pairing, sensor capture, FIT decoding, API approval or SDK evaluation was performed for this guide.
