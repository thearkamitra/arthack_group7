# NEEDME-01: Paid API Test Approval

- **ID**: `NEEDME-01`
- **Status**: Done
- **Owner**: Codex
- **Scope**: Record the user's authorization; live integration acceptance stays with EPIC-05 and EPIC-06.

The user explicitly authorized API credit use on 2026-10-24 and then approved
implementation. No further budget approval is needed for bounded demo tests.

Verification: agent signed URL returned successfully; a single ElevenLabs Flash v2
speech request produced a 45,600-byte MP3, decoded by ffprobe as 2.786395 seconds.
Local evidence: `work/coordinator/checks/1792854084906670000/manifest.json` (ignored).
No API keys or signed URLs were printed or committed.

This closes authorization only. Conversational streaming on Quest, fal image/video
validation and in-headset media comfort remain separate acceptance checks. The
coordinator keeps its explicit `--enable-paid` switch and four-job session limit.
