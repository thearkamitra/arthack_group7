/* Pure session rules, shared by the browser and offline Node tests. */
(function (root) {
  'use strict';
  const regions = ['sky', 'ridge', 'water'];
  const clients = [
    { id: 'demo-jamie', name: 'Jamie Morgan', initials: 'JM', color: 'sage', focus: 'Making room for change', description: 'Exploring transitions with a little more space and curiosity.' },
    { id: 'demo-alex', name: 'Alex Rivera', initials: 'AR', color: 'lavender', focus: 'Finding a steadier rhythm', description: 'Noticing the places and patterns that feel grounding.' },
    { id: 'demo-robin', name: 'Robin Ellis', initials: 'RE', color: 'peach', focus: 'Reconnecting with curiosity', description: 'An open-ended exploration of what feels meaningful.' }
  ];
  function fresh() { return { version: 1, sessions: [], notes: {} }; }
  function load(raw) {
    if (!raw) return fresh();
    try {
      const data = JSON.parse(raw);
      if (data.version !== 1 || !Array.isArray(data.sessions) || !data.notes || typeof data.notes !== 'object' || Array.isArray(data.notes)) return fresh();
      const valid = data.sessions.every(s => s && clients.some(c => c.id === s.clientId) && typeof s.id === 'string' && ['active', 'paused', 'completed'].includes(s.status) && regions.every(r => Number.isInteger(s.depth?.[r]) && s.depth[r] >= 0 && s.depth[r] <= 3) && Array.isArray(s.events) && typeof s.preNotes === 'string' && typeof s.postNotes === 'string' && Number.isFinite(s.remaining) && s.remaining >= 0 && s.remaining <= 30 && regions.includes(s.region));
      if (!valid) return fresh();
      // Restored sessions require an explicit resume; time away never counts as exploration.
      data.sessions.forEach(s => { if (s.status === 'active') s.status = 'paused'; });
      return data;
    } catch { return fresh(); }
  }
  function create(clientId, setup, now = new Date().toISOString()) {
    if (!clients.some(c => c.id === clientId)) throw new Error('Unknown demo client');
    if (!setup.goal?.trim() || !setup.consent) throw new Error('A session aim and demo acknowledgement are required');
    return { id: 'session-' + (globalThis.crypto?.randomUUID?.() || Math.random().toString(36).slice(2)), clientId, createdAt: now, completedAt: null, status: 'active', goal: setup.goal.trim(), preNotes: setup.preNotes || '', postNotes: '', before: setup.before || '', after: '', exclusions: setup.exclusions || '', depth: {sky: 0, ridge: 0, water: 0}, region: 'ridge', remaining: 30, cycle: 1, pendingCycle: false, approved: false, events: [{type: 'guide', text: 'Take a moment to look around. What draws your attention?', at: now}] };
  }
  function select(session, region, now = new Date().toISOString()) {
    if (session.status !== 'active' || session.pendingCycle || !regions.includes(region)) return false;
    session.region = region;
    session.events.push({type: 'selection', region, text: 'Selected ' + region + ' with desktop controls', at: now});
    return true;
  }
  function reflect(session, text, now = new Date().toISOString()) {
    const clean = text.trim();
    if (session.status !== 'active' || session.pendingCycle || !clean || clean.length > 2000) return false;
    const region = session.region;
    session.depth[region] = Math.min(3, session.depth[region] + 1);
    session.events.push({type: 'reflection', text: clean, region, at: now});
    const prompts = { sky: 'What would you like to give a little more space to?', ridge: 'What feels steady here, and what would you like to change?', water: 'What do you notice when you let this moment settle?' };
    session.events.push({type: 'guide', text: prompts[region], region, at: now});
    return true;
  }
  function tick(session) {
    if (session.status !== 'active' || session.pendingCycle) return false;
    session.remaining = Math.max(0, session.remaining - 1);
    if (!session.remaining) { session.pendingCycle = true; session.events.push({type: 'cycle', text: '30-second simulated exploration complete. Waiting for a deliberate next step.', at: new Date().toISOString()}); }
    return true;
  }
  function next(session) {
    if (session.status !== 'active' || !session.pendingCycle) return false;
    session.cycle++; session.remaining = 30; session.pendingCycle = false;
    session.events.push({type: 'cycle', text: 'Started cycle ' + session.cycle + ' with participant confirmation', at: new Date().toISOString()});
    return true;
  }
  function pause(session) { if (session.status === 'active') { session.status = 'paused'; return true; } return false; }
  function resume(session) { if (session.status === 'paused') { session.status = 'active'; return true; } return false; }
  function finish(session) { if (session.status === 'completed') return false; session.status = 'completed'; session.completedAt = new Date().toISOString(); return true; }
  const api = { clients, regions, fresh, load, create, select, reflect, tick, next, pause, resume, finish };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.LandscapeState = api;
})(typeof window !== 'undefined' ? window : globalThis);
