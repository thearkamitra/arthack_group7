/* The Mac coordinator owns BLE. Readings and the connection lease stay in memory. */
(function () {
  let sid = null, token = null, timer = null, pending = false, epoch = 0;
  let observation = { status: "disconnected" }, devices = [], message = "", busy = false;
  const notify = () => window.dispatchEvent(new CustomEvent("garminchange"));
  async function request(path, options = {}) {
    const response = await fetch(path, {
      credentials: "same-origin", signal: AbortSignal.timeout(15000), ...options,
      headers: { "Content-Type": "application/json", "X-Garmin-Token": token || "", ...options.headers },
    });
    const result = await response.json();
    if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Garmin request failed");
    return result;
  }
  const path = (id, suffix = "") => `/api/sessions/${encodeURIComponent(id)}/heart-rate${suffix}`;
  const api = {
    get state() { return { sid, observation, devices, message, busy }; },
    async scan() {
      if (busy || sid) return;
      busy = true; message = "Scanning nearby heart-rate devices (8 seconds)…"; devices = []; notify();
      try {
        devices = (await request("/api/garmin/scan", { method: "POST" })).devices;
        message = devices.length ? "Select your watch, confirm monitoring, then connect." : "No heart-rate device found. Start Broadcast Heart Rate and scan again.";
      } catch (error) { message = error.message; }
      finally { busy = false; notify(); }
    },
    async start(id, deviceId, consent) {
      if (busy || sid) return;
      if (!consent) throw new Error("Confirm local heart-rate monitoring first.");
      busy = true; const run = ++epoch; message = "Connecting to watch…"; notify();
      try {
        await window.LandscapeBackend.flush();
        const result = await request(path(id, "/start"), { method: "POST", body: JSON.stringify({device_id: deviceId, consent: true}) });
        if (run !== epoch) {
          await request(path(id, "/stop"), {method: "POST", headers: {"X-Garmin-Token": result.token}});
          return;
        }
        sid = id; token = result.token; observation = result.observation; message = "";
        timer = setInterval(poll, 1000);
        await poll();
      } catch (error) { if (run === epoch) message = error.message; }
      finally { busy = false; notify(); }
    },
    async stop() {
      ++epoch;
      const oldSid = sid, oldToken = token;
      clearInterval(timer); timer = null; sid = token = null;
      observation = {status: "disconnected"}; devices = []; message = "Disconnected. Active heart-rate data cleared."; notify();
      if (oldSid) {
        try { await request(path(oldSid, "/stop"), {method: "POST", keepalive: true, headers: {"X-Garmin-Token": oldToken}}); }
        catch { message = "Connection closed in this page. The coordinator clears it after at most 15 seconds without this page; stop watch broadcasting if needed."; notify(); }
      }
    },
    reconcile(session, visible) {
      if ((sid || busy) && (!session || session.status !== "active" || !visible)) api.stop();
    },
  };
  async function poll() {
    if (pending || !sid) return;
    pending = true; const id = sid, run = epoch;
    try {
      const next = await request(path(id));
      if (run !== epoch) return;
      observation = next;
      if (next.status === "disconnected") {
        await api.stop(); message = next.error || "Watch disconnected. Scan to reconnect.";
      }
      notify();
    } catch (error) {
      if (run === epoch) { await api.stop(); message = error.message + ". Monitoring stopped."; notify(); }
    } finally { pending = false; }
  }
  document.addEventListener("visibilitychange", () => { if (document.hidden) api.stop(); });
  window.addEventListener("pagehide", () => api.stop());
  window.LandscapeGarmin = api;
})();
