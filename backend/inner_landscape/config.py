from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    fal_key: str = ""
    eleven_key: str = ""
    agent_id: str = ""
    paid_enabled: bool = False
    image_model: str = "fal-ai/flux-kontext/dev"
    video_model: str = "fal-ai/kling-video/v2.5-turbo/standard/image-to-video"
    max_jobs: int = 4

    @property
    def work(self) -> Path:
        return self.root / "work" / "coordinator"

    @classmethod
    def load(cls) -> Settings:
        # Never print these values. Process env wins. CLI voice key takes precedence
        # over the manual voice key; fal uses the manual file first.
        manual = dotenv_values(ROOT / ".env")
        cli = dotenv_values(ROOT / ".env.local")

        def value(name: str, voice: bool = False) -> str:
            first, second = (cli, manual) if voice else (manual, cli)
            return os.environ.get(name) or first.get(name) or second.get(name) or ""

        agent = value("ELEVENLABS_AGENT_ID", True)
        if not agent:
            try:
                agent = json.loads(
                    (ROOT / "work" / "elevenlabs-agent.json").read_text()
                )["agent_id"]
            except (OSError, ValueError, KeyError):
                pass
        return cls(
            fal_key=value("FAL_KEY"),
            eleven_key=value("ELEVENLABS_API_KEY", True),
            agent_id=agent,
            paid_enabled=os.getenv("INNER_LANDSCAPE_ENABLE_PAID", "") == "1",
        )
