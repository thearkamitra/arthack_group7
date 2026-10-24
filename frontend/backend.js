/* Optional same-origin coordinator. Static/file previews remain fully local. */
(function () {
  let revision = 0,
    status = null,
    connected = false,
    pending = 0;
  let queue = Promise.resolve(),
    onSnapshot = () => {},
    onStatus = () => {};
  let lastLocal = null;
  let authenticationRefresh = null;
  async function refreshAuthentication() {
    if (!["127.0.0.1", "localhost", "[::1]"].includes(location.hostname)) return false;
    if (!authenticationRefresh)
      authenticationRefresh = fetch("/", {credentials: "same-origin", cache: "no-store"})
        .then(response => response.ok).catch(() => false)
        .finally(() => { authenticationRefresh = null; });
    return authenticationRefresh;
  }
  function connectionMessage(error) {
    if (error.status === 401)
      return "Workspace authentication expired. Reload this page on the Mac to sign in again; keep any unsaved drafts.";
    if (error.status)
      return `Coordinator returned HTTP ${error.status}. Your drafts are retained; check the Mac server.`;
    return "Coordinator connection failed. Check the Mac server or network; your drafts are retained.";
  }
  async function request(path, options = {}, allowAuthenticationRefresh = true) {
    const response = await fetch(path, {
      credentials: "same-origin",
      ...options,
      headers: { "Content-Type": "application/json", ...options.headers },
    });
    if (response.status === 401 && allowAuthenticationRefresh &&
        (options.method || "GET").toUpperCase() === "GET" &&
        ["/api/status", "/api/workspace"].includes(path) && await refreshAuthentication())
      return request(path, options, false);
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(response.status === 401
        ? "Workspace authentication expired. Reload this page on the Mac; this action was not retried."
        : typeof body.detail === "string" ? body.detail : "The coordinator could not complete this request.");
      error.status = response.status;
      throw error;
    }
    return body;
  }
  const api = {
    get connected() {
      return connected;
    },
    get status() {
      return status;
    },
    async start(workspace, callback, change) {
      onSnapshot = callback;
      onStatus = change;
      if (!["http:", "https:"].includes(location.protocol)) return;
      try {
        status = await request("/api/status");
        if (status.service !== "inner-landscape") return;
        const snapshot = await request("/api/workspace");
        revision = snapshot.revision;
        connected = true;
        lastLocal = JSON.parse(JSON.stringify(snapshot.workspace));
        if (
          !snapshot.workspace.sessions.length &&
          !Object.keys(snapshot.workspace.notes).length &&
          (workspace.sessions.length || Object.keys(workspace.notes).length)
        ) {
          await api.save(workspace);
        } else onSnapshot(snapshot.workspace);
        onStatus("Shared workspace connected");
        setInterval(async () => {
          if (pending || document.hidden) return;
          try {
            const next = await request("/api/workspace");
            if (next.revision !== revision) {
              revision = next.revision;
              lastLocal = JSON.parse(JSON.stringify(next.workspace));
              onSnapshot(next.workspace);
            }
          } catch (error) {
            onStatus(connectionMessage(error));
          }
        }, 1500);
      } catch (error) {
        status = null;
        connected = false;
        onStatus(connectionMessage(error));
      }
    },
    save(workspace) {
      if (!connected) return Promise.resolve();
      const snapshot = JSON.parse(JSON.stringify(workspace));
      const base = lastLocal || snapshot;
      lastLocal = snapshot;
      pending++;
      queue = queue.then(async () => {
        try {
          let result,
            rebased = false;
          try {
            result = await request("/api/workspace", {
              method: "PUT",
              body: JSON.stringify({ revision, workspace: snapshot }),
            });
          } catch (error) {
            if (!error.message.includes("Workspace changed")) throw error;
            rebased = true;
            const remote = await request("/api/workspace");
            const merged = window.LandscapeMerge.workspace(
              base,
              snapshot,
              remote.workspace,
            );
            result = await request("/api/workspace", {
              method: "PUT",
              body: JSON.stringify({
                revision: remote.revision,
                workspace: merged,
              }),
            });
          }
          revision = result.revision;
          if (pending === 1) {
            lastLocal = JSON.parse(JSON.stringify(result.workspace));
            if (rebased) onSnapshot(result.workspace);
          }
        } catch (error) {
          onStatus(error.message);
          // Do not overwrite another client's state or silently discard local data.
          connected = false;
          throw error;
        } finally {
          pending--;
        }
      });
      queue.catch(() => {});
      return queue;
    },
    async scene(id, image) {
      await queue;
      await request(`/api/sessions/${id}/scene`, {
        method: "POST",
        body: JSON.stringify({ image }),
      });
      const snap = await request("/api/workspace");
      revision = snap.revision;
      onSnapshot(snap.workspace);
    },
    async pair(id) {
      await queue;
      return request(`/api/sessions/${id}/pair`, { method: "POST" });
    },
    async jobs(id) {
      return request(`/api/sessions/${id}/media`);
    },
    async generate(id, body) {
      await queue;
      return request(`/api/sessions/${id}/media`, {
        method: "POST",
        body: JSON.stringify(body),
      });
    },
    async canonical(id) {
      await queue;
      await request(`/api/sessions/${id}/canonical-scene`, {method: "POST"});
      const snapshot = await request("/api/workspace"); revision = snapshot.revision; onSnapshot(snapshot.workspace);
    },
    async entry(id, excerpt, parent_job = null) {
      await this.flush();
      return request(`/api/sessions/${id}/region-entry`, {method: "POST", body: JSON.stringify({excerpt, parent_job})});
    },
    async apply(id, jobId) {
      await queue;
      await request(`/api/sessions/${id}/media/apply`, {
        method: "POST",
        body: JSON.stringify({ job_id: jobId, continuity_confirmed: true }),
      });
      const snapshot = await request("/api/workspace");
      revision = snapshot.revision;
      onSnapshot(snapshot.workspace);
    },
    async command(id, name, payload = {}) {
      await queue;
      const result = await request(`/api/sessions/${id}/commands`, {
        method: "POST",
        body: JSON.stringify({
          command_id: crypto.randomUUID(),
          command: name,
          payload,
        }),
      });
      const snap = await request("/api/workspace");
      revision = snap.revision;
      lastLocal = JSON.parse(JSON.stringify(snap.workspace));
      onSnapshot(snap.workspace);
      return result;
    },
    async flush() {
      await queue;
    },
  };
  window.LandscapeBackend = api;
})();
