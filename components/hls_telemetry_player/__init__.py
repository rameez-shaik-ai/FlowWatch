from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit.components.v1 as components


_FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"
_component_func = components.declare_component(
    "hls_telemetry_player",
    path=str(_FRONTEND_DIR),
)


def hls_telemetry_player(
    stream_url: str,
    refresh_interval_ms: int = 2000,
    height: int = 620,
    emit_metrics: bool = True,
    key: str | None = None,
) -> dict[str, Any] | None:
    return _component_func(
        stream_url=stream_url,
        refresh_interval_ms=refresh_interval_ms,
        height=height,
        emit_metrics=emit_metrics,
        key=key,
        default=None,
    )
