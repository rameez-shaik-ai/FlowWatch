from __future__ import annotations

import random
from typing import Any


def calculate_qoe_score(telemetry: dict[str, Any]) -> int:
    """Calculate a QoE score from telemetry using the current demo scoring model."""
    score = 100.0

    bitrate = float(telemetry["bitrate_mbps"])
    buffering = float(telemetry["buffering_ratio"])
    latency = float(telemetry["latency_ms"])
    packet_loss = float(telemetry["packet_loss"])
    crashes = int(telemetry["app_crashes"])

    if bitrate < 8:
        score -= (8 - bitrate) * 4.5
    if buffering > 1:
        score -= min(buffering - 1, 12) * 4.8
    if latency > 40:
        score -= min((latency - 40) / 12, 20)
    if packet_loss > 0.5:
        score -= min((packet_loss - 0.5) * 10, 24)
    if crashes > 0:
        score -= min(crashes * 18, 36)

    return max(0, min(100, round(score)))


def generate_random_telemetry() -> dict[str, Any]:
    telemetry = {
        "customer_id": f"CUST_{random.randint(100, 999)}",
        "device_id": f"STB_{random.randint(100, 999)}",
        "service": random.choice(
            ["TV streaming", "Live sports stream", "Movie playback", "Kids channel"]
        ),
        "bitrate_mbps": round(random.uniform(0.8, 9.5), 1),
        "buffering_ratio": round(random.uniform(0.0, 9.5), 1),
        "latency_ms": random.randint(20, 260),
        "packet_loss": round(random.uniform(0.0, 4.5), 1),
        "app_crashes": random.randint(0, 2),
    }
    telemetry["qoe_score"] = calculate_qoe_score(telemetry)
    return telemetry


def generate_ideal_telemetry() -> dict[str, Any]:
    while True:
        telemetry = {
            "customer_id": f"CUST_{random.randint(100, 999)}",
            "device_id": f"STB_{random.randint(100, 999)}",
            "service": "TV streaming",
            "bitrate_mbps": round(random.uniform(6.4, 9.4), 1),
            "buffering_ratio": round(random.uniform(0.0, 1.8), 1),
            "latency_ms": random.randint(22, 78),
            "packet_loss": round(random.uniform(0.0, 0.7), 1),
            "app_crashes": 0,
        }
        telemetry["qoe_score"] = calculate_qoe_score(telemetry)
        if telemetry["qoe_score"] > 80:
            return telemetry
