const test = require("node:test");
const assert = require("node:assert/strict");
const D = require("../demo-script.js");
test("every script step belongs to a section and has a line", () => {
  for (const step of D.steps) {
    assert.ok(D.sections[step.section]);
    assert.ok(["therapist", "patient"].includes(step.speaker));
    assert.ok(step.text.trim());
  }
  assert.equal(D.sections.at(-1).end, 240);
});
test("visual cues accumulate in script order", () => {
  assert.deepEqual(D.sceneAt(0), D.neutral);
  assert.equal(D.sceneAt(2).lake, 1);
  assert.equal(D.sceneAt(6).light, 1);
  assert.equal(D.sceneAt(10).pressure, "edge");
  assert.equal(D.sceneAt(11).pressure, "close");
  assert.equal(D.sceneAt(15).gap, 1);
  const end = D.sceneAt(D.steps.length - 1);
  assert.equal(end.pressure, "distant");
  assert.equal(end.path, 1);
  assert.equal(end.lake, 2);
});
test("declining the heaviness skips its exploration and keeps shapes away", () => {
  const choice = D.steps.findIndex((s) => s.choice);
  const next = D.nextIndex(choice, true);
  assert.equal(D.steps[next].section, 4);
  assert.equal(D.previousIndex(next, true), choice);
  for (let i = next; i < D.steps.length; i++) {
    assert.equal(D.sceneAt(i, true).pressure, "none");
    assert.equal(D.sceneAt(i, true).gap, 0);
  }
  assert.doesNotMatch(D.lineAt(D.steps.length - 2, true), /heavy shape/);
  assert.equal(D.nextIndex(choice, false), choice + 1);
});
test("stepping stops at the ends of the script", () => {
  assert.equal(D.nextIndex(D.steps.length - 1), -1);
  assert.equal(D.previousIndex(0), -1);
});
test("simulated Garmin summary is labelled and complete for the demo", () => {
  const G = require("../demo-garmin.js");
  assert.equal(G.synthetic, true);
  assert.equal(G.session_window.minutes, 4);
  const metrics = [
    G.session.stress,
    G.session.body_battery,
    G.session.respiration,
    G.session.activity.heart_rate,
    ...Object.values(G.session.fitness),
    ...Object.values(G.previous_night),
  ];
  for (const m of metrics) assert.equal(m.status, "available");
  assert.equal(G.session.activity.recordings.length, 1);
  assert.match(G.session.stress.note, /not an emotional state/);
});
