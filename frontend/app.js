(function () {
  "use strict";
  const S = window.LandscapeState;
  const STORAGE_KEY = "inner-landscape-demo-v1";
  let storageAvailable = true;
  let data;
  try {
    data = S.load(localStorage.getItem(STORAGE_KEY));
  } catch {
    data = S.fresh();
    storageAvailable = false;
  }
  const $ = (selector) => document.querySelector(selector);
  const esc = (value) =>
    String(value ?? "").replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
  const icons = {
    home: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    people:
      '<circle cx="9" cy="8" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M16 5a3 3 0 0 1 0 6M18 14a5 5 0 0 1 3 4v3"/>',
    notes:
      '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
    calendar:
      '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 11h18M8 15h2M14 15h2"/>',
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    back: '<path d="M19 12H5M11 6l-6 6 6 6"/>',
    chevron: '<path d="m9 5 7 7-7 7"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    leaf: '<path d="M20 3C8 2 2 7 4 14s15 9 16-11ZM5 20 16 8M8 16V9M11 13h6"/>',
    search: '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/>',
    heart:
      '<path d="M20 13 12 21 4 13C-2 6 7 0 12 7c5-7 14-1 8 6Z"/><path d="M5 12h4l2-4 3 8 2-4h3"/>',
    headset:
      '<path d="M4 7h16l2 11-6 1-4-4-4 4-6-1Z"/><path d="M8 11h1M15 11h1"/>',
    audio: '<path d="M5 9v6M9 5v14M13 8v8M17 3v18M21 9v6"/>',
    image:
      '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8" cy="8" r="1"/><path d="m3 17 5-5 4 4 4-6 5 7"/>',
    shield:
      '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z"/><path d="m8 12 3 3 5-6"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    pause: '<path d="M8 5v14M16 5v14"/>',
    play: '<path d="m8 4 12 8-12 8Z"/>',
    settings:
      '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2"/>',
    close: '<path d="m5 5 14 14M19 5 5 19"/>',
    book: '<path d="M12 5C8 2 4 3 2 4v16c3-2 7-2 10 0 3-2 7-2 10 0V4c-3-1-7-2-10 1ZM12 5v15"/>',
  };
  function icon(name, cls = "") {
    return `<svg class="icon ${cls}" viewBox="0 0 24 24" aria-hidden="true">${icons[name] || icons.leaf}</svg>`;
  }
  const client = (id) => S.clients.find((c) => c.id === id) || S.clients[0];
  const sessions = (id) =>
    data.sessions
      .filter((s) => !id || s.clientId === id)
      .slice()
      .reverse();
  const current = () => data.sessions.find((s) => s.status !== "completed");
  const byId = (id) => data.sessions.find((s) => s.id === id);
  function save() {
    try {
      for (const session of data.sessions)
        for (const item of session.events) {
          if (!item.event_id) item.event_id = crypto.randomUUID();
          item.session_id = session.id;
          item.schema_version = 1;
          item.source = item.source || "desktop";
          if (!item.cycle_id) item.cycle_id = session.cycle;
        }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
      if (window.LandscapeBackend?.connected)
        window.LandscapeBackend.save(data).catch((error) =>
          toast(error.message),
        );
      storageAvailable = true;
    } catch {
      storageAvailable = false;
      toast("Browser storage is unavailable. Changes last only in this tab.");
    }
  }
  // Persist the explicit pause applied to restored sessions.
  if (data.sessions.length) save();
  function toast(message) {
    $("#toast").textContent = message;
    $("#toast").classList.add("visible");
    clearTimeout(toast.timer);
    toast.timer = setTimeout(
      () => $("#toast").classList.remove("visible"),
      3500,
    );
  }
  function date(value, options = {}) {
    return new Date(value).toLocaleDateString("en-GB", {
      day: "numeric",
      month: "short",
      ...options,
    });
  }
  function time(value) {
    return new Date(value).toLocaleTimeString("en-GB", {
      hour: "2-digit",
      minute: "2-digit",
    });
  }
  function avatar(c, large = false) {
    return `<span class="avatar ${c.color} ${large ? "large" : ""}">${esc(c.initials)}</span>`;
  }
  function brand() {
    return `<a class="brand" href="#overview" aria-label="Inner Landscape home"><span class="brand-mark">${icon("leaf")}</span><span>inner<br><small>landscape</small></span></a>`;
  }
  function button(label, action, secondary = false, extra = "") {
    return `<button class="button ${secondary ? "secondary" : ""}" data-action="${action}" ${extra}>${label}</button>`;
  }
  function link(label, href, secondary = false) {
    return `<a class="button ${secondary ? "secondary" : ""}" href="#${href}">${label}</a>`;
  }
  function head(eyebrow, title, description, action = "") {
    return `<div class="page-head"><div><span class="eyebrow">${eyebrow}</span><h1>${title}</h1><p>${description}</p></div>${action}</div>`;
  }
  const navItems = [
    ["overview", "home", "Overview"],
    ["clients", "people", "Clients"],
    ["sessions", "calendar", "Sessions"],
    ["demo", "play", "Guided demo"],
    ["notes", "notes", "Notes"],
    ["settings", "settings", "Settings"],
  ];
  function layout(content, section) {
    return `<div class="shell"><aside class="sidebar">${brand()}<div class="workspace-label">YOUR WORKSPACE</div><nav class="nav" aria-label="Workspace">${navItems.map(([id, img, title]) => `<a href="#${id}" class="${section === id ? "active" : ""}" ${section === id ? 'aria-current="page"' : ""}>${icon(img)}<span class="nav-label">${title}</span>${id === "clients" ? '<span class="count">3</span>' : ""}</a>`).join("")}</nav><div class="sidebar-bottom"><div class="quiet-card">${icon("leaf")}<p>A little space.<br>A different perspective.</p></div><div class="profile"><span class="avatar">DR</span><div>Demo practitioner<small>Therapist workspace</small></div></div></div></aside><div class="workspace"><header class="topbar"><div class="crumb">Workspace ${icon("chevron")} ${esc(section[0].toUpperCase() + section.slice(1))}</div><div class="top-actions"><span class="subtext date">${date(new Date(), { weekday: "short", year: "numeric" })}</span><span class="pill amber"><span class="dot"></span>${window.LandscapeBackend?.connected ? "Shared Mac demo" : "Local demo"}</span><a href="#client/demo-jamie" class="text-link">Client view ${icon("arrow")}</a></div></header><main id="main" tabindex="-1">${!storageAvailable ? '<div class="storage-alert" role="alert">Local storage is unavailable. Changes will not survive closing this page.</div>' : ""}${content}<div class="footer-note">${icon("shield")} ${window.LandscapeBackend?.connected ? "Fictional clients · Shared on this Mac · Garmin optional · session-only" : "Fictional clients · Browser-local demo · Devices and AI are not connected"}</div></main></div></div>`;
  }
  let artworkId = 0;
  function artwork(depth = {}, hero = false) {
    const id = "land-" + ++artworkId;
    return `<svg class="landscape-svg" viewBox="0 0 900 560" preserveAspectRatio="xMidYMid slice" role="img" aria-label="A soft landscape of sage hills, a misty sky and still water"><defs><linearGradient id="${id}-sky" x2="0" y2="1"><stop stop-color="#e4e9d8"/><stop offset=".6" stop-color="#f1eddb"/><stop offset="1" stop-color="#d5dfca"/></linearGradient><linearGradient id="${id}-lake" x2="0" y2="1"><stop stop-color="#becfc0"/><stop offset="1" stop-color="#d4ded0"/></linearGradient><linearGradient id="${id}-hill" x2=".6" y2="1"><stop stop-color="#bac7ab"/><stop offset="1" stop-color="#7f977a"/></linearGradient><filter id="${id}-blur"><feGaussianBlur stdDeviation="8"/></filter></defs><rect width="900" height="560" fill="url(#${id}-sky)"/><circle cx="660" cy="133" r="48" fill="#f8f1d8" opacity=".85"/><path d="M-40 300Q130 150 260 275T520 245T950 210V560H-40Z" fill="#cdd6bc"/><path d="M-20 370Q140 215 310 340T580 300T950 330V560H-20Z" fill="#b6c7aa"/><path d="M-30 440Q120 310 300 410T620 385T940 355V560H-30Z" fill="url(#${id}-hill)"/><path d="M150 560Q400 390 600 410T1000 480V600H150Z" fill="url(#${id}-lake)"/><path d="M-20 560V410Q180 380 340 480T700 560Z" fill="#809579" opacity=".8"/><g fill="none" stroke="#f5f1d8" stroke-width="2" opacity=".3"><path d="M530 460h140M600 480h180M480 510h220M740 530h90"/></g><g filter="url(#${id}-blur)" fill="#f0efdf" opacity=".45"><ellipse cx="200" cy="330" rx="280" ry="35"/><ellipse cx="710" cy="380" rx="240" ry="30"/></g><g class="region-detail ${depth.sky > 0 || hero ? "visible" : ""}" data-detail="sky"><g stroke="#7f9278" stroke-width="2" fill="none" opacity=".65"><path d="M490 135q10-11 20 0 10-11 20 0M560 108q8-8 16 0 8-8 16 0"/></g>${depth.sky > 1 ? '<path d="M100 180Q200 130 300 155" stroke="#faf5e6" stroke-width="14" stroke-linecap="round" opacity=".5" fill="none"/>' : ""}</g><g class="region-detail ${depth.ridge > 0 || hero ? "visible" : ""}" data-detail="ridge"><g fill="#5f795c" opacity=".75"><path d="m330 315 17-49 17 49h-10l13 25h-40l12-25Z"/><path d="m370 330 12-36 12 36h-8l11 20h-31l10-20Z"/><rect x="345" y="334" width="4" height="20"/></g>${depth.ridge > 1 ? '<path d="M340 382Q400 350 447 385T510 410" stroke="#e4dcc0" stroke-width="8" fill="none" opacity=".8"/>' : ""}${depth.ridge > 2 ? '<path d="M432 377v-28a12 12 0 0 1 24 0v37" fill="#9aab86" stroke="#708663" stroke-width="2"/>' : ""}</g><g class="region-detail ${depth.water > 0 || hero ? "visible" : ""}" data-detail="water"><g fill="none" stroke="#f9f3d9" opacity=".65"><ellipse cx="690" cy="470" rx="33" ry="5"/><ellipse cx="690" cy="470" rx="60" ry="10"/></g>${depth.water > 1 ? '<g stroke="#648064" stroke-width="3"><path d="M770 515q15-45 10-68M785 520q-2-25 13-41"/></g>' : ""}${depth.water > 2 ? '<path d="m605 479 22 0-7 8h-10Z" fill="#718768"/>' : ""}</g></svg>`;
  }
  function scene(session, cls = "", disabled = false) {
    const depth = session?.depth || {};
    return `<div class="scene ${cls}" id="scene">${artwork(depth)}${session?.media && session.media.source !== "desktop_snapshot" ? `<${session.media.kind === "video" ? "video" : "img"} class="applied-media" src="${esc(session.media.url)}" ${session.media.kind === "video" ? (session.status === "active" ? 'autoplay muted playsinline preload="metadata"' : 'muted playsinline preload="metadata"') : 'alt="Approved session landscape"'}></${session.media.kind === "video" ? "video" : "img"}>` : ""}<span class="scene-label">${session ? "DESKTOP EXPLORATION · SIMULATED" : "A LITTLE ROOM TO EXPLORE"}</span>${session ? `<div class="scene-regions" aria-label="Choose a landscape region">${S.regions.map((r, i) => `<button class="region-button" data-action="select" data-region="${r}" aria-label="Explore ${r}" aria-pressed="${session.region === r}" ${disabled ? "disabled" : ""}><span>${["The sky", "The ridges", "The water"][i]} · ${(depth[r] || 0) + 1}/4</span></button>`).join("")}</div>` : ""}</div>`;
  }
  function clientRows() {
    return S.clients
      .map((c) => {
        const list = sessions(c.id);
        return `<a class="client-row" href="#profile/${c.id}">${avatar(c)}<div><strong>${esc(c.name)}</strong><small>${esc(c.focus)}</small></div><div class="row-end"><span class="pill sage">${list.length ? list.length + " session" + (list.length > 1 ? "s" : "") : "Ready to begin"}</span>${icon("chevron")}</div></a>`;
      })
      .join("");
  }
  function overview() {
    const active = current();
    const completed = sessions().filter((s) => s.status === "completed");
    const activeLink = active ? `session/${active.id}` : "prepare/demo-jamie";
    return layout(
      `${head("A SPACE FOR MEANINGFUL MOMENTS", "Make room for reflection.", "A quiet overview of your clients, conversations, and what comes next.", link(icon(active ? "play" : "plus") + (active ? "Return to session" : "Begin a session"), activeLink))}<section class="hero"><div class="hero-copy"><span class="eyebrow">A DIFFERENT WAY TO EXPLORE</span><h2>Let the conversation<br>shape the landscape.</h2><p>A gentle space where attention becomes a starting point, and each reflection opens something new.</p><a class="text-link" href="#${activeLink}">${active ? "Continue exploring" : "Prepare your first session"} ${icon("arrow")}</a><br><a class="text-link" href="#demo">Watch the 4-minute guided demo ${icon("arrow")}</a></div><div class="hero-art">${artwork({}, true)}</div></section><div class="stats"><div class="stat"><span class="stat-icon">${icon("people")}</span><div><div class="stat-label">Clients in your workspace</div><strong>3</strong><small>fictional demo profiles</small></div></div><div class="stat"><span class="stat-icon">${icon("calendar")}</span><div><div class="stat-label">Completed sessions</div><strong>${completed.length}</strong><small>${completed.length ? "moments to look back on" : "a fresh beginning"}</small></div></div><div class="stat"><span class="stat-icon">${icon("notes")}</span><div><div class="stat-label">Session reflections</div><strong>${data.sessions.reduce((n, s) => n + s.events.filter((e) => e.type === "reflection").length, 0)}</strong><small>${window.LandscapeBackend?.connected ? "saved on this Mac" : "saved in this browser"}</small></div></div></div><div class="grid-two"><section><div class="section-head"><div><h2>Your clients</h2><p>Every journey starts with a conversation.</p></div><a href="#clients" class="text-link">View all ${icon("arrow")}</a></div><div class="panel">${clientRows()}</div></section><section><div class="section-head"><h2>A moment for you</h2></div><div class="panel journal">${icon("leaf", "leaf")}<span class="eyebrow">THE PRACTITIONER'S PAUSE</span><h3>Arrive before you begin.</h3><p>Take a breath. Notice what you bring into the room. There is no need to have every answer.</p><a href="#notes" class="text-link">Open your notes ${icon("arrow")}</a></div><div class="callout mt"><strong>Start with curiosity.</strong><br>This prototype uses a scripted guide. Your judgement and the client's choices lead the experience.</div></section></div>`,
      "overview",
    );
  }
  function clientsPage() {
    return layout(
      `${head("THE PEOPLE YOU SUPPORT", "Every journey is personal.", "A little context helps you meet each person where they are.")}<div class="section-head"><div class="search">${icon("search")}<input id="client-search" aria-label="Search demo clients" placeholder="Find a client…" autocomplete="off"></div><span class="subtext">3 fictional clients</span></div><div class="client-grid" id="client-grid">${clientCards("")}</div>`,
      "clients",
    );
  }
  function clientCards(query) {
    const matches = S.clients.filter((c) =>
      (c.name + " " + c.focus).toLowerCase().includes(query.toLowerCase()),
    );
    return matches.length
      ? matches
          .map(
            (c) =>
              `<article class="panel client-card">${avatar(c, true)}<div><h2>${c.name}</h2><div class="client-id">FICTIONAL CLIENT · ${c.initials}-00${S.clients.indexOf(c) + 1}</div></div><p>${c.description}</p><div class="card-meta"><span>${sessions(c.id).length} sessions</span><span>${window.LandscapeBackend?.connected ? "Shared Mac demo" : "Local demo"}</span></div>${link("View client " + icon("arrow"), "profile/" + c.id, true)}</article>`,
          )
          .join("")
      : '<div class="panel empty empty-search">No clients match this search.</div>';
  }
  function history(list) {
    return list.length
      ? list
          .map(
            (s) =>
              `<article class="history-item"><span class="history-date"><strong>${new Date(s.createdAt).getDate()}</strong>${new Date(s.createdAt).toLocaleDateString("en-GB", { month: "short" })}</span><div><h3>${esc(s.goal)}</h3><p>${esc(client(s.clientId).name)} · ${s.status === "completed" ? "Completed" : "Paused or in progress"} · ${s.events.filter((e) => e.type === "reflection").length} reflections ${s.approved ? "· Reviewed" : ""}</p></div><a class="button secondary small" href="#${s.status === "completed" ? "review" : "session"}/${s.id}">${s.status === "completed" ? "Review" : "Open"} ${icon("arrow")}</a></article>`,
          )
          .join("")
      : `<div class="empty">${icon("calendar")}<h3>A new chapter awaits.</h3><p>Completed sessions will appear here, along with notes and reflections.</p></div>`;
  }
  function profilePage(id) {
    const c = client(id),
      list = sessions(c.id);
    return layout(
      `<a href="#clients" class="back">${icon("back")} All clients</a><div class="page-head"><div class="spaced">${avatar(c, true)}<div><h1 style="margin-bottom:4px">${c.name}</h1><p>${c.focus} <span class="badge">DEMO CLIENT</span></p></div></div>${link(icon("plus") + "Prepare session", "prepare/" + c.id)}</div><div class="tabs"><span class="active" style="padding:13px 0;font-size:12px;border-bottom:2px solid var(--sage)">Overview</span><a href="#client/${c.id}">Client experience ${icon("arrow")}</a></div><div class="split-details"><section><div class="section-head"><h2>Session history</h2><span class="subtext">${list.length} sessions</span></div><div class="panel">${history(list)}</div><div class="panel panel-pad mt"><div class="section-head"><h2>Practitioner notes</h2><span class="save-indicator" id="save-state">${window.LandscapeBackend?.connected ? "Saved on Mac" : "Browser-local"}</span></div><p class="subtext">Private in a future connected system. This demo has no authentication—use fictional content only.</p><label for="profile-note">Ongoing context</label><textarea id="profile-note" data-profile="${c.id}" placeholder="What would you like to remember for next time?" maxlength="10000">${esc(data.notes[c.id] || "")}</textarea><div class="form-actions">${button("Save note", "save-profile", false, `data-client="${c.id}"`)}</div></div></section><aside><div class="panel panel-pad"><span class="eyebrow">EXPLORATION FOCUS</span><h2 class="mt">${c.focus}</h2><p class="subtext">${c.description}</p><div class="divider"></div><span class="eyebrow">ASSESSMENTS</span><p class="subtext mt">No standardized questionnaire selected. A practitioner will select an appropriate instrument before it is added.</p><span class="pill">Not configured</span></div><div class="callout mt">Client check-ins are simple comfort ratings, not standardized tests or clinical scores.</div></aside></div>`,
      "clients",
    );
  }
  function devices() {
    return [
      ["headset", "Meta Quest 2", "Head-directed attention"],
      ["heart", "Garmin Venu 4", "Heart-rate broadcast"],
      ["audio", "ElevenLabs", "Conversational guide"],
      ["image", "fal.ai", "Image & video generation"],
    ]
      .map(
        ([i, t, d]) =>
          `<div class="device"><span class="device-icon">${icon(i)}</span><div><strong>${t}</strong><small>${d}</small></div><span class="pill">Not connected</span></div>`,
      )
      .join("");
  }
  function comfort(
    name,
    value = "",
    label = "How comfortable do you feel right now?",
  ) {
    return `<div class="field"><label for="${name}">${label}</label><select id="${name}" name="${name}"><option value="">Prefer not to answer</option>${["1 · Not comfortable", "2 · A little uncomfortable", "3 · Somewhere in between", "4 · Mostly comfortable", "5 · Very comfortable"].map((v, i) => `<option value="${i + 1}" ${String(value) === String(i + 1) ? "selected" : ""}>${v}</option>`).join("")}</select><small class="hint">Optional personal check-in · not a standardized assessment</small></div>`;
  }
  function preparePage(id) {
    const c = client(id),
      active = current();
    return layout(
      `<a href="#profile/${c.id}" class="back">${icon("back")} ${c.name}</a>${head("BEFORE YOU BEGIN", "Set the scene.", "A few intentions, a little context, and space for the unexpected.")}<div class="split-details"><form id="prepare-form" class="panel panel-pad"><div class="section-head"><h2>Session preparation</h2><span class="pill sage">${c.name}</span></div><input type="hidden" name="clientId" value="${c.id}"><div class="field"><label for="goal">What would you like to make room for?</label><input id="goal" name="goal" placeholder="e.g. Exploring change with curiosity" required maxlength="150" value="${esc(c.focus)}"></div><div class="field"><label for="preNotes">Before-session notes</label><textarea id="preNotes" name="preNotes" placeholder="Context, intentions, or things to return to…" maxlength="10000"></textarea><small class="hint">Practitioner notes are separate from the scripted conversation.</small></div><div class="field"><label for="exclusions">Topics or imagery to avoid</label><input id="exclusions" name="exclusions" maxlength="500" placeholder="Optional boundaries for a future AI guide"><small class="hint">Recorded for review. This simulator uses fixed questions and cannot enforce topic rules against an AI.</small></div>${comfort("before")}<div class="callout">${icon("book")} <strong>Questionnaires come later.</strong> Standardized assessments will be chosen with a practitioner. Nothing is scored or recommended automatically here.</div><label class="check-row"><input name="consent" type="checkbox" required><span>I understand this is a desktop simulation with fictional content. Notes and reflections are ${window.LandscapeBackend?.connected ? "saved on this Mac" : "saved in this browser"}. Optional voice, headset and live watch connections require separate explicit actions during the session.</span></label>${active ? `<div class="callout mb">There is already an unfinished session. <a href="#session/${active.id}" class="text-link">Return to it ${icon("arrow")}</a> before starting another.</div>` : ""}<div class="form-actions">${link("Back", "profile/" + c.id, true)}<button class="button" ${active ? "disabled" : ""}>${icon("play")} Begin demo session</button></div></form><aside><div class="panel panel-pad"><h2>A gentle starting point</h2><p class="subtext">A large landscape. Three regions. A scripted guide to help you find a place to begin.</p>${scene(null, "small")}<div class="divider"></div><h3>Connection check</h3>${devices()}</div></aside></div>`,
      "sessions",
    );
  }
  function sessionLegend(s) {
    return `<div class="scene-legend">${S.regions.map((r) => `<span class="pill ${s.region === r ? "sage" : ""}">${r === "ridge" ? "Ridges" : r[0].toUpperCase() + r.slice(1)} · ${s.depth[r] + 1}/4</span>`).join("")}</div>`;
  }
  function latestGuide(s) {
    return [...s.events].reverse().find((e) => e.type === "guide")?.text || "";
  }
  function timeline(s) {
    return s.events
      .slice()
      .reverse()
      .map(
        (e) =>
          `<li class="${esc(e.type)}"><small>${time(e.at)} · ${esc({ guide: "Scripted guide", selection: "Desktop selection", reflection: "Client reflection", cycle: "Cycle event", note: "Practitioner note", control: "Session control" }[e.type] || e.type)}</small><p>${esc(e.text)}</p></li>`,
      )
      .join("");
  }
  function stage(s, clientMode = false) {
    const disabled = s.status !== "active" || s.pendingCycle;
    return `<section><div id="scene-slot">${scene(s, clientMode ? "client-scene" : "", disabled)}</div><div id="scene-legend">${sessionLegend(s)}</div>${s.proposal ? `<div class="callout mb"><strong>Suggested next region: ${esc(s.proposal.region || "ask the practitioner")}</strong><br>${esc(s.proposal.reason)} ${s.proposal.region ? button("Confirm region", "select", true, `data-id="${s.id}" data-region="${s.proposal.region}" ${s.status !== "active" ? "disabled" : ""}`) : ""}</div>` : ""}<div class="progress" aria-hidden="true"><span id="cycle-progress" style="width:${((30 - s.remaining) / 30) * 100}%"></span></div><div class="stage-footer"><div class="timer"><strong id="remaining">${String(s.remaining).padStart(2, "0")}</strong> / 30 sec <span class="countdown-caption">· Cycle ${s.cycle} · simulated window</span></div><div class="controls">${button(icon(s.status === "paused" ? "play" : "pause") + (s.status === "paused" ? "Resume" : "Pause"), "pause", true, `data-id="${s.id}"`)}${button("Finish session", "finish", true, `data-id="${s.id}"`)}</div></div>${s.pendingCycle ? `<div class="callout"><strong>A moment to reflect.</strong><br>This 30-second window is complete. Stay here as long as you need. ${button("Begin next cycle " + icon("arrow"), "next", false, `data-id="${s.id}" ${s.status !== "active" ? "disabled" : ""}`)}</div>` : ""}${s.status === "paused" ? '<div class="callout">Session paused. The clock and exploration are held until you resume.</div>' : ""}<p class="demo-notice">${s.driver === "unity" ? "Unity participant paired; head-directed reports are used when received." : "Desktop selection uses clicks or keyboard."} ${s.media?.job_id ? "Approved provider media is shown." : "Artwork is procedural; no generated video is playing."}</p></section>`;
  }
  function guide(s) {
    const disabled = s.status !== "active" || s.pendingCycle;
    return `<section class="panel guide-panel"><div class="guide-heading"><span class="guide-orb"></span><div><strong>Your reflection guide</strong><small>${window.LandscapeVoice?.active ? "ElevenLabs live voice · microphone active" : "Scripted preview · no AI connected"}</small></div></div><p class="guide-text" id="guide-text">${s.pendingCycle ? "Take your time with this moment. Begin the next cycle when you feel ready to explore further." : esc(latestGuide(s))}</p><form id="reflection-form" data-id="${s.id}"><label for="reflection">A few words about the ${s.region === "ridge" ? "ridges" : s.region}</label><textarea id="reflection" name="reflection" placeholder="There is no right answer…" required maxlength="2000" ${disabled ? "disabled" : ""}></textarea><small class="hint subtext">This is a simulation. Your words are recorded, but their meaning does not drive the artwork.</small><button class="button wide mt" ${disabled ? "disabled" : ""}>Reflect & reveal ${icon("arrow")}</button></form></section>`;
  }
  function sessionPage(id) {
    const s = byId(id);
    if (!s) return notFound();
    if (s.status === "completed") {
      location.hash = "review/" + s.id;
      return "";
    }
    return layout(
      `<div class="page-head"><div><span class="eyebrow">SESSION IN PROGRESS · ${esc(client(s.clientId).name)}</span><h1>${esc(s.goal)}</h1><p>A conversation, a landscape, and time to notice.</p></div><a class="button secondary" href="#client-session/${s.id}">Client view ${icon("arrow")}</a></div><div class="session-grid">${stage(s)}${guide(s)}</div>${connectionControls(s)}${garminControls(s)}<div class="device-summary">${[s.driver === "unity" ? "Unity · paired" : "Quest 2 · not connected", "Garmin · optional live monitoring", "ElevenLabs · not connected", "fal.ai · not connected"].map((t) => `<div class="device-mini">${t.split(" · ")[0]}<strong style="margin:6px 0 0">${t.split(" · ")[1]}</strong></div>`).join("")}</div><div class="grid-two mt"><section class="panel panel-pad"><div class="section-head"><h2>Conversation & interactions</h2><span class="badge">LIVE DEMO TIMELINE</span></div><ol class="timeline" id="timeline">${timeline(s)}</ol></section><section class="panel panel-pad"><h2>In-the-moment notes</h2><p class="subtext">Keep your observations separate from the client's words.</p><form id="session-note" data-id="${s.id}"><label for="moment-note">Practitioner observation</label><textarea id="moment-note" name="note" maxlength="5000" placeholder="What feels useful to remember?" required></textarea><div class="form-actions"><button class="button secondary">Add to timeline</button></div></form><div class="callout mt">Optional live heart rate can flag a sustained rise for a check-in. Ask the participant what they need; pulse does not identify emotion.</div></section></div>${referencesPanel(s.id)}`,
      "sessions",
    );
  }
  function garminControls(s) {
    if (!window.LandscapeBackend?.connected) return "";
    const g = window.LandscapeGarmin.state;
    return `<section class="panel panel-pad mt" aria-labelledby="garmin-heading"><div class="section-head"><h2 id="garmin-heading">Garmin heart rate</h2><span class="pill" id="garmin-status">Disconnected</span></div><p class="subtext">Wear your watch and start Broadcast Heart Rate. Close the standalone research receiver before connecting here. The Mac receives Bluetooth; your browser only displays local observations.</p><div class="garmin-readings"><strong id="garmin-bpm">— BPM</strong><span id="garmin-baseline">No baseline</span><span id="garmin-age">No readings received</span></div><p id="garmin-cue" role="status"></p><div class="spaced"><button class="button secondary" data-action="garmin-scan" data-id="${esc(s.id)}">Scan for watch</button><label for="garmin-device">Watch</label><select id="garmin-device" ${g.devices.length ? "" : "disabled"}>${g.devices.map(d => `<option value="${esc(d.id)}">${esc(d.name)}</option>`).join("")}</select><button class="button" data-action="garmin-connect" data-id="${esc(s.id)}">Connect watch</button><button class="button secondary" data-action="garmin-stop" data-id="${esc(s.id)}">Disconnect & clear</button></div><label class="check-row"><input type="checkbox" id="garmin-consent"><span>I agree to local, session-only heart-rate monitoring. BPM and baseline stay in memory, are not sent to the voice guide, and are cleared on pause, finish, navigation away or disconnection.</span></label><p class="hint">Prototype pacing cue: after at least 30 seconds and 15 samples, a rise of at least 20 BPM or 25% above the baseline (whichever is greater) for 5 seconds prompts a check-in. These are engineering thresholds, not medical limits. No automatic scene change or emotion inference.</p><p id="garmin-message" class="subtext" role="status">${esc(g.message)}</p></section>`;
  }
  function updateGarmin() {
    const g = window.LandscapeGarmin?.state;
    if (!g || !$("#garmin-status")) return;
    const o = g.observation;
    const labels = {disconnected:"Disconnected", baseline:"Collecting baseline", tracking:"Receiving live heart rate", elevated:"Sustained rise", stale:"Signal stale — baseline reset"};
    $("#garmin-status").textContent = o.transport === "connecting" ? "Connecting…" : o.transport === "connected" && !o.broadcast_received ? "Connected · waiting for broadcast" : labels[o.status] || "Disconnected";
    $("#garmin-bpm").textContent = o.bpm == null ? "— BPM" : `${o.bpm} BPM`;
    $("#garmin-baseline").textContent = o.baseline == null ? (g.sid ? `Baseline: ${Math.min(30, Math.floor(o.baseline_seconds || 0))}/30 sec · ${o.baseline_samples || 0} samples` : "No baseline") : `Baseline ${o.baseline} BPM · rise threshold ${Math.ceil(o.threshold_bpm)} BPM`;
    $("#garmin-age").textContent = o.age_seconds == null ? "No readings received" : `${o.broadcast_received ? "Broadcast verified · " : ""}Last reading ${o.age_seconds}s ago`;
    $("#garmin-cue").textContent = o.cue || (o.status === "stale" ? "No fresh readings. Pacing cues are suspended; reconnect if the signal does not return." : "");
    $("#garmin-cue").className = o.spike ? "callout garmin-rise" : "subtext";
    $("#garmin-message").textContent = g.message || o.error || "";
    const active = current()?.status === "active";
    for (const action of ["scan", "connect", "stop"]) {
      const b = document.querySelector(`[data-action="garmin-${action}"]`);
      if (b) b.disabled = action === "stop" ? !g.sid : g.busy || !!g.sid || !active || (action === "connect" && !g.devices.length);
    }
  }
  window.addEventListener("garminchange", () => {
    const select = $("#garmin-device"), g = window.LandscapeGarmin.state;
    if (select && Array.from(select.options).map(o => o.value).join() !== g.devices.map(d => d.id).join()) {
      select.replaceChildren(...g.devices.map(d => new Option(d.name, d.id)));
      select.disabled = !g.devices.length;
    }
    updateGarmin();
  });

  function connectionControls(s) {
    const backend = window.LandscapeBackend;
    if (!backend?.connected)
      return '<div class="callout mt">Local-only workspace. Start the coordinator to pair Unity and configure voice/media. Start it to use local Garmin Bluetooth monitoring.</div>';
    return `<section class="panel panel-pad mt"><div class="section-head"><h2>Connected session</h2><span class="pill sage">Mac coordinator</span></div><p class="subtext">Pair the Unity client to this session. Voice sends microphone audio to ElevenLabs only after explicit start. Media uses the current scene plus a visual brief; private notes are not sent. Garmin monitoring is available below with separate consent.</p><div class="spaced">${button("Pair Unity headset", "pair", true, `data-id="${s.id}"`)}${button(window.LandscapeVoice?.active ? "Stop voice" : "Start voice guide", "voice", true, `data-id="${s.id}" ${!backend.status?.paid_enabled || !backend.status?.voice.configured ? "disabled" : ""}`)}${button("Media studio", "media-studio", true, `data-id="${s.id}"`)}<span id="connection-message" class="subtext"></span></div><div id="media-studio"></div></section>`;
  }
  async function captureScene() {
    const svg = document.querySelector("#scene svg");
    if (!svg) throw new Error("Open a live scene first.");
    const copy = svg.cloneNode(true);
    copy.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    copy
      .querySelectorAll(".region-detail")
      .forEach((el) =>
        el.setAttribute(
          "opacity",
          el.classList.contains("visible") ? "1" : "0",
        ),
      );
    const blob = new Blob([new XMLSerializer().serializeToString(copy)], {
        type: "image/svg+xml",
      }),
      url = URL.createObjectURL(blob);
    try {
      const image = new Image();
      image.src = url;
      await image.decode();
      const canvas = document.createElement("canvas");
      canvas.width = 900;
      canvas.height = 560;
      canvas.getContext("2d").drawImage(image, 0, 0, 900, 560);
      return canvas.toDataURL("image/png");
    } finally {
      URL.revokeObjectURL(url);
    }
  }
  async function openMedia(s) {
    const jobs = await window.LandscapeBackend.jobs(s.id),
      enabled = window.LandscapeBackend.status?.paid_enabled;
    document.querySelector("#media-studio").innerHTML =
      `<div class="divider"></div><p class="subtext">${enabled ? "Generation may incur provider charges. One job at a time; four jobs maximum per session. Video output is currently 5 seconds, within the 30-second limit." : "Paid generation is disabled. Restart the coordinator with --enable-paid only after agreeing a test budget."}</p><form id="media-form" data-id="${s.id}"><label for="visual-brief">Visual brief (no names, notes or identifying details)</label><input id="visual-brief" name="brief" required maxlength="1000" placeholder="Soft mist lifting over the selected region"><div class="spaced mt"><select name="kind" aria-label="Media type" style="width:auto"><option value="image">Refine selected image region</option><option value="video">Animate current scene · 5 seconds</option></select><button class="button" ${!enabled ? "disabled" : ""}>Generate preview</button>${button("Refresh jobs", "media-studio", true, `data-id="${s.id}"`)}</div></form><div class="mt">${jobs.map((j) => `<article class="callout mb"><strong>${esc(j.kind)} · ${esc(j.status)}</strong><p class="subtext">${esc(j.error || j.model)}</p>${j.status === "ready" ? `${j.kind === "image" ? `<img src="/api/sessions/${s.id}/media/${j.id}/artifact" alt="Generated preview" style="max-width:100%;border-radius:8px">` : `<video controls preload="metadata" src="/api/sessions/${s.id}/media/${j.id}/artifact" style="width:100%"></video>`}<p class="subtext">Check continuity and region placement before applying. A generated video can move landmarks.</p>${button("Confirm continuity & use", "apply-media", true, `data-id="${s.id}" data-job="${j.id}"`)}` : ""}</article>`).join("") || '<p class="subtext">No generation jobs yet.</p>'}</div>`;
  }
  function sessionsPage() {
    return layout(
      `${head("THE JOURNEY SO FAR", "Moments worth returning to.", "Your session history, with the context that makes it meaningful.", link(icon("plus") + "New session", "clients"))}<div class="panel">${history(sessions())}</div>`,
      "sessions",
    );
  }
  function draftSummary(s) {
    const reflections = s.events.filter((e) => e.type === "reflection"),
      explored = S.regions.filter((r) => s.depth[r]);
    return `${client(s.clientId).name} completed a simulated reflection session focused on “${s.goal}”. ${reflections.length} reflection${reflections.length === 1 ? " was" : "s were"} recorded across ${explored.length} landscape region${explored.length === 1 ? "" : "s"}${explored.length ? ": " + explored.join(", ") : ""}. This template summarizes activity only; it does not interpret clinical meaning. Optional connections may have been used; live heart-rate readings are cleared when monitoring stops and are not part of this review.`;
  }
  function reviewPage(id) {
    const s = byId(id);
    if (!s) return notFound();
    if (s.status !== "completed") {
      location.hash = "session/" + s.id;
      return "";
    }
    const c = client(s.clientId),
      reflections = s.events.filter((e) => e.type === "reflection");
    return layout(
      `<a href="#profile/${c.id}" class="back">${icon("back")} ${c.name}'s sessions</a>${head("AFTER THE CONVERSATION", "Give the moment some meaning.", "Review what happened, add your observations, and decide what to carry forward.", `<span class="pill sage">${s.approved ? "Reviewed" : "Awaiting review"}</span>`)}<div class="split-details"><section><div class="panel panel-pad"><div class="section-head"><h2>${esc(s.goal)}</h2><span class="subtext">${date(s.createdAt)}</span></div>${scene(s, "small", true)}<div class="review-stats"><div class="review-stat"><strong>${reflections.length}</strong><small>client reflections</small></div><div class="review-stat"><strong>${S.regions.filter((r) => s.depth[r]).length}/3</strong><small>regions explored</small></div><div class="review-stat"><strong>${s.cycle}</strong><small>exploration cycles</small></div></div><span class="eyebrow">BEFORE THE SESSION</span><p class="note-box preline">${esc(s.preNotes) || "No pre-session notes recorded."}</p><div class="section-head"><h3>Activity summary</h3><span class="badge">LOCAL TEMPLATE · NOT AI</span></div><p class="subtext">${esc(draftSummary(s))}</p></div><section class="panel panel-pad mt"><h2>Interaction history</h2><ol class="timeline">${timeline(s)}</ol></section></section><section><form id="review-form" data-id="${s.id}" class="panel panel-pad"><h2>Practitioner reflection</h2><p class="subtext">Your notes bring the context. No clinical conclusions are generated automatically.</p>${comfort("after", s.after, "Client comfort after the session")}<div class="field"><label for="postNotes">After-session notes</label><textarea id="postNotes" name="postNotes" rows="7" maxlength="10000" placeholder="What emerged? What might be worth returning to?">${esc(s.postNotes)}</textarea></div><label class="check-row"><input type="checkbox" name="approved" ${s.approved ? "checked" : ""}><span>I have reviewed the interaction history and my notes.</span></label><div class="form-actions"><button class="button">Save review ${icon("check")}</button></div></form><div class="callout mt"><strong>Personal check-ins</strong><br>Before: ${s.before ? esc(s.before) + "/5" : "not answered"} · After: ${s.after ? esc(s.after) + "/5" : "not answered"}<br>These are optional comfort ratings, not a clinical outcome measure.</div><div class="spaced mt">${link("Return to client", "profile/" + c.id, true)}${link("Prepare another session", "prepare/" + c.id, true)}</div></section></div>`,
      "sessions",
    );
  }
  function notesPage() {
    const profileNotes = S.clients.filter((c) => data.notes[c.id]);
    const sessionNotes = sessions().filter(
      (s) =>
        s.preNotes || s.postNotes || s.events.some((e) => e.type === "note"),
    );
    return layout(
      `${head("CONTEXT, HELD WITH CARE", "A place for your observations.", "Practitioner notes stay distinct from client reflections and activity summaries.")}<div class="demo-banner">This is not a private clinical record system. Notes persist in this browser without authentication. Use fictional demonstration content only.</div><div class="notes-list">${profileNotes.map((c) => `<article class="panel note-card"><span class="note-label">ONGOING CONTEXT · ${esc(c.name)}</span><p class="mt">${esc(data.notes[c.id])}</p><a href="#profile/${c.id}" class="text-link">Open client ${icon("arrow")}</a></article>`).join("")}${sessionNotes
        .map(
          (s) =>
            `<article class="panel note-card"><span class="note-label">SESSION NOTES · ${esc(client(s.clientId).name)} · ${date(s.createdAt)}</span><h3>${esc(s.goal)}</h3>${s.preNotes ? `<p><strong>Before:</strong> ${esc(s.preNotes)}</p>` : ""}${s.events
              .filter((e) => e.type === "note")
              .map((e) => `<p><strong>During:</strong> ${esc(e.text)}</p>`)
              .join(
                "",
              )}${s.postNotes ? `<p><strong>After:</strong> ${esc(s.postNotes)}</p>` : ""}<a href="#${s.status === "completed" ? "review" : "session"}/${s.id}" class="text-link">Open session ${icon("arrow")}</a></article>`,
        )
        .join(
          "",
        )}${!profileNotes.length && !sessionNotes.length ? '<div class="panel empty">' + icon("notes") + '<h3>Space for what matters.</h3><p>Add notes in a client profile or before, during and after a session.</p><a href="#clients" class="text-link">Find a client ' + icon("arrow") + "</a></div>" : ""}</div>`,
      "notes",
    );
  }
  function settingsPage() {
    return layout(
      `${head("A LITTLE CLARITY", "Your workspace, explained.", "Connections, local storage, and what this first milestone can do.")}<div class="grid-two"><div class="panel panel-pad"><h2>Connections</h2><p class="subtext">The Mac coordinator supports optional connections during an active session. Garmin uses Bluetooth on the Mac; live readings stay in memory. There are no secret input fields in the frontend.</p>${devices()}<div class="callout mt">API keys belong in the backend environment. Creating a key does not connect this desktop prototype.</div></div><div class="panel panel-pad"><h2>Demo data & privacy</h2><ul class="privacy-list"><li>All three clients are fictional.</li><li>Notes, check-ins and sessions persist in this browser's local storage.</li><li>Garmin heart rate stays local and is cleared on disconnect. Explicitly started voice/media features send their disclosed inputs to their providers.</li><li>The client preview is a presentation mode, not a separate authorized role.</li><li>Returning to an unfinished session requires explicit resume.</li><li>Clearing browser storage removes saved demo data.</li></ul><div class="divider"></div><p class="subtext">To remove this prototype's saved notes and sessions from this browser, confirm below. Other websites' data is unaffected.</p>${button("Clear saved demo data", "clear", true)}</div></div>`,
      "settings",
    );
  }
  function clientLayout(content, c, session) {
    return `<main id="main" class="client-shell" tabindex="-1"><header class="client-header">${brand()}<div class="spaced"><span class="pill amber">Client preview · demo</span><a class="button secondary small" href="#${session ? "session/" + session.id : "profile/" + c.id}">Back to workspace ${icon("arrow")}</a></div></header>${content}<div class="footer-note">${icon("shield")} Fictional participant · Preview mode is not authentication · Use demo content only</div></main>`;
  }
  function clientWelcome(id) {
    const c = client(id),
      active = current();
    return clientLayout(
      `<div class="client-intro"><span class="eyebrow">WELCOME, ${c.name.split(" ")[0].toUpperCase()}</span><h1>A little space.<br>A new perspective.</h1><p>There is nothing to get right. Take your time, follow your curiosity, and see where the landscape takes you.</p></div><div class="client-card-wrap">${scene(null, "small")}<form id="client-start" class="panel panel-pad client-welcome-form"><input type="hidden" name="clientId" value="${c.id}"><h2>Before we begin</h2><p class="subtext">This is a scripted desktop preview. You can pause or stop whenever you want. No microphone, headset or watch is being used.</p>${comfort("before")}<label class="check-row"><input name="consent" type="checkbox" required><span>I understand this is a demo and anything I type is ${window.LandscapeBackend?.connected ? "saved on this Mac" : "saved in this browser"}. I will use fictional content.</span></label>${active ? `<div class="callout mb">An unfinished session is already open. ${link("Return to session", "client-session/" + active.id, true)}</div>` : ""}<button class="button wide" ${active ? "disabled" : ""}>Begin reflection ${icon("arrow")}</button></form></div>`,
      c,
    );
  }
  function clientSession(id) {
    const s = byId(id);
    if (!s) return notFound();
    const c = client(s.clientId);
    if (s.status === "completed")
      return clientLayout(
        `<div class="client-intro"><span class="eyebrow">A MOMENT TO CLOSE</span><h1>Take something<br>gentle with you.</h1><p>Your reflection is complete. You can leave the landscape here and return to your practitioner.</p></div><div class="client-card-wrap">${scene(s, "small", true)}<div class="panel panel-pad mt"><h2>Your journey</h2><p class="subtext">You shared ${s.events.filter((e) => e.type === "reflection").length} reflections across ${S.regions.filter((r) => s.depth[r]).length} regions.</p><form id="client-checkout" data-id="${s.id}">${comfort("after", s.after)}<button class="button">Save check-in ${icon("check")}</button></form></div></div>`,
        c,
        s,
      );
    return clientLayout(
      `<div class="page-head"><div><span class="eyebrow">GUIDED REFLECTION</span><h1>Follow what draws you in.</h1><p>Choose a region, share a thought, or simply take a moment.</p></div><span class="pill">Scripted guide · simulated artwork</span></div><div class="client-session">${stage(s, true)}${guide(s)}</div>`,
      c,
      s,
    );
  }
  // Therapist reference files served from frontend/reference/. Notes stay in this browser, per session or demo.
  const REFERENCES = [
    { id: "questionnaire", title: "Initial questionnaire", file: "reference/initial-questionnaire.pdf", pdf: true },
    { id: "colours", title: "Colour map · colours", file: "reference/colour-map-colours.png" },
    { id: "shapes-1", title: "Colour map · shapes and lines (Admiration–Pity)", file: "reference/colour-map-shapes-1.png" },
    { id: "shapes-2", title: "Colour map · shapes and lines (Pride–Surprise)", file: "reference/colour-map-shapes-2.png" },
  ];
  const NOTES_KEY = "inner-landscape-reference-notes-v1";
  let referenceNotes = {};
  try {
    referenceNotes = JSON.parse(localStorage.getItem(NOTES_KEY) || "{}") || {};
  } catch {
    referenceNotes = {};
  }
  const openReference = {};
  function referencesPanel(scope) {
    const open = REFERENCES.find((r) => r.id === openReference[scope]);
    const list = REFERENCES.map(
      (r) =>
        `<button class="button secondary small" data-action="reference-open" data-scope="${esc(scope)}" data-ref="${r.id}" aria-pressed="${open === r}">${icon("notes")}${esc(r.title)}</button>`,
    ).join("");
    const note = open && `reference-note-${scope}-${open.id}`;
    const viewer = open
      ? `<div class="reference-viewer">${open.pdf ? `<iframe src="${open.file}" title="${esc(open.title)}"></iframe>` : `<img src="${open.file}" alt="${esc(open.title)} reference table">`}</div><div class="spaced"><a class="text-link" href="${open.file}" target="_blank" rel="noopener">Open in new tab ${icon("arrow")}</a></div><label for="${esc(note)}">Notes on ${esc(open.title)}</label><textarea id="${esc(note)}" data-reference-note="${esc(scope + ":" + open.id)}" maxlength="5000" placeholder="Scores, observations or what the client says these mean to them">${esc(referenceNotes[scope + ":" + open.id] || "")}</textarea><p class="subtext">${storageAvailable ? "Saved in this browser as you type." : "Browser storage is unavailable; notes are kept in memory only."}</p>`
      : '<p class="subtext">Choose a file to open it here and take notes alongside it.</p>';
    return `<section class="panel panel-pad mt" id="references-${esc(scope)}"><div class="section-head"><h2>Reference materials</h2><span class="badge">PRACTITIONER ONLY</span></div><p class="subtext">The colour maps are a starting point, not a key: ask what colours and shapes mean to the client, and do not infer emotions from colour alone.</p><div class="reference-list">${list}</div>${viewer}</section>`;
  }
  document.addEventListener("click", (e) => {
    const target = e.target.closest("[data-action='reference-open']");
    if (!target) return;
    const scope = target.dataset.scope;
    openReference[scope] = openReference[scope] === target.dataset.ref ? null : target.dataset.ref;
    const panel = document.getElementById("references-" + scope);
    if (panel) panel.outerHTML = referencesPanel(scope);
  });
  document.addEventListener("input", (e) => {
    const key = e.target.dataset?.referenceNote;
    if (!key) return;
    referenceNotes[key] = e.target.value;
    try {
      localStorage.setItem(NOTES_KEY, JSON.stringify(referenceNotes));
    } catch {
      // Notes remain in memory; the panel already states when storage is unavailable.
    }
  });
  // Scripted walkthrough state stays in memory: nothing is saved or sent.
  const D = window.LandscapeDemo;
  const demo = {
    index: -1,
    declined: false,
    paused: false,
    neutral: false,
    done: false,
    elapsed: 0,
    comfort: [],
  };
  const clock = (seconds) =>
    String(Math.floor(seconds / 60)).padStart(2, "0") +
    ":" +
    String(seconds % 60).padStart(2, "0");
  const demoRunning = () => demo.index >= 0 && !demo.done;
  function demoScene() {
    return demoRunning() && !demo.neutral
      ? D.sceneAt(demo.index, demo.declined)
      : demo.done
        ? D.sceneAt(D.steps.length - 1, demo.declined)
        : D.neutral;
  }
  function demoArtwork() {
    return `<svg class="landscape-svg demo-svg" viewBox="0 0 900 560" preserveAspectRatio="xMidYMid slice" role="img" aria-label="An abstract landscape that changes with the scripted conversation"><defs><linearGradient id="demo-sky" x2="0" y2="1"><stop stop-color="#e2e6dc"/><stop offset=".65" stop-color="#efece0"/><stop offset="1" stop-color="#d9e0d0"/></linearGradient><linearGradient id="demo-lake" x2="0" y2="1"><stop stop-color="#8eb0c4"/><stop offset="1" stop-color="#bdd2d9"/></linearGradient><radialGradient id="demo-glow"><stop stop-color="#fff4d6" stop-opacity=".9"/><stop offset="1" stop-color="#fff4d6" stop-opacity="0"/></radialGradient><filter id="demo-soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="14"/></filter><filter id="demo-shape" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="5"/></filter></defs><rect width="900" height="560" fill="url(#demo-sky)"/><g class="d-glow"><ellipse cx="640" cy="150" rx="330" ry="170" fill="url(#demo-glow)"/><circle cx="640" cy="140" r="44" fill="#f8f1d8"/></g><g class="d-horizon"><path d="M-40 300Q140 205 300 270T600 250T950 235V560H-40Z" fill="#cdd5c3"/><path d="M-30 345Q150 270 330 330T650 310T950 320V560H-30Z" fill="#bac7af"/></g><path d="M-30 380Q200 350 450 360T940 375V560H-30Z" fill="#a9b99e"/><g class="d-shapes" filter="url(#demo-soft)" opacity=".55"><ellipse cx="150" cy="300" rx="110" ry="45" fill="#c9b89a"/><ellipse cx="770" cy="270" rx="120" ry="40" fill="#b7c3a7"/><ellipse cx="260" cy="470" rx="150" ry="40" fill="#93a889"/></g><g class="d-lake"><ellipse cx="450" cy="420" rx="300" ry="78" fill="url(#demo-lake)"/><g fill="none" stroke="#f3f6ef" stroke-linecap="round" opacity=".55"><path d="M330 410h120M420 432h170M300 448h90"/></g></g><g class="d-ripples" fill="none" stroke="#f6f8f2" stroke-width="2"><ellipse cx="450" cy="420" rx="60" ry="12"/><ellipse cx="450" cy="420" rx="60" ry="12"/><ellipse cx="450" cy="420" rx="60" ry="12"/></g><g class="d-mist" filter="url(#demo-soft)" fill="#f4f3ea"><ellipse cx="260" cy="380" rx="300" ry="60"/><ellipse cx="700" cy="420" rx="280" ry="55"/><ellipse cx="450" cy="300" rx="380" ry="50"/></g><path class="d-path" d="M430 560C300 548 110 525 100 450S150 360 260 330 380 282 400 262" pathLength="1" fill="none" stroke="#fbf5df" stroke-width="7" stroke-linecap="round"/><path class="d-gap" d="M590 560C582 505 592 465 620 425" fill="none" stroke="#fff6da" stroke-width="30" stroke-linecap="round" filter="url(#demo-shape)"/><g class="d-pressure" filter="url(#demo-shape)"><path d="M760 360c40-25 95-10 105 30s-25 80-75 75-70-25-75-55 10-38 45-50Z" fill="#5f5873"/><path d="M800 395c30-10 60 5 60 30s-30 40-58 32-35-50-2-62Z" fill="#4c4163" opacity=".85"/><ellipse cx="745" cy="420" rx="38" ry="24" fill="#7a7787" opacity=".8"/></g><path d="M300 560Q450 520 600 560Z" fill="#8fa287"/></svg>`;
  }
  function demoStageAttrs(scene) {
    return Object.entries(scene)
      .map(([key, value]) => `data-${key}="${value}"`)
      .join(" ");
  }
  function demoCaption() {
    if (demo.done)
      return '<p class="demo-line">The scene has settled. The walkthrough is complete.</p>';
    if (!demoRunning())
      return '<p class="demo-line">When the participant is settled, press Start. Timing is a guide, and the walkthrough itself is not saved.</p>';
    if (demo.neutral)
      return '<span class="demo-speaker">Neutral reset</span><p class="demo-line">The landscape has returned to a quiet starting point. Return to the scene only when ready.</p>';
    const step = D.steps[demo.index];
    return `<span class="demo-speaker ${step.speaker}">${step.speaker === "therapist" ? "Therapist" : "Patient · example response"}</span><p class="demo-line">“${esc(D.lineAt(demo.index, demo.declined))}”</p>`;
  }
  function demoControls() {
    if (!demoRunning())
      return demo.done
        ? `${button(icon("play") + "Restart walkthrough", "demo-restart")}`
        : `${button(icon("play") + "Start", "demo-start")}`;
    const step = D.steps[demo.index],
      hold = demo.paused || demo.neutral,
      last = D.nextIndex(demo.index, demo.declined) < 0;
    const forward = step.choice
      ? `${button("Explore the heaviness " + icon("arrow"), "demo-next", false, hold ? "disabled" : "")}${button("Stay with the lake", "demo-decline", true, hold ? "disabled" : "")}`
      : button(
          (last ? "Close the session " : "Next ") + icon("arrow"),
          "demo-next",
          false,
          hold ? "disabled" : "",
        );
    return `<div class="spaced">${button(icon("back") + "Back", "demo-back", true, hold || demo.index === 0 ? "disabled" : "")}${forward}</div><div class="spaced">${button(icon(demo.paused ? "play" : "pause") + (demo.paused ? "Resume" : "Pause"), "demo-pause", true)}${button(demo.neutral ? "Return to scene" : "Neutral reset", "demo-neutral", true, demo.paused ? "disabled" : "")}${button("End early", "demo-end", true)}</div>`;
  }
  function demoStatus() {
    const active = demoRunning() ? D.steps[demo.index].section : -1,
      section = D.sections[Math.max(0, active)],
      over = demoRunning() && demo.elapsed > section.end;
    return `<div class="demo-clock"><div><strong id="demo-clock">${clock(demo.elapsed)}</strong> <span class="subtext">elapsed · about 04:00 planned</span></div>${demo.paused ? '<span class="pill amber">Paused</span>' : ""}</div><p class="subtext">${demoRunning() ? `Target for this part: ${clock(section.start)}–${clock(section.end)}.${over ? " Running over is fine; do not rush emotionally significant material." : ""}` : "The schedule is a guide, not a reason to interrupt."}</p><ol class="demo-sections">${D.sections.map((s, i) => `<li class="${i === active ? "current" : i < active || demo.done ? "past" : ""} ${demo.declined && i === 3 ? "skipped" : ""}" ${i === active ? 'aria-current="step"' : ""}><small>${clock(s.start)}–${clock(s.end)}</small><span>${s.title}${demo.declined && i === 3 ? " · declined" : ""}</span></li>`).join("")}</ol>${active >= 0 ? `<div class="callout"><strong>Visual cue · presenter only</strong><br>${esc(section.cue)}</div>` : ""}`;
  }
  function demoStage(cls = "") {
    return `<div class="scene demo-stage ${cls} ${demo.paused ? "paused" : ""}" id="demo-stage" ${demoStageAttrs(demoScene())}>${demoArtwork()}<span class="scene-label">SCRIPTED DEMO · EXAMPLE DIALOGUE · NO AI</span></div><div class="demo-caption ${cls}" id="demo-caption" aria-live="polite">${demoCaption()}</div>`;
  }
  function demoPage() {
    return layout(
      `${head("SCRIPTED WALKTHROUGH · ABOUT 4 MINUTES", "The lake and the heavy shape.", "One example session: association, emotion, challenge, personal need and a small, self-directed step.", link("Presentation view " + icon("arrow"), "demo/present", true))}<div class="demo-grid"><section>${demoStage()}<div class="demo-controls" id="demo-controls">${demoControls()}</div><p class="demo-notice">Patient lines are fictional examples. Colors and shapes have no fixed meaning; each visual change settles within 8 seconds, well under the 30-second exploration limit, and the next waits for a deliberate click. Apart from reference notes kept in this browser, nothing is recorded or sent.</p></section><aside><div class="panel panel-pad" id="demo-status">${demoStatus()}</div><div class="panel panel-pad mt"><h2>Comfort check</h2><p class="subtext">Offer at any point. Pause, neutral reset and ending early are always available.</p>${comfort("demo-comfort")}${button("Record check-in", "demo-comfort", true)}<ul class="demo-checkins" id="demo-checkins">${demoCheckins()}</ul></div></aside></div><div id="demo-garmin">${demoGarmin()}</div>${referencesPanel("demo")}<section class="panel panel-pad mt"><h2>Facilitation notes</h2><ul class="privacy-list"><li><strong>Patient-led meaning.</strong> Ask what colors and shapes represent; do not infer emotions from color alone.</li><li><strong>No forced resolution.</strong> The heavy shape stays visible; naming a difficulty can be meaningful in itself.</li><li><strong>Clinical safety.</strong> Nothing here diagnoses or infers clinical states from speech or visual choices.</li></ul></section>`,
      "demo",
    );
  }
  function demoPresent() {
    return `<main id="main" class="client-shell demo-present" tabindex="-1"><header class="client-header">${brand()}<div class="spaced"><span class="pill amber">Scripted demo · example dialogue</span><a class="button secondary small" href="#demo">Presenter view ${icon("arrow")}</a></div></header>${demoStage("demo-large")}<div class="demo-controls" id="demo-controls">${demoControls()}</div><div class="footer-note">${icon("shield")} Fictional example · No AI, microphone or headset · Nothing is saved</div></main>`;
  }
  function demoCheckins() {
    return demo.comfort
      .map((c) => `<li>${clock(c.at)} · ${c.value ? c.value + "/5" : "Preferred not to answer"}</li>`)
      .join("");
  }
  // Simulated watch summary from synthetic FIT files (demo-garmin.js); shown once the walkthrough ends.
  function garminTile(label, metric, main, sub) {
    const ok = metric?.status === "available";
    return `<div class="device-mini">${label}<strong style="margin:6px 0 0">${ok ? esc(main(metric)) : "Not available"}</strong>${ok ? esc(sub(metric)) : ""}</div>`;
  }
  function demoGarmin() {
    const G = window.LandscapeDemoGarmin;
    if (!demo.done || !G) return "";
    const s = G.session,
      n = G.previous_night,
      rec = s.activity.recordings[0],
      signed = (v) => (v > 0 ? "+" : "") + v;
    const during = [
      garminTile("Heart rate", s.activity.heart_rate, (m) => `${Math.round(m.mean)} bpm average`, (m) => `${m.min}–${m.max} bpm`),
      garminTile("Stress · Garmin estimate", s.stress, (m) => `${m.first} → ${m.last}`, (m) => `average ${m.mean} of 100`),
      garminTile("Body Battery", s.body_battery, (m) => `${m.first}% → ${m.last}%`, (m) => `${signed(m.change)} during session`),
      garminTile("Respiration", s.respiration, (m) => `${m.mean} breaths/min`, (m) => `${m.min.toFixed(1)}–${m.max.toFixed(1)}`),
      garminTile("Activity", rec && { status: "available", ...rec }, (m) => `${m.calories_kcal} kcal`, (m) => `${m.elapsed_seconds / 60} min · ${m.sport}`),
      garminTile("Resting heart rate", s.fitness.resting_heart_rate, (m) => `${m.current_day} bpm`, () => "today"),
      garminTile("VO2 max", s.fitness.vo2_max, (m) => `${m.value}`, () => "mL/kg/min"),
      garminTile("Training effect", s.fitness.training_effect, (m) => `${m.aerobic_training_effect} aerobic`, () => "scale 0–5"),
    ];
    const night = [
      garminTile("Sleep", n.sleep, (m) => `${Math.floor(m.total_sleep_minutes / 60)} h ${Math.round(m.total_sleep_minutes % 60)} min`, (m) => `score ${m.assessment?.overall_score ?? "–"} · ${m.minutes.deep} min deep`),
      garminTile("Skin temperature", n.skin_temperature, (m) => `${signed(m.deviation_from_baseline)} °C`, () => "vs. personal baseline"),
      garminTile("HRV status", n.hrv_status, (m) => `${m.last_night_average} ms`, (m) => `${m.garmin_status} · weekly ${m.weekly_average} ms`),
    ];
    return `<section class="panel panel-pad mt"><div class="section-head"><h2>End-of-session watch summary</h2><span class="badge">SIMULATED GARMIN DATA</span></div><p class="subtext">Read from synthetic FIT files that stand in for the transfer from the watch after a ${G.session_window.minutes}-minute recording. No watch or person was measured. These are device-style estimates, not emotional or clinical assessments.</p><span class="eyebrow">DURING THE SESSION</span><div class="device-summary">${during.join("")}</div><span class="eyebrow" style="display:block;margin-top:18px">THE NIGHT BEFORE</span><div class="device-summary">${night.join("")}</div></section>`;
  }
  function updateDemo() {
    const stage = $("#demo-stage");
    if (!stage) return;
    if ($("#demo-garmin")) $("#demo-garmin").innerHTML = demoGarmin();
    Object.assign(stage.dataset, demoScene());
    stage.classList.toggle("paused", demo.paused);
    $("#demo-caption").innerHTML = demoCaption();
    $("#demo-controls").innerHTML = demoControls();
    if ($("#demo-status")) $("#demo-status").innerHTML = demoStatus();
    if ($("#demo-checkins")) $("#demo-checkins").innerHTML = demoCheckins();
  }
  function demoAction(action) {
    if (action === "demo-start" || action === "demo-restart") {
      Object.assign(demo, {
        index: 0,
        declined: false,
        paused: false,
        neutral: false,
        done: false,
        elapsed: 0,
        comfort: [],
      });
    }
    if (action === "demo-comfort")
      demo.comfort.push({ at: demo.elapsed, value: $("#demo-comfort")?.value || "" });
    if (!demoRunning()) return updateDemo();
    const hold = demo.paused || demo.neutral;
    if ((action === "demo-next" || action === "demo-decline") && !hold) {
      if (action === "demo-decline") demo.declined = true;
      const next = D.nextIndex(demo.index, demo.declined);
      if (next < 0) demo.done = true;
      else demo.index = next;
    }
    if (action === "demo-back" && !hold && demo.index > 0) {
      demo.index = Math.max(0, D.previousIndex(demo.index, demo.declined));
      // Returning to the invitation offers the choice again.
      if (D.steps[demo.index].choice) demo.declined = false;
    }
    if (action === "demo-pause") demo.paused = !demo.paused;
    if (action === "demo-neutral" && !demo.paused) demo.neutral = !demo.neutral;
    if (action === "demo-end") {
      demo.done = true;
      demo.paused = demo.neutral = false;
    }
    updateDemo();
  }
  document.addEventListener("click", (e) => {
    const target = e.target.closest("[data-action^='demo-']");
    if (target && !target.disabled) demoAction(target.dataset.action);
  });
  document.addEventListener("keydown", (e) => {
    if (!$("#demo-stage") || e.target.closest("input,textarea,select,button"))
      return;
    if (e.key === "ArrowRight")
      demoAction(demoRunning() ? "demo-next" : "demo-start");
    if (e.key === "ArrowLeft") demoAction("demo-back");
  });
  setInterval(() => {
    if (!demoRunning() || demo.paused || document.hidden) return;
    demo.elapsed++;
    if ($("#demo-clock")) $("#demo-clock").textContent = clock(demo.elapsed);
    if ($("#demo-status") && demo.elapsed === D.sections[D.steps[demo.index].section].end + 1)
      $("#demo-status").innerHTML = demoStatus();
  }, 1000);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden && demoRunning() && !demo.paused) {
      demo.paused = true;
      updateDemo();
    }
  });
  function notFound() {
    return layout(
      '<div class="panel empty"><h1>This page is not here.</h1><p>The session may have been cleared from this browser.</p><a class="button" href="#overview">Back to overview</a></div>',
      "overview",
    );
  }
  let renderedPath = "";
  function render() {
    const preserved = {};
    const focusId = document.activeElement?.id;
    const selection = document.activeElement?.selectionStart;
    const studio =
      renderedPath === location.hash
        ? document.querySelector("#media-studio")?.innerHTML
        : null;
    if (renderedPath === location.hash)
      for (const field of document.querySelectorAll(
        "textarea[id],input[id],select[id]",
      )) {
        preserved[field.id] = { value: field.value, checked: field.checked };
      }
    const [page, id] = (location.hash.slice(1) || "overview").split("/");
    window.LandscapeGarmin?.reconcile(current(), ["session", "client-session"].includes(page) && current()?.id === id && !document.hidden);
    const views = {
      overview,
      clients: clientsPage,
      profile: () => profilePage(id),
      prepare: () => preparePage(id),
      sessions: sessionsPage,
      session: () => sessionPage(id),
      review: () => reviewPage(id),
      notes: notesPage,
      settings: settingsPage,
      client: () => clientWelcome(id),
      "client-session": () => clientSession(id),
      demo: () => (id === "present" ? demoPresent() : demoPage()),
    };
    $("#app").innerHTML = (views[page] || notFound)();
    if (studio && document.querySelector("#media-studio"))
      document.querySelector("#media-studio").innerHTML = studio;
    renderedPath = location.hash;
    updateGarmin();
    for (const [id, value] of Object.entries(preserved)) {
      const field = document.getElementById(id);
      if (field) {
        field.value = typeof value === "object" ? value.value : value;
        if (typeof value === "object" && field.type === "checkbox")
          field.checked = value.checked;
      }
    }
    if (focusId && document.getElementById(focusId)) {
      const focused = document.getElementById(focusId);
      focused.focus({ preventScroll: true });
      if (typeof selection === "number" && focused.setSelectionRange)
        try {
          focused.setSelectionRange(selection, selection);
        } catch {}
    }
    document.title =
      "Inner Landscape · " +
      ({
        overview: "Overview",
        clients: "Clients",
        profile: "Client profile",
        prepare: "Session preparation",
        sessions: "Sessions",
        session: "Live session",
        review: "Session review",
        notes: "Notes",
        settings: "Settings",
        client: "Client welcome",
        "client-session": "Client reflection",
        demo: "Guided demo",
      }[page] || "Workspace");
  }
  function event(s, type, text) {
    s.events.push({ type, text, at: new Date().toISOString() });
  }
  document.addEventListener("click", (e) => {
    const target = e.target.closest("[data-action]");
    if (!target || target.disabled) return;
    const action = target.dataset.action,
      s = byId(target.dataset.id) || current();
    if (action === "select" && s) {
      if (S.select(s, target.dataset.region)) {
        save();
        render();
      }
    }
    if (action === "pause" && s) {
      const paused = s.status === "active";
      if (paused ? S.pause(s) : S.resume(s)) {
        event(s, "control", paused ? "Session paused" : "Session resumed");
        save();
        render();
      }
    }
    if (action === "next" && s) {
      if (S.next(s)) {
        save();
        render();
      }
    }
    if (action === "finish" && s) {
      S.finish(s);
      event(s, "control", "Session finished");
      save();
      const clientMode = location.hash.startsWith("#client-session/");
      location.hash = (clientMode ? "client-session/" : "review/") + s.id;
      render();
    }
    if (action === "save-profile") {
      const c = client(target.dataset.client);
      data.notes[c.id] = $("#profile-note").value;
      save();
      toast(
        storageAvailable
          ? "Demo note saved locally."
          : "Note is kept in memory only.",
      );
    }
    if (
      action === "clear" &&
      confirm(
        "Remove all saved Inner Landscape demo sessions and notes from this browser? This cannot be undone.",
      )
    ) {
      data = S.fresh();
      save();
      referenceNotes = {};
      try {
        localStorage.removeItem(NOTES_KEY);
      } catch {
        // Nothing stored to remove.
      }
      render();
      toast("Saved demo data cleared.");
    }
  });
  document.addEventListener("input", (e) => {
    if (e.target.id === "client-search")
      $("#client-grid").innerHTML = clientCards(e.target.value);
  });
  document.addEventListener("submit", (e) => {
    const form = e.target;
    if (
      ![
        "prepare-form",
        "reflection-form",
        "session-note",
        "review-form",
        "client-start",
        "client-checkout",
      ].includes(form.id)
    )
      return;
    e.preventDefault();
    const values = Object.fromEntries(new FormData(form));
    if (form.id === "prepare-form" || form.id === "client-start") {
      if (current()) {
        toast("Finish the current session first.");
        return;
      }
      const c = client(values.clientId);
      let s;
      try {
        s = S.create(c.id, {
          ...values,
          goal: values.goal || c.focus,
          consent: !!values.consent,
        });
      } catch (err) {
        toast(err.message);
        return;
      }
      data.sessions.push(s);
      save();
      location.hash =
        (form.id === "client-start" ? "client-session/" : "session/") + s.id;
    }
    const s = byId(form.dataset.id);
    if (form.id === "reflection-form" && s) {
      if (S.reflect(s, values.reflection || "")) {
        form.reset();
        save();
        render();
        $("#reflection")?.focus();
      } else
        toast("Resume the session or begin the next cycle before reflecting.");
    }
    if (form.id === "session-note" && s) {
      const text = (values.note || "").trim();
      if (text) {
        event(s, "note", text);
        form.reset();
        save();
        render();
        toast("Observation added to the timeline.");
      }
    }
    if (form.id === "review-form" && s) {
      s.postNotes = values.postNotes || "";
      s.after = values.after || "";
      s.approved = !!values.approved;
      save();
      render();
      toast("Demo review saved.");
    }
    if (form.id === "client-checkout" && s) {
      s.after = values.after || "";
      save();
      toast("Check-in saved.");
    }
  });
  window.addEventListener("hashchange", () => {
    render();
    window.scrollTo(0, 0);
    $("#main")?.focus({ preventScroll: true });
  });
  // Ticks update only the countdown. Typing and draft notes are never overwritten.
  setInterval(() => {
    const s = current();
    const path = location.hash.slice(1).split("/");
    if (
      !s ||
      !["session", "client-session"].includes(path[0]) ||
      path[1] !== s.id ||
      document.hidden
    )
      return;
    if (s.driver === "unity") return;
    if (S.tick(s)) {
      save();
      if ($("#remaining"))
        $("#remaining").textContent = String(s.remaining).padStart(2, "0");
      if ($("#cycle-progress"))
        $("#cycle-progress").style.width =
          ((30 - s.remaining) / 30) * 100 + "%";
      if (s.pendingCycle) {
        const draft = $("#reflection")?.value || "",
          note = $("#moment-note")?.value || "";
        render();
        if ($("#reflection")) $("#reflection").value = draft;
        if ($("#moment-note")) $("#moment-note").value = note;
        toast(
          "This exploration window is complete. Continue when you are ready.",
        );
      }
    }
  }, 1000);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      const s = current();
      if (s && S.pause(s)) {
        event(s, "control", "Paused when browser tab became inactive");
        save();
        render();
      }
    }
  });
  window.addEventListener("beforeunload", () => {
    const s = current();
    if (s && S.pause(s)) save();
  });
  render();

  document.addEventListener("click", async (e) => {
    const target = e.target.closest("[data-action]");
    if (!target || target.disabled) return;
    const s = byId(target.dataset.id);
    if (!s) return;
    try {
      if (target.dataset.action === "garmin-scan") await window.LandscapeGarmin.scan();
      if (target.dataset.action === "garmin-connect") await window.LandscapeGarmin.start(s.id, $("#garmin-device").value, $("#garmin-consent").checked);
      if (target.dataset.action === "garmin-stop") await window.LandscapeGarmin.stop();
      if (target.dataset.action === "pair") {
        await window.LandscapeBackend.scene(s.id, await captureScene());
        const result = await window.LandscapeBackend.pair(s.id);
        toast("Unity pairing code: " + result.code + " (valid 2 minutes)");
        const msg = document.querySelector("#connection-message");
        if (msg)
          msg.textContent =
            "Pairing code: " + result.code + " · expires in 2 minutes";
      }
      if (target.dataset.action === "voice") {
        if (window.LandscapeVoice.active) await window.LandscapeVoice.stop();
        else {
          if (
            !confirm(
              "Start the paid voice guide? Microphone audio and conversation will be processed by ElevenLabs. Use fictional demo content only.",
            )
          )
            return;
          await window.LandscapeBackend.flush();
          await window.LandscapeVoice.start(s.id, toast);
        }
        render();
      }
      if (target.dataset.action === "media-studio") await openMedia(s);
      if (target.dataset.action === "apply-media")
        await window.LandscapeBackend.apply(s.id, target.dataset.job);
      if (["pause", "finish"].includes(target.dataset.action))
        await window.LandscapeVoice.stop();
      if (target.dataset.action === "select") window.LandscapeVoice.update();
    } catch (error) {
      toast(error.message);
    }
  });
  document.addEventListener("submit", async (e) => {
    if (e.target.id !== "media-form") return;
    e.preventDefault();
    const form = e.target,
      values = Object.fromEntries(new FormData(form)),
      s = byId(form.dataset.id);
    const submit = form.querySelector(
      'button[type="submit"],button:not([type])',
    );
    if (submit) submit.disabled = true;
    try {
      const image = await captureScene();
      await window.LandscapeBackend.generate(s.id, {
        image,
        brief: values.brief,
        kind: values.kind,
      });
      toast("Generation queued. The existing scene stays in place.");
      await openMedia(s);
    } catch (error) {
      toast(error.message);
      if (submit) submit.disabled = false;
    }
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) window.LandscapeVoice?.stop();
  });
  window.LandscapeBackend?.start(
    data,
    (workspace) => {
      data = workspace;
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
      } catch {}
      const active = current();
      if (!active || active.status !== "active") window.LandscapeVoice?.stop();
      render();
    },
    (message) => {
      toast(message);
      render();
    },
  );

  document.addEventListener(
    "click",
    async (e) => {
      const target = e.target.closest("[data-action]"),
        backend = window.LandscapeBackend;
      if (
        !target ||
        target.disabled ||
        !backend?.connected ||
        !["pause", "finish", "select", "next"].includes(target.dataset.action)
      )
        return;
      const s = byId(target.dataset.id) || current();
      if (!s) return;
      e.preventDefault();
      e.stopImmediatePropagation();
      try {
        let name = target.dataset.action,
          payload = {};
        if (name === "pause") {
          name = s.status === "paused" ? "resume" : "pause";
          await window.LandscapeGarmin.stop();
          await window.LandscapeVoice.stop();
        }
        if (name === "finish") {
          name = "stop";
          await window.LandscapeGarmin.stop();
          await window.LandscapeVoice.stop();
        }
        if (name === "select") payload = { region: target.dataset.region };
        await backend.command(s.id, name, payload);
        if (name === "stop")
          location.hash =
            (location.hash.startsWith("#client-session/")
              ? "client-session/"
              : "review/") + s.id;
        window.LandscapeVoice.update();
      } catch (error) {
        toast(error.message);
      }
    },
    true,
  );
})();
