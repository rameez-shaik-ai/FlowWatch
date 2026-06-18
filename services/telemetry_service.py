from __future__ import annotations

import random
from typing import Any

import requests

from config import DEFAULT_TELEMETRY
from utils.qoe_scoring import calculate_qoe_score


DEMO_LIVE_API_ENDPOINT_PREFIX = "flowwatch://demo/live-api/"


def _normalize_native_payload(data: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    expected_keys = set(DEFAULT_TELEMETRY.keys()) - {"qoe_score"}
    if not expected_keys.issubset(data.keys()):
        missing = ", ".join(sorted(expected_keys - set(data.keys())))
        return None, f"Telemetry payload is missing keys: {missing}"

    normalized = {
        "customer_id": str(data["customer_id"]),
        "device_id": str(data["device_id"]),
        "service": str(data["service"]),
        "bitrate_mbps": float(data["bitrate_mbps"]),
        "buffering_ratio": float(data["buffering_ratio"]),
        "latency_ms": int(data["latency_ms"]),
        "packet_loss": float(data["packet_loss"]),
        "app_crashes": int(data["app_crashes"]),
    }
    normalized["qoe_score"] = calculate_qoe_score(normalized)
    return normalized, None


def _normalize_simple_mock_payload(data: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    required = {"session_id", "bitrate", "buffering_ratio", "stall_count", "cdn", "device", "network"}
    if not required.issubset(data.keys()):
        missing = ", ".join(sorted(required - set(data.keys())))
        return None, f"Telemetry payload is missing keys: {missing}"

    network = str(data["network"]).strip().lower()
    latency_lookup = {
        "ethernet": 50,
        "wifi": 90,
        "5g": 110,
        "4g": 160,
    }
    buffering_ratio_percent = float(data["buffering_ratio"]) * 100
    stall_count = int(data["stall_count"])
    normalized = {
        "customer_id": str(data["session_id"]),
        "device_id": str(data["device"]),
        "service": f"Live API stream via {str(data['cdn'])}",
        "bitrate_mbps": float(data["bitrate"]) / 1000,
        "buffering_ratio": buffering_ratio_percent,
        "latency_ms": latency_lookup.get(network, 100),
        "packet_loss": min(5.0, stall_count * 0.8 + buffering_ratio_percent * 0.15),
        "app_crashes": 0,
    }
    normalized["qoe_score"] = calculate_qoe_score(normalized)
    return normalized, None


def normalize_live_telemetry_payload(data: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    if {"customer_id", "device_id", "service", "bitrate_mbps", "buffering_ratio", "latency_ms", "packet_loss", "app_crashes"}.issubset(data.keys()):
        return _normalize_native_payload(data)
    if {"session_id", "bitrate", "buffering_ratio", "stall_count", "cdn", "device", "network"}.issubset(data.keys()):
        return _normalize_simple_mock_payload(data)
    return None, "Telemetry payload is not in a supported FlowWatch format."


def load_live_telemetry(endpoint: str) -> tuple[dict[str, Any] | None, str | None]:
    """Fetch and normalize telemetry JSON from a live endpoint."""
    try:
        response = requests.get(endpoint, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as exc:
        return None, f"Unable to fetch telemetry: {exc}"
    except ValueError:
        return None, "Telemetry endpoint did not return valid JSON."

    return normalize_live_telemetry_payload(data)


def generate_demo_live_api_telemetry(
    tick: int,
    session_id: str = "flowwatch-session",
) -> dict[str, Any]:
    cycle_tick = tick % 23
    rng = random.Random(4200 + tick * 13)

    if cycle_tick <= 5:
        stage = "healthy"
    elif cycle_tick <= 10:
        stage = "warning"
    elif cycle_tick <= 16:
        stage = "poor"
    else:
        stage = "recovering"

    if stage == "healthy":
        telemetry = {
            "customer_id": "LIVE_API_001",
            "device_id": "STB_LIVE_01",
            "service": "Live API stream",
            "bitrate_mbps": round(7.0 + (cycle_tick % 3) * 0.7 + rng.uniform(0.0, 0.25), 1),
            "buffering_ratio": round(0.2 + (cycle_tick % 4) * 0.25 + rng.uniform(0.0, 0.2), 1),
            "latency_ms": int(30 + (cycle_tick % 4) * 10 + rng.uniform(0, 8)),
            "packet_loss": round(0.1 + (cycle_tick % 3) * 0.15 + rng.uniform(0.0, 0.08), 1),
            "app_crashes": 0,
        }
    elif stage == "warning":
        stage_tick = cycle_tick - 6
        telemetry = {
            "customer_id": "LIVE_API_001",
            "device_id": "STB_LIVE_01",
            "service": "Live API stream",
            "bitrate_mbps": round(5.0 - stage_tick * 0.35 + rng.uniform(-0.1, 0.12), 1),
            "buffering_ratio": round(2.5 + stage_tick * 0.45 + rng.uniform(0.0, 0.18), 1),
            "latency_ms": int(100 + stage_tick * 10 + rng.uniform(0, 6)),
            "packet_loss": round(1.0 + stage_tick * 0.18 + rng.uniform(0.0, 0.08), 1),
            "app_crashes": 0,
        }
    elif stage == "poor":
        stage_tick = cycle_tick - 11
        telemetry = {
            "customer_id": "LIVE_API_001",
            "device_id": "STB_LIVE_01",
            "service": "Live API stream",
            "bitrate_mbps": round(max(1.2, 2.8 - stage_tick * 0.22 + rng.uniform(-0.08, 0.08)), 1),
            "buffering_ratio": round(min(9.5, 6.0 + stage_tick * 0.55 + rng.uniform(0.0, 0.25)), 1),
            "latency_ms": int(min(260, 170 + stage_tick * 14 + rng.uniform(0, 8))),
            "packet_loss": round(min(4.0, 2.2 + stage_tick * 0.24 + rng.uniform(0.0, 0.12)), 1),
            "app_crashes": 1 if stage_tick >= 3 else 0,
        }
    else:
        stage_tick = cycle_tick - 17
        telemetry = {
            "customer_id": "LIVE_API_001",
            "device_id": "STB_LIVE_01",
            "service": "Live API stream",
            "bitrate_mbps": round(min(6.5, 3.5 + stage_tick * 0.7 + rng.uniform(0.0, 0.18)), 1),
            "buffering_ratio": round(max(1.2, 4.0 - stage_tick * 0.7 + rng.uniform(-0.05, 0.12)), 1),
            "latency_ms": int(max(80, 150 - stage_tick * 18 + rng.uniform(0, 6))),
            "packet_loss": round(max(0.5, 2.0 - stage_tick * 0.35 + rng.uniform(-0.04, 0.05)), 1),
            "app_crashes": 0,
        }

    telemetry["customer_id"] = f"LIVE_API_{session_id.replace('-', '_').upper()[:18]}"
    telemetry["device_id"] = f"STB_{session_id.replace('-', '_').upper()[:14]}"
    telemetry["qoe_score"] = calculate_qoe_score(telemetry)
    return telemetry
