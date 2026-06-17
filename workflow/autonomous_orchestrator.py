from __future__ import annotations

from typing import Any


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
            "detail": "Commander decided no agent escalation is needed yet.",
        },
        "diagnose": {
            "title": "Diagnosis required",
            "detail": "Commander assigned Diagnosis Agent for investigation.",
        },
        "self_heal": {
            "title": "Self-healing recommended",
            "detail": "Commander recommends safe recovery after approval.",
        },
        "customer_care": {
            "title": "Customer care required",
            "detail": "Commander recommends customer-safe communication.",
        },
        "escalate": {
            "title": "Escalation required",
            "detail": "Commander recommends full workflow and human oversight.",
        },
    }
    base = mappings.get(decision, mappings["monitor_only"])
    return {
        "title": base["title"],
        "detail": base["detail"],
        "priority": severity,
        "band": band,
    }
