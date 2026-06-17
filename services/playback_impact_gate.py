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
    raw_stall_count = int(telemetry.get("stall_count", 0) or 0)
    resolution = str(telemetry.get("resolution", "unknown"))
    dropped_frame_ratio = calculate_dropped_frame_ratio(telemetry)
    current_buffering_state = player_state in {"buffering", "waiting", "stalled"}
    healthy_buffer = buffered_ahead_seconds >= 10
    usable_buffer = buffered_ahead_seconds >= 5
    low_buffer = buffered_ahead_seconds < 5
    critical_buffer = buffered_ahead_seconds < 2
    playback_stuck = not playback_time_moving and player_state not in {"paused", "ended"}
    confirmed_stall = current_buffering_state and playback_stuck and low_buffer
    smooth_playback = (
        healthy_buffer
        and playback_time_moving
        and dropped_frame_ratio < 0.02
        and player_state in {"playing", "buffering", "ready"}
    )

    critical = (
        player_state == "error"
        or critical_buffer
        or (qoe_status == "Poor" and playback_stuck and low_buffer)
        or (raw_stall_count >= 2 and confirmed_stall)
    )
    if critical:
        reasons: list[str] = []
        if player_state == "error":
            reasons.append("Player reported an error state.")
        if critical_buffer:
            reasons.append("Buffered-ahead depth dropped below 2 seconds.")
        if qoe_status == "Poor" and playback_stuck and low_buffer:
            reasons.append("Playback is stuck while QoE is poor and buffer is low.")
        if raw_stall_count >= 2 and confirmed_stall:
            reasons.append("Repeated confirmed stalls occurred with low buffer.")
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
        healthy_buffer
        and playback_time_moving
        and dropped_frame_ratio < 0.02
        and player_state in {"playing", "buffering", "ready", "paused"}
        and player_state != "error"
    )
    if stable:
        reasons: list[str] = [
            "Buffered-ahead depth remains above 10 seconds.",
            "Playback time is advancing.",
            "Dropped-frame ratio remains below 2%.",
        ]
        if player_state in {"buffering", "waiting", "stalled"} or raw_stall_count > 0:
            reasons.append("Raw buffering/stall events detected, but playback is currently smooth.")
        else:
            reasons.append(f"Player state is {player_state} with smooth playback progression.")
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
        (
            qoe_status in {"Poor", "Warning"}
            or raw_stall_count > 0
            or player_state in {"buffering", "waiting"}
            or 0.02 <= dropped_frame_ratio < 0.03
            or 5 <= buffered_ahead_seconds < 10
        )
        and not confirmed_stall
        and usable_buffer
        and playback_time_moving
    )
    if at_risk:
        reasons = []
        if qoe_status in {"Poor", "Warning"}:
            reasons.append("QoE is degraded but playback is still moving.")
        if usable_buffer:
            reasons.append("Buffer depth remains usable.")
        if raw_stall_count > 0 or player_state in {"buffering", "waiting", "stalled"}:
            reasons.append("Raw stall/buffering events were detected but not confirmed as visible stalls.")
        if 0.02 <= dropped_frame_ratio < 0.03:
            reasons.append("Dropped-frame ratio is elevated but below impact threshold.")
        return {
            "impact_status": "At Risk",
            "should_run_diagnosis": False,
            "should_run_recovery": False,
            "should_run_customer_care": False,
            "impact_score": 42,
            "reasons": reasons,
            "decision": "QoE or player risk detected, but playback impact is not confirmed. Continue monitoring.",
            "dropped_frame_ratio": dropped_frame_ratio,
        }

    impact_confirmed = (
        confirmed_stall
        or low_buffer
        or dropped_frame_ratio >= 0.03
        or (
            resolution in {"854x480", "640x360"}
            and qoe_status in {"Poor", "Warning"}
        )
    )
    if impact_confirmed:
        reasons: list[str] = []
        if low_buffer:
            reasons.append("Buffer depth dropped below 5 seconds.")
        if confirmed_stall:
            reasons.append("Playback is buffering or waiting and time is not advancing.")
        if dropped_frame_ratio >= 0.03:
            reasons.append("Dropped-frame ratio reached or exceeded 3%.")
        if resolution in {"854x480", "640x360"} and qoe_status in {"Poor", "Warning"}:
            reasons.append("Resolution fell to low quality during degraded QoE.")
        return {
            "impact_status": "Impact Confirmed",
            "should_run_diagnosis": True,
            "should_run_recovery": True,
            "should_run_customer_care": False,
            "impact_score": 74,
            "reasons": reasons,
            "decision": "Playback impact detected. Run diagnosis and recovery.",
            "dropped_frame_ratio": dropped_frame_ratio,
        }

    return {
        "impact_status": "Stable" if smooth_playback else "At Risk",
        "should_run_diagnosis": False,
        "should_run_recovery": False,
        "should_run_customer_care": False,
        "impact_score": 15 if smooth_playback else 35,
        "reasons": [
            "Playback signals are mixed, but visible impact is not confirmed yet."
        ],
        "decision": (
            "Playback is stable. Continue monitoring."
            if smooth_playback
            else "QoE or player risk detected, but playback impact is not confirmed. Continue monitoring."
        ),
        "dropped_frame_ratio": dropped_frame_ratio,
    }
