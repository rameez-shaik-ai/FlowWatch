from __future__ import annotations

import json
from typing import Any

from services.aiml_api import call_aiml_api


def recovery_action_agent(
    telemetry: dict[str, Any],
    diagnosis_text: str,
    model_name: str,
) -> str:
    system_prompt = (
        "You are the Recovery Action Agent for a telecom TV streaming service. "
        "Recommend only safe automated recovery actions. Prefer these actions when appropriate: "
        "Refresh streaming session, Retry playback session, Adjust adaptive bitrate profile, "
        "Switch to alternative CDN route if CDN issue is suspected, Restart TV app session on "
        "set-top box, Clear temporary session/cache state, Continue monitoring after action. "
        "Do not suggest billing or account changes, manual router configuration, technician "
        "dispatch as a first step, large network configuration changes, or actions that could "
        "impact many customers. Respond with concise markdown using the headings: Recommended "
        "Actions, Why These Are Safe, Automation Order, and Monitoring Plan."
    )
    user_prompt = (
        "Given the telemetry and diagnosis below, recommend safe recovery actions.\n\n"
        f"Telemetry:\n{json.dumps(telemetry, indent=2)}\n\n"
        f"Diagnosis:\n{diagnosis_text}"
    )
    return call_aiml_api(system_prompt, user_prompt, model_name)
