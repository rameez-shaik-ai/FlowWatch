from __future__ import annotations

import json
from typing import Any

from services.aiml_api import call_aiml_api


def diagnosis_agent(
    telemetry: dict[str, Any], qoe_result: dict[str, Any], model_name: str
) -> str:
    system_prompt = (
        "You are the Diagnosis Agent in a telecom TV streaming QoE monitoring workflow. "
        "Diagnose the most likely root cause using only these categories: "
        "Network congestion, Wi-Fi / home network issue, Set-top box or device issue, "
        "TV streaming app issue, CDN / content delivery issue, Backend platform issue, "
        "Unknown / needs human investigation. Respond with concise markdown using the "
        "headings: Likely Root Cause, Why, Confidence, Evidence Used, and Suggested "
        "Validation Checks."
    )
    user_prompt = (
        "Analyze this telemetry and QoE summary, then diagnose the most likely root cause.\n\n"
        f"Telemetry:\n{json.dumps(telemetry, indent=2)}\n\n"
        f"QoE summary:\n{json.dumps(qoe_result, indent=2)}"
    )
    return call_aiml_api(system_prompt, user_prompt, model_name)
