"""Small compatibility boundary for ElevenLabs conversational transcript events."""


def transcript(item: dict) -> tuple[str, str] | None:
    kind = item.get('type')
    if kind == 'user_transcript':
        body = item.get('user_transcription_event', item.get('user_transcript_event', {}))
        text = body.get('user_transcript', '')
        role = 'reflection'
    elif kind == 'agent_response':
        text = item.get('agent_response_event', {}).get('agent_response', '')
        role = 'guide'
    else:
        return None
    return (role, text[:2000]) if isinstance(text, str) and text.strip() else None
