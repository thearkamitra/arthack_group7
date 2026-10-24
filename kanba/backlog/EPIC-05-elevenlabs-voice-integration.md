# EPIC-05: ElevenLabs Real-Time Voice Guide Live Testing & Audio Pipeline

- **ID**: `EPIC-05`
- **Milestone Reference**: Milestone 5 (AI guide)
- **Status**: Queued; paid approval recorded; live acceptance in progress under EPIC-08 ([NEEDME-01](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/done/NEEDME-01-paid-api-approval.md))
- **Primary Owner**: Backend / AI Engineer
- **Relevant Files**:
  - [backend/inner_landscape/agent.py](file:///Users/arkamitra/Documents/ChatGPT/arthack/backend/inner_landscape/agent.py)
  - [backend/inner_landscape/api.py](file:///Users/arkamitra/Documents/ChatGPT/arthack/backend/inner_landscape/api.py)
  - [frontend/voice.js](file:///Users/arkamitra/Documents/ChatGPT/arthack/frontend/voice.js)
  - [docs/BACKEND.md](file:///Users/arkamitra/Documents/ChatGPT/arthack/docs/BACKEND.md#L31-L66)

---

## 1. Objective & Scope

Establish live, low-latency conversational audio between the client (via browser microphone or Unity headset) and the configured ElevenLabs conversational reflection agent. The guide speaks calmly, asks one concise non-leading question at a time, respects silence, and handles speech interruptions gracefully.

### Critical Constraints
- **Explicit Approval for Paid API**: Paid speech tests require user approval and running the server with `--enable-paid`. Never initiate unapproved billable voice sessions.
- **Privacy & Prompt Boundary**: Only send bounded contextual updates (confirmed region, dwell summary, therapist session constraints) at conversation boundaries. **Never send raw head-pose samples, private therapist pre/post notes, or client clinical assessments to ElevenLabs.**
- **Audio Consent & Control**: Microphones must never record automatically. Require an explicit "Start Voice" button click with microphone permission. Pausing or stopping the session must immediately terminate voice capture and playback.
- **No Diagnostic Claims**: The AI guide facilitates reflective exploration; it must not offer diagnoses, medical interpretations, or therapeutic prescriptions.

---

## 2. Current Implementation State

- **Agent Provisioning**: The private reflection agent was created and verified with the official ElevenLabs SDK using the English Flash v2 model ([backend/inner_landscape/agent.py](file:///Users/arkamitra/Documents/ChatGPT/arthack/backend/inner_landscape/agent.py)). Agent metadata is stored locally in `work/elevenlabs-agent.json`.
- **Coordinator Audio Bridge**: [backend/inner_landscape/api.py](file:///Users/arkamitra/Documents/ChatGPT/arthack/backend/inner_landscape/api.py) implements the PCM16 / 16kHz WebSocket bridge connecting the client to the ElevenLabs Conversational AI WebSocket endpoint.
- **Client Audio Capture**: [frontend/voice.js](file:///Users/arkamitra/Documents/ChatGPT/arthack/frontend/voice.js) implements browser AudioContext resampling and binary PCM streaming.
- **Pending**: Actual end-to-end paid voice stream execution, measuring acoustic latency, echo cancellation, and verifying conversational turn-taking quality.

---

## 3. Tasks & Stories

- [ ] **Task 5.1 — Paid Service Gate Activation**:
  - Obtain user sign-off for paid speech testing budget ([NEEDME-01](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/done/NEEDME-01-paid-api-approval.md)).
  - Launch coordinator with `bash backend/scripts/run.sh --enable-paid`.
- [ ] **Task 5.2 — WebSocket Audio Bridge Verification**:
  - Connect browser client to `/api/v1/sessions/{session_id}/voice/ws`.
  - Verify handshake with ElevenLabs WebSocket endpoint using server-side API key.
  - Test bidirectional PCM16/16kHz streaming (browser mic ➔ coordinator ➔ ElevenLabs ➔ coordinator ➔ browser speaker).
- [ ] **Task 5.3 — Conversational Prompt & Context Dynamics**:
  - Verify opening turn: guide opens with a calm prompt (e.g., *"Take a moment to look around. What draws your attention?"*).
  - Test contextual update: when the client confirms a region (`ridge`), verify coordinator pushes bounded context JSON (`current_region`, `dwell_summary`) to the agent WebSocket.
  - Verify follow-up question references the confirmed region appropriately.
- [ ] **Task 5.4 — Interruption & Pause Handling**:
  - Test client speaking while the guide is speaking: verify ElevenLabs interruption event stops playback immediately and resets the audio buffer.
  - Test session pause / tab hiding: verify voice capture stops immediately and audio socket disconnects cleanly.
- [ ] **Task 5.5 — Latency & Acoustic Quality Measurement**:
  - Measure round-trip audio latency (client speech end to guide speech start). Target: < 1.5 seconds.
  - Verify absence of echo loops when using open laptop speakers or headset headphones.

---

## 4. Acceptance Criteria

1. Voice connection establishes in < 2 seconds over loopback WebSocket.
2. Guide speaks with calm, natural pacing and asks single, short, non-leading questions.
3. Client interruption cuts off guide audio playback in < 400ms without pops or artifacts.
4. Pausing or stopping the session immediately silences audio and stops microphone capture.
5. Zero private notes or clinical assessment data transmitted in WebSocket payloads.
