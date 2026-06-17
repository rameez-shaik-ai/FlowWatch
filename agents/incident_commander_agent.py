from __future__ import annotations

import json
from typing import Any

from services.aiml_api import call_aiml_api


ALLOWED_DECISIONS = {
    "monitor_only",
    "diagnose",
    "self_heal",
    "customer_care",
    "escalate",
}
ALLOWED_SEVERITIES = {"Low", "Medium", "High", "Critical"}
ALLOWED_HEALING_ACTIONS = {
    "restart_streaming_app",
    "refresh_streaming_session",
    "retry_playback",
    "none",
}
KNOWN_AGENTS = {
    "Diagnosis Agent",
    "Recovery Action Agent",
    "Customer Care Agent",
}


def _extract_json_payload(text: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        payload = json.loads(text[start : end + 1])
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        return None


def _normalize_commander_decision(payload: dict[str, Any]) -> dict[str, Any]:
    decision = str(payload.get("decision", "monitor_only"))
    if decision not in ALLOWED_DECISIONS:
        decision = "monitor_only"

    severity = str(payload.get("severity", "Low")).title()
    if severity not in ALLOWED_SEVERITIES:
        severity = "Low"

    agents_to_run = [
        str(agent)
        for agent in payload.get("agents_to_run", [])
        if str(agent) in KNOWN_AGENTS
    ]

    healing_action = str(payload.get("recommended_healing_action", "none"))
    if healing_action not in ALLOWED_HEALING_ACTIONS:
        healing_action = "none"

    return {
        "agent": "Incident Commander Agent",
        "decision": decision,
        "severity": severity,
        "band_room_required": bool(payload.get("band_room_required", False)),
        "agents_to_run": agents_to_run,
        "customer_care_required": bool(payload.get("customer_care_required", False)),
        "human_approval_required": bool(payload.get("human_approval_required", False)),
        "recommended_healing_action": healing_action,
        "reason": str(payload.get("reason", "Commander decision unavailable.")),
        "next_step": str(payload.get("next_step", "Continue monitoring.")),
    }


def fallback_incident_commander_decision(
    telemetry: dict[str, Any],
    qoe_result: dict[str, Any],
    playback_impact: dict[str, Any] | None,
) -> dict[str, Any]:
    impact_status = (playback_impact or {}).get("impact_status", "At Risk")
    qoe_status = qoe_result.get("qoe_status", "Warning")

    if impact_status == "Stable":
        return {
            "agent": "Incident Commander Agent",
            "decision": "monitor_only",
            "severity": "Low",
            "band_room_required": False,
            "agents_to_run": [],
            "customer_care_required": False,
            "human_approval_required": False,
            "recommended_healing_action": "none",
            "reason": "Playback is stable and no specialist escalation is required.",
            "next_step": "Continue monitoring the session.",
        }
    if impact_status == "Critical" or qoe_status == "Poor":
        return {
            "agent": "Incident Commander Agent",
            "decision": "escalate",
            "severity": "Critical",
            "band_room_required": True,
            "agents_to_run": [
                "Diagnosis Agent",
                "Recovery Action Agent",
                "Customer Care Agent",
            ],
            "customer_care_required": True,
            "human_approval_required": True,
            "recommended_healing_action": "restart_streaming_app",
            "reason": "Critical playback disruption requires recovery, oversight, and communication.",
            "next_step": "Run the full workflow with human oversight.",
        }
    if impact_status == "At Risk":
        return {
            "agent": "Incident Commander Agent",
            "decision": "monitor_only",
            "severity": "Medium",
            "band_room_required": False,
            "agents_to_run": [],
            "customer_care_required": False,
            "human_approval_required": False,
            "recommended_healing_action": "none",
            "reason": "Risk signals are present, but playback impact is not confirmed.",
            "next_step": "Keep monitoring for sustained degradation.",
        }
    if impact_status == "Impact Confirmed":
        return {
            "agent": "Incident Commander Agent",
            "decision": "self_heal",
            "severity": "High",
            "band_room_required": True,
            "agents_to_run": ["Diagnosis Agent", "Recovery Action Agent"],
            "customer_care_required": False,
            "human_approval_required": True,
            "recommended_healing_action": "restart_streaming_app",
            "reason": "Playback impact is confirmed and safe recovery should be prepared.",
            "next_step": "Run diagnosis and recovery, then request restart approval.",
        }
    return {
        "agent": "Incident Commander Agent",
        "decision": "diagnose",
        "severity": "High",
        "band_room_required": True,
        "agents_to_run": ["Diagnosis Agent"],
        "customer_care_required": False,
        "human_approval_required": False,
        "recommended_healing_action": "none",
        "reason": f"Fallback routing selected based on {impact_status} playback impact.",
        "next_step": "Run diagnosis to collect more incident evidence.",
    }


def incident_commander_agent(
    telemetry: dict[str, Any],
    qoe_result: dict[str, Any],
    playback_impact: dict[str, Any] | None,
    model_name: str,
) -> dict[str, Any]:
    system_prompt = (
        "You are the Incident Commander Agent in an autonomous telecom TV streaming incident workflow. "
        "Decide the safest next action for the session. "
        "Return JSON only with keys: agent, decision, severity, band_room_required, agents_to_run, "
        "customer_care_required, human_approval_required, recommended_healing_action, reason, next_step. "
        "Valid decision values: monitor_only, diagnose, self_heal, customer_care, escalate. "
        "Valid severity values: Low, Medium, High, Critical. "
        "Valid healing actions: restart_streaming_app, refresh_streaming_session, retry_playback, none. "
        "Do not include markdown or commentary outside the JSON object. "
        "Use these rules: Stable->monitor_only Low no Band. At Risk->monitor_only Medium no Band. "
        "Impact Confirmed->self_heal High with Diagnosis Agent and Recovery Action Agent, Band required, approval required. "
        "Critical->escalate Critical with Diagnosis Agent, Recovery Action Agent, Customer Care Agent, Band required, approval required."
    )
    user_prompt = json.dumps(
        {
            "telemetry": telemetry,
            "qoe_result": qoe_result,
            "playback_impact": playback_impact,
            "current_incident_context": {
                "source_mode": telemetry.get("source_mode", "unknown"),
                "customer_id": telemetry.get("customer_id"),
                "device_id": telemetry.get("device_id"),
            },
        },
        indent=2,
    )
    response = call_aiml_api(system_prompt, user_prompt, model_name)
    if response.startswith("Error:") or response.startswith("HTTP error") or response.startswith(
        "Request error"
    ):
        return fallback_incident_commander_decision(telemetry, qoe_result, playback_impact)

    payload = _extract_json_payload(response)
    if payload is None:
        return fallback_incident_commander_decision(telemetry, qoe_result, playback_impact)
    return _normalize_commander_decision(payload)
