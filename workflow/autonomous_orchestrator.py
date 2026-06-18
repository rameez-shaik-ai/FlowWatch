from __future__ import annotations

from typing import Any


def _count_severe_signals(telemetry: dict[str, Any]) -> int:
    severe_signals = 0
    if float(telemetry.get("buffering_ratio", 0) or 0) >= 5:
        severe_signals += 1
    if int(telemetry.get("latency_ms", 0) or 0) >= 150:
        severe_signals += 1
    if float(telemetry.get("packet_loss", 0) or 0) >= 2:
        severe_signals += 1
    if int(telemetry.get("app_crashes", 0) or 0) > 0:
        severe_signals += 1
    return severe_signals


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

    if mode == "Live API fetch":
        return (
            qoe_preview.get("qoe_status") == "Poor"
            and _count_severe_signals(telemetry) >= 2
        )

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
