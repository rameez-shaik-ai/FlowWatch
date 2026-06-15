from __future__ import annotations

from typing import Any


def qoe_monitoring_agent(telemetry: dict[str, Any]) -> dict[str, Any]:
    """Apply the rule-based QoE monitoring logic used by FlowWatch today."""
    qoe_score = float(telemetry["qoe_score"])
    evidence: list[str] = []

    if float(telemetry["buffering_ratio"]) > 5:
        evidence.append(
            f"Buffering ratio is {telemetry['buffering_ratio']}%, above the 5% threshold."
        )
    if float(telemetry["latency_ms"]) > 150:
        evidence.append(
            f"Latency is {telemetry['latency_ms']} ms, above the 150 ms threshold."
        )
    if float(telemetry["packet_loss"]) > 2:
        evidence.append(
            f"Packet loss is {telemetry['packet_loss']}%, above the 2% threshold."
        )
    if float(telemetry["bitrate_mbps"]) < 3:
        evidence.append(
            f"Bitrate is {telemetry['bitrate_mbps']} Mbps, below the 3 Mbps threshold."
        )
    if int(telemetry["app_crashes"]) > 0:
        evidence.append(
            f"Application crashed {telemetry['app_crashes']} time(s) during the session."
        )

    if qoe_score >= 80:
        qoe_status = "Good"
    elif qoe_score >= 50:
        qoe_status = "Warning"
    else:
        qoe_status = "Poor"

    if evidence:
        qoe_status = "Poor"

    if qoe_status == "Good":
        impact_summary = (
            "Streaming experience appears healthy and no proactive intervention is required."
        )
    elif qoe_status == "Warning":
        impact_summary = (
            "Customer experience may degrade soon, so closer monitoring is recommended."
        )
    else:
        impact_summary = (
            "Customer is likely experiencing noticeable streaming disruption and needs proactive support."
        )

    return {
        "agent": "QoE Monitoring Agent",
        "qoe_status": qoe_status,
        "key_evidence": evidence,
        "customer_impact_summary": impact_summary,
        "recommended_next_agent": (
            "Diagnosis Agent" if qoe_status != "Good" else "None"
        ),
    }
