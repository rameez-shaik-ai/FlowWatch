from __future__ import annotations

from typing import Any

from utils.qoe_scoring import calculate_qoe_score


ALLOWED_SELF_HEALING_ACTIONS = {
    "restart_streaming_app",
    "refresh_streaming_session",
    "retry_playback",
    "none",
}


def sanitize_healing_action(action: str) -> str:
    action = str(action or "none")
    return action if action in ALLOWED_SELF_HEALING_ACTIONS else "none"


def get_healing_action_label(action: str) -> str:
    labels = {
        "restart_streaming_app": "Restart streaming app",
        "refresh_streaming_session": "Refresh streaming session",
        "retry_playback": "Retry playback",
        "none": "No self-healing action",
    }
    return labels.get(sanitize_healing_action(action), "No self-healing action")


def get_healing_action_description(action: str) -> str:
    descriptions = {
        "restart_streaming_app": "Restart the playback application and re-check whether the stream stabilizes.",
        "refresh_streaming_session": "Refresh the active streaming session to rebuild the playback pipeline.",
        "retry_playback": "Retry the current playback request without changing customer account state.",
        "none": "No operator-approved self-healing action is recommended at this time.",
    }
    return descriptions.get(
        sanitize_healing_action(action),
        "No operator-approved self-healing action is recommended at this time.",
    )


def simulate_restart_app_progress() -> list[str]:
    return [
        "Closing playback session",
        "Clearing temporary session state",
        "Restarting streaming app",
        "Rechecking QoE",
    ]


def apply_post_healing_telemetry(telemetry: dict[str, Any]) -> dict[str, Any]:
    healed = {
        **telemetry,
        "bitrate_mbps": max(float(telemetry.get("bitrate_mbps", 0.0) or 0.0), 5.8),
        "buffering_ratio": min(float(telemetry.get("buffering_ratio", 0.0) or 0.0), 1.2),
        "latency_ms": min(int(telemetry.get("latency_ms", 0) or 0), 80),
        "packet_loss": min(float(telemetry.get("packet_loss", 0.0) or 0.0), 0.5),
        "app_crashes": 0,
        "player_state": "playing",
        "buffered_ahead_seconds": max(
            float(telemetry.get("buffered_ahead_seconds", 0.0) or 0.0), 12.0
        ),
        "resolution": "1920x1080",
        "stall_count": 0,
        "playback_time_moving": True,
    }
    healed["qoe_score"] = calculate_qoe_score(healed)
    return healed
