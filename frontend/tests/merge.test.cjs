const test = require("node:test"),
  assert = require("node:assert/strict");
const { workspace } = require("../merge.js");
function sample() {
  return {
    version: 1,
    notes: {},
    sessions: [
      {
        id: "a",
        status: "active",
        cycle: 1,
        remaining: 30,
        region: "ridge",
        depth: { sky: 0, ridge: 0, water: 0 },
        preNotes: "",
        events: [],
      },
    ],
  };
}
test("rebase retains headset attention and new provider events while saving therapist notes", () => {
  const base = sample(),
    local = structuredClone(base),
    remote = structuredClone(base);
  local.sessions[0].preNotes = "New note";
  remote.sessions[0].attention = { sky: 2 };
  remote.sessions[0].events.push({ type: "guide", text: "Hello" });
  const result = workspace(base, local, remote);
  assert.equal(result.sessions[0].preNotes, "New note");
  assert.deepEqual(result.sessions[0].attention, { sky: 2 });
  assert.equal(result.sessions[0].events.length, 1);
});
test("rebase never revives a remotely completed session", () => {
  const base = sample(),
    local = structuredClone(base),
    remote = structuredClone(base);
  local.sessions[0].remaining = 29;
  remote.sessions[0].status = "completed";
  assert.equal(workspace(base, local, remote).sessions[0].status, "completed");
  assert.equal(workspace(base, local, remote).sessions[0].remaining, 30);
});
test("conflicting same-field changes are explicit, not last-write-wins", () => {
  const base = sample(),
    local = structuredClone(base),
    remote = structuredClone(base);
  local.sessions[0].preNotes = "One";
  remote.sessions[0].preNotes = "Another";
  assert.throws(() => workspace(base, local, remote));
});
