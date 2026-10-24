# NEEDME-01: Paid API Test Approval & Budget Authorization

- **ID**: `NEEDME-01`
- **Blocks**: [EPIC-05: ElevenLabs Voice](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/backlog/EPIC-05-elevenlabs-voice-integration.md), [EPIC-06: fal.ai Media Studio](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/backlog/EPIC-06-fal-media-pipeline.md)
- **Status**: Waiting on User Authorization
- **Action Required From**: User / Budget Owner

---

## What is Needed from You

To prevent accidental charges, the Mac coordinator service disables paid API calls by default. Per the project conventions in [AGENTS.md](file:///Users/arkamitra/Documents/ChatGPT/arthack/AGENTS.md) and [PLAN.md](file:///Users/arkamitra/Documents/ChatGPT/arthack/PLAN.md), paid speech and media tests require your explicit approval.

### 1. Cost & Usage Estimates
- **ElevenLabs Conversational AI**:
  - Model: English Flash v2 (agent ID in `work/elevenlabs-agent.json`).
  - Standard conversation test (~1–2 minutes): ~ $0.10–$0.20.
- **fal.ai Generative Media**:
  - `fal-ai/flux-kontext/dev` (image inpainting edit): ~ $0.025 / megapixel (~ $0.03 per image).
  - `fal-ai/kling-video/v2.5-turbo/standard/image-to-video` (5-second silent video clip): $0.042 / second (~ $0.21 per video).
  - Estimated per-test cost (1 still + 1 video): ~ $0.25.
  - Enforced session limit: maximum 4 generation jobs per session.

### 2. How to Approve & Run
When you are ready to authorize a bounded test run:
1. Ensure your API keys are in `.env` or `.env.local` (`ELEVENLABS_API_KEY` and `FAL_KEY`).
2. Start the coordinator with the `--enable-paid` flag:
   ```bash
   bash backend/scripts/run.sh --enable-paid
   ```
3. Once approved and tested, move this card to `kanba/done/` and proceed with [EPIC-05](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/backlog/EPIC-05-elevenlabs-voice-integration.md) and [EPIC-06](file:///Users/arkamitra/Documents/ChatGPT/arthack/kanba/backlog/EPIC-06-fal-media-pipeline.md).
