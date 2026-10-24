# API setup

The local frontend and Lovable demo currently use no external APIs. Creating keys
alone does not connect them. Integration work will read the following variables
on the backend; never embed them in browser code or prefix secrets with VITE_.

## Local Mac

A local `.env` has been prepared at the repository root and is ignored by Git.
Open it locally in an editor and fill:

```dotenv
FAL_KEY=your_fal_key
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_AGENT_ID=your_agent_id
```

The future backend must explicitly load this file; the HTML sketch cannot read it.
No SDKs or environment replacements are required just to store the keys.

## fal.ai

1. Sign in at https://fal.ai/dashboard.
2. Open API Keys (https://fal.ai/dashboard/keys), create a named key for this
   project, selecting API scope rather than admin scope when available.
3. Copy it directly into local `.env` as FAL_KEY. Check available credits in the
   dashboard before generation. Do not paste the key into chat or GitHub.

## ElevenLabs

1. Sign in at https://elevenlabs.io/app.
2. Open Developers, then API Keys, and create a named, restricted project key.
3. Enable permissions needed for Agents/conversations. Enable text-to-speech
   separately only if using that endpoint; set a credit limit where available.
4. Put the key in local `.env` as ELEVENLABS_API_KEY.
5. Agent creation is pending. During implementation, create the reflection guide
   in Agents, configure its voice, opening question and instructions, and copy
   its ID into ELEVENLABS_AGENT_ID. This ID is not another API key. Leave it
   unset until the agent exists.
6. Integration should obtain short-lived conversation credentials server-side
   rather than putting the permanent API key in the browser.

## Lovable hosting

Lovable is the frontend builder/host; no Lovable API key is needed for the current
published demo. Local `.env` values do not transfer to the hosted frontend.
If we later use Lovable's backend, add FAL_KEY and ELEVENLABS_API_KEY through its
secure project secret form (Backend / Secrets). Agent ID is configuration, not a
secret, but may also be kept server-side. Keep all paid provider calls behind a
backend with access and usage controls before enabling them on a shared URL.
Alternatively, keep the Python backend and configure the deployed frontend with
its HTTPS endpoint after that backend is hosted.

## Provider references

- https://docs.fal.ai/model-apis/authentication
- https://elevenlabs.io/docs/help-center/technical/how-do-i-authorize-myself-using-an-api-key
- https://elevenlabs.io/docs/eleven-agents/quickstart/
- https://docs.lovable.dev/features/secrets

Never commit secrets. Only `.env.example` with blank placeholders is tracked.
