/* Rebase intentional local edits over new headset/voice events, without
   reviving a remotely stopped session or replacing server-owned media. */
(function (root) {
  const equal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  function workspace(base, local, remote) {
    const result = JSON.parse(JSON.stringify(remote));
    for (const [key, value] of Object.entries(local.notes))
      if (!equal(value, base.notes[key])) result.notes[key] = value;
    for (const edited of local.sessions) {
      const before = base.sessions.find((s) => s.id === edited.id),
        target = result.sessions.find((s) => s.id === edited.id);
      if (!target) {
        if (!before) result.sessions.push(edited);
        continue;
      }
      if (!before) throw new Error("Session conflict. Reload before saving.");
      for (const key of [
        "goal",
        "preNotes",
        "postNotes",
        "exclusions",
        "before",
        "after",
        "approved",
        "depth",
        "region",
        "remaining",
        "cycle",
        "pendingCycle",
        "status",
        "completedAt",
      ]) {
        if (equal(edited[key], before[key])) continue;
        if (
          target.status === "completed" &&
          [
            "status",
            "region",
            "depth",
            "remaining",
            "cycle",
            "pendingCycle",
          ].includes(key)
        )
          continue;
        if (
          target.driver === "unity" &&
          ["remaining", "cycle", "pendingCycle"].includes(key)
        )
          continue;
        if (
          !equal(target[key], before[key]) &&
          !equal(target[key], edited[key])
        )
          throw new Error(
            "Concurrent change to " + key + ". Reload before saving.",
          );
        target[key] = edited[key];
      }
      const known = new Set(before.events.map((e) => JSON.stringify(e))),
        existing = new Set(target.events.map((e) => JSON.stringify(e)));
      for (const event of edited.events)
        if (
          !known.has(JSON.stringify(event)) &&
          !existing.has(JSON.stringify(event))
        )
          target.events.push(event);
    }
    return result;
  }
  const api = { workspace };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.LandscapeMerge = api;
})(typeof window !== "undefined" ? window : globalThis);
