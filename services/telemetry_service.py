from __future__ import annotations

from typing import Any

import requests

from config import DEFAULT_TELEMETRY


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

    expected_keys = set(DEFAULT_TELEMETRY.keys())
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
        "qoe_score": int(data["qoe_score"]),
    }
    return normalized, None
