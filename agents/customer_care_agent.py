from __future__ import annotations

import json
from typing import Any

from services.aiml_api import call_aiml_api


def customer_care_agent(
    telemetry: dict[str, Any],
    diagnosis_text: str,
    recovery_text: str,
    model_name: str,
) -> str:
    system_prompt = (
        "You are the Customer Care Agent for a telecom TV streaming service. "
        "Generate a non-technical customer-friendly message, an internal support ticket summary, "
        "a priority level, and a recommended next step. Do not expose QoE score, packet loss, "
        "CDN, internal agent names, backend details, or technical root cause wording to the "
        "customer-facing message. Respond with concise markdown using the headings: Customer "
        "Message, Internal Support Ticket, Priority Level, and Recommended Next Step."
    )
    user_prompt = (
        "Create the communication outputs based on the telemetry, diagnosis, and recovery plan.\n\n"
        f"Telemetry:\n{json.dumps(telemetry, indent=2)}\n\n"
        f"Diagnosis:\n{diagnosis_text}\n\n"
        f"Recovery plan:\n{recovery_text}"
    )
    return call_aiml_api(system_prompt, user_prompt, model_name)
