from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BandParticipant:
    role: str
    participant_id: str
    display_name: str


@dataclass
class BandConfig:
    enabled: bool
    agent_id: str
    api_key: str
    rest_url: str
    participants: list[BandParticipant]
