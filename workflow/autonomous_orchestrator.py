from __future__ import annotations

from typing import Any


def is_self_healing_eligible(
    *,
    source_config: dict[str, Any],
    telemetry: dict[str, Any],
    qoe_preview: dict[str, Any],
    playback_impact: dict[str, Any] | None,
    commander_decision: dict[str, Any],
) -> bool:
    action = commander_decision.get("recommended_healing_action", "none")
    if action == "none":
        return False
    if not commander_decision.get("human_approval_required", False):
        return False
    if commander_decision.get("decision") not in {"self_heal", "escalate"}:
        return False

    mode = source_config.get("mode")
    if mode == "Manual":
        return qoe_preview.get("qoe_status") == "Poor"

    if mode == "Embedded HLS player":
        impact_confirmed = (
            playback_impact is not None
            and playback_impact.get("impact_status") in {"Impact Confirmed", "Critical"}
        )
        if not impact_confirmed:
            return False
        scenario = source_config.get("player_scenario")
        if scenario == "Live":
            return qoe_preview.get("qoe_status") in {"Poor", "Warning"}
        if scenario == "Degraded":
            return True
        return False

    return False


def should_run_agent(commander_decision: dict[str, Any], agent_name: str) -> bool:
    agents = commander_decision.get("agents_to_run", [])
    if agent_name == "Customer Care Agent":
        return bool(
            agent_name in agents or commander_decision.get("customer_care_required", False)
        )
    return agent_name in agents


def get_action_summary_from_commander(commander_decision: dict[str, Any]) -> dict[str, str]:
    decision = commander_decision.get("decision", "monitor_only")
    severity = commander_decision.get("severity", "Low")
    band = "Required" if commander_decision.get("band_room_required") else "Optional"

    mappings = {
        "monitor_only": {
            "title": "Monitor only",
            "detail": "Monitoring only",
        },
        "diagnose": {
            "title": "Diagnosis required",
            "detail": "Diagnosis running",
        },
        "self_heal": {
            "title": "Self-healing recommended",
            "detail": "Waiting for approval",
        },
        "customer_care": {
            "title": "Customer care required",
            "detail": "Customer care required",
        },
        "escalate": {
            "title": "Escalation required",
            "detail": "Waiting for approval",
        },
    }
    base = mappings.get(decision, mappings["monitor_only"])
    return {
        "title": base["title"],
        "detail": base["detail"],
        "priority": severity,
        "band": band,
    }
