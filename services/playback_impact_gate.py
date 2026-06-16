from __future__ import annotations

from typing import Any


def calculate_dropped_frame_ratio(telemetry: dict[str, Any]) -> float:
    total_frames = max(0, int(telemetry.get("total_frames", 0) or 0))
    dropped_frames = max(0, int(telemetry.get("dropped_frames", 0) or 0))
    if total_frames <= 0:
        return 0.0
    return dropped_frames / total_frames


def evaluate_playback_impact(
    telemetry: dict[str, Any], qoe_status: str
) -> dict[str, Any]:
    player_state = str(telemetry.get("player_state", "unknown"))
    buffered_ahead_seconds = float(telemetry.get("buffered_ahead_seconds", 0.0) or 0.0)
    playback_time_moving = bool(telemetry.get("playback_time_moving", False))
    stall_count = int(telemetry.get("stall_count", 0) or 0)
    resolution = str(telemetry.get("resolution", "unknown"))
    dropped_frame_ratio = calculate_dropped_frame_ratio(telemetry)

    critical = (
        player_state == "error"
        or buffered_ahead_seconds < 2
        or stall_count >= 2
        or (qoe_status == "Poor" and not playback_time_moving)
    )
    if critical:
        reasons: list[str] = []
        if player_state == "error":
            reasons.append("Player reported an error state.")
        if buffered_ahead_seconds < 2:
            reasons.append("Buffered-ahead depth dropped below 2 seconds.")
        if stall_count >= 2:
            reasons.append("Two or more playback stalls were observed.")
        if qoe_status == "Poor" and not playback_time_moving:
            reasons.append("Playback time is not advancing while QoE is poor.")
        return {
            "impact_status": "Critical",
            "should_run_diagnosis": True,
            "should_run_recovery": True,
            "should_run_customer_care": True,
            "impact_score": 92,
            "reasons": reasons,
            "decision": "Critical playback degradation detected. Trigger the full agent workflow.",
            "dropped_frame_ratio": dropped_frame_ratio,
        }

    stable = (
        buffered_ahead_seconds >= 10
        and player_state in {"playing", "ready", "paused"}
        and (playback_time_moving or player_state == "paused")
        and dropped_frame_ratio < 0.02
        and qoe_status in {"Good", "Warning"}
    )
    if stable:
        reasons = [
            "Buffered-ahead depth remains above 10 seconds.",
            f"Player state is {player_state} with smooth playback progression.",
            "Dropped-frame ratio remains below 2%.",
        ]
        return {
            "impact_status": "Stable",
            "should_run_diagnosis": False,
            "should_run_recovery": False,
            "should_run_customer_care": False,
            "impact_score": 12,
            "reasons": reasons,
            "decision": "Playback is stable. Continue monitoring.",
            "dropped_frame_ratio": dropped_frame_ratio,
        }

    at_risk = (
        qoe_status in {"Poor", "Warning"}
        and buffered_ahead_seconds >= 5
        and player_state == "playing"
        and dropped_frame_ratio < 0.03
    )
    if at_risk:
        reasons = [
            "QoE is degraded, but the buffer remains above 5 seconds.",
            "Playback is still advancing in a playing state.",
            "Dropped-frame ratio remains below 3%.",
        ]
        return {
            "impact_status": "At Risk",
            "should_run_diagnosis": False,
            "should_run_recovery": False,
            "should_run_customer_care": False,
            "impact_score": 42,
            "reasons": reasons,
            "decision": "QoE risk detected, but playback impact is not confirmed. Continue monitoring.",
            "dropped_frame_ratio": dropped_frame_ratio,
        }

    reasons = []
    if buffered_ahead_seconds < 5:
        reasons.append("Buffered-ahead depth dropped below 5 seconds.")
    if player_state in {"buffering", "waiting"} and not playback_time_moving:
        reasons.append("Playback entered buffering or waiting while time stopped advancing.")
    if stall_count > 0:
        reasons.append("At least one playback stall was observed.")
    if dropped_frame_ratio >= 0.03:
        reasons.append("Dropped-frame ratio reached or exceeded 3%.")
    if resolution in {"854x480", "640x360"} and qoe_status in {"Poor", "Warning"}:
        reasons.append("Playback quality fell to a low resolution during degraded QoE.")

    return {
        "impact_status": "Impact Confirmed",
        "should_run_diagnosis": True,
        "should_run_recovery": True,
        "should_run_customer_care": False,
        "impact_score": 74,
        "reasons": reasons or ["Playback smoothness signals indicate visible customer impact."],
        "decision": "Playback impact detected. Run diagnosis and recovery.",
        "dropped_frame_ratio": dropped_frame_ratio,
    }
