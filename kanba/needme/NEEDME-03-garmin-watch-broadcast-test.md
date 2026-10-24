# NEEDME-03: Garmin Watch Broadcast Hardware Trial

- **ID**: `NEEDME-03`
- **Blocks**: [EPIC-04: Garmin BLE Receiver](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/backlog/EPIC-04-garmin-ble-integration.md)
- **Status**: Waiting on User / Watch Hardware
- **Action Required From**: User with physical Garmin Venu 4

---

## What is Needed from You

A complete BLE receiver script has been built at [research/garmin_ble_receiver.py](file:///Users/arkamitra/Documents/ChatGPT/arthack/research/garmin_ble_receiver.py). To verify that your Mac can discover and receive heart-rate notifications from the Garmin Venu 4, a physical broadcast test is required.

### Action Steps
1. **Wear & Start Broadcast**:
   - Wear your charged Garmin Venu 4 watch snugly on your wrist.
   - On the watch, navigate to: **Settings → Health & Wellness → Wrist Heart Rate → Broadcast Heart Rate**.
   - Press the watch button to start broadcasting.
2. **Scan on Mac**:
   - In terminal on the Mac, run:
     ```bash
     uv run --with bleak python research/garmin_ble_receiver.py --scan-only
     ```
   - Confirm your watch appears in the discovered BLE device list.
3. **Stream & Record 2-Minute Test**:
   - Run the receiver:
     ```bash
     uv run --with bleak python research/garmin_ble_receiver.py
     ```
   - Sit comfortably for 2 minutes while observing live readings on the terminal.
   - Press `Ctrl+C` to end. Check that `runs/garmin/run_YYYYMMDD_HHMMSS/` contains `heart-rate.csv` and `manifest.json`.
4. **Report Results**:
   - Confirm connection speed and signal reliability.
   - Once verified, move this card to `kanba/done/`.
