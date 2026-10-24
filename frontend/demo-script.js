/* Scripted four-minute walkthrough: example dialogue and visual cues only.
   No AI, microphone or provider is involved; patient lines are fictional examples. */
(function (root) {
  "use strict";
  const sections = [
    {
      title: "Arriving in the space",
      start: 0,
      end: 35,
      cue: "The blue region slowly expands into a reflective lake. Soft ripples appear; the surrounding shapes stay indistinct. The patient may explore or stay still.",
    },
    {
      title: "Discovering the association",
      start: 35,
      end: 75,
      cue: "The lake becomes clearer and more spacious; the horizon widens and the light softens. Only add a comfort shape if the patient names a current source of comfort.",
    },
    {
      title: "Exploring the contrast",
      start: 75,
      end: 125,
      cue: "Muted grey and violet shapes appear at the edge of the lake, separate from the water. The patient can decline to explore them.",
    },
    {
      title: "Giving the challenge a shape",
      start: 125,
      end: 185,
      cue: "The shape comes close, then a small gap opens between it and the patient's position, with a faint band of light. The shape stays visible.",
    },
    {
      title: "Finding a personal direction",
      start: 185,
      end: 240,
      cue: "The lake remains the anchor. A subtle path opens toward the horizon; the shape stays visible at a comfortable distance. The scene settles.",
    },
  ];
  const neutral = {
    lake: 0,
    light: 0,
    pressure: "none",
    gap: 0,
    path: 0,
    settled: 0,
  };
  // Each step may change part of the scene; the visible scene is the sum of earlier changes.
  const steps = [
    { section: 0, speaker: "therapist", text: "Take a moment to settle into this space. There is nothing you need to achieve here. Just notice what draws your attention. What do you see first?" },
    { section: 0, speaker: "patient", text: "I notice the blue. It feels familiar somehow." },
    { section: 0, speaker: "therapist", text: "Let yourself stay with that blue for a moment. What does it bring to mind?", scene: { lake: 1 } },
    { section: 1, speaker: "patient", text: "It reminds me of the lake near my hometown. I used to go there quite often." },
    { section: 1, speaker: "therapist", text: "What feelings come up when you think about being there?" },
    { section: 1, speaker: "patient", text: "I feel calm. I think of feeling safe, and of not having to worry for a while." },
    { section: 1, speaker: "therapist", text: "It sounds as though that place gives you a sense of safety. Where, if anywhere, do you experience something similar in your life today?", scene: { lake: 2, light: 1 } },
    { section: 2, speaker: "patient", text: "Not very often. I have been busy, and I feel like I always need to be doing something." },
    { section: 2, speaker: "therapist", text: "There seems to be a difference between the calm you remember and the pace of your life now. What does that pressure feel like for you?" },
    { section: 2, speaker: "patient", text: "It feels heavy. There is always something I should be doing, and I feel guilty when I stop." },
    { section: 2, speaker: "therapist", text: "That sounds exhausting. Would you like to explore what that heaviness looks or feels like in this landscape?", scene: { pressure: "edge" }, choice: true },
    { section: 3, speaker: "patient", text: "I imagine a dark, heavy shape. It feels close to me, like I cannot get away from it.", scene: { pressure: "close" } },
    { section: 3, speaker: "therapist", text: "Notice how close it feels, without needing to change it. What do you think that shape represents for you?" },
    { section: 3, speaker: "patient", text: "Maybe my own expectations. I feel like I am never doing enough." },
    { section: 3, speaker: "therapist", text: "If you could change just one thing about your relationship with that pressure, what would you want to be different?" },
    { section: 3, speaker: "patient", text: "I would like to rest without feeling that I have failed.", scene: { gap: 1 } },
    { section: 4, speaker: "therapist", text: "What might help you bring a little of that sense of safety into your everyday life?" },
    { section: 4, speaker: "patient", text: "Maybe I could take a short break in the evening without trying to make it productive." },
    { section: 4, speaker: "therapist", text: "That sounds like a small, concrete experiment. As you imagine giving yourself that time, what do you notice in the landscape now?", scene: { path: 1, pressure: "distant" } },
    { section: 4, speaker: "patient", text: "The lake still feels calm. The heavy shape is still there, but it seems a little further away.", declinedText: "The lake still feels calm. There seems to be a little more room around it." },
    { section: 4, speaker: "therapist", text: "Take a moment to notice that. You do not need to solve everything today. We can return to what you have discovered and explore it further together.", scene: { settled: 1 } },
  ];
  // Declining the heaviness skips section 3 and keeps the pressure shapes away.
  const skipped = (index, declined) => declined && steps[index].section === 3;
  function sceneAt(index, declined = false) {
    const scene = { ...neutral };
    for (let i = 0; i <= index && i < steps.length; i++)
      if (!skipped(i, declined)) Object.assign(scene, steps[i].scene);
    if (declined && index > 10) scene.pressure = "none";
    return scene;
  }
  function nextIndex(index, declined = false) {
    let i = index + 1;
    while (i < steps.length && skipped(i, declined)) i++;
    return i < steps.length ? i : -1;
  }
  function previousIndex(index, declined = false) {
    let i = index - 1;
    while (i >= 0 && skipped(i, declined)) i--;
    return i;
  }
  function lineAt(index, declined = false) {
    const step = steps[index];
    return declined && step.declinedText ? step.declinedText : step.text;
  }
  const api = {
    sections,
    steps,
    neutral,
    sceneAt,
    nextIndex,
    previousIndex,
    lineAt,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.LandscapeDemo = api;
})(typeof window !== "undefined" ? window : globalThis);
