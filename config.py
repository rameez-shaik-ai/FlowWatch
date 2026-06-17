from __future__ import annotations

import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional in stripped-down test runtimes
    def load_dotenv() -> bool:
        return False
try:
    import streamlit as st
    from streamlit.errors import StreamlitSecretNotFoundError
except ImportError:  # pragma: no cover - allows tests to import config without Streamlit
    st = None


load_dotenv()


AIML_API_URL = "https://api.aimlapi.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini"
MODEL_OPTIONS = [
    "gpt-4o-mini",
    "openai/gpt-4o-mini",
    "gpt-4o",
    "openai/gpt-4o",
    "google/gemma-3-4b-it",
]
DEFAULT_BAND_REST_URL = "https://app.band.ai"
DEFAULT_TELEMETRY = {
    "customer_id": "CUST_1001",
    "device_id": "STB_4455",
    "service": "TV streaming",
    "bitrate_mbps": 8.8,
    "buffering_ratio": 0.4,
    "latency_ms": 36,
    "packet_loss": 0.2,
    "app_crashes": 0,
    "qoe_score": 100,
}


def get_secret(name: str, default: str = "") -> str:
    """Read a secret from Streamlit first, then fall back to environment variables."""
    if st is None:
        return os.getenv(name, default)
    try:
        return st.secrets.get(name, os.getenv(name, default))
    except StreamlitSecretNotFoundError:
        return os.getenv(name, default)
