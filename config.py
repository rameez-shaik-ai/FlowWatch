from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv


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
    "bitrate_mbps": 2.1,
    "buffering_ratio": 8.5,
    "latency_ms": 180,
    "packet_loss": 3.2,
    "app_crashes": 1,
    "qoe_score": 42,
}


def get_secret(name: str, default: str = "") -> str:
    """Read a secret from Streamlit first, then fall back to environment variables."""
    return st.secrets.get(name, os.getenv(name, default))
