from __future__ import annotations

import streamlit as st

from models import BandConfig
from services.band_service import BAND_SDK_AVAILABLE


def render_hero(band_config: BandConfig) -> None:
    band_status = (
        '<span class="status-chip band">Band live sync enabled</span>'
        if band_config.enabled
        else '<span class="status-chip warn">Band sync optional</span>'
    )
    sdk_status = (
        '<span class="status-chip ready">Band SDK ready</span>'
        if BAND_SDK_AVAILABLE
        else '<span class="status-chip warn">Band SDK not installed locally</span>'
    )
    st.markdown(
        f"""
        <div class="hero-shell">
            <div class="hero-kicker">Telecom multi-agent command center</div>
            <div class="hero-title">FlowWatch</div>
            <p class="hero-copy">
                Detect TV streaming degradation early, hand off context across specialist agents,
                publish the workflow into a real Band room, and generate safe recovery guidance
                plus customer-ready communication from one modern operations console.
            </p>
            <div class="flow-line">
                <span class="flow-pill">Monitor</span>
                <span class="flow-pill">Diagnose</span>
                <span class="flow-pill">Recover</span>
                <span class="flow-pill">Communicate</span>
                <span class="flow-pill">Band sync</span>
            </div>
            <div class="status-chip-row">
                <span class="status-chip ready">AI/ML API connected by key</span>
                {sdk_status}
                {band_status}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_overview_cards() -> None:
    cards = st.columns(3, gap="large")
    overview = [
        (
            "Proactive operations",
            "Rules catch poor QoE before a complaint lands in customer care.",
        ),
        (
            "Real Band handoffs",
            "Each run can create a live Band room and publish agent-to-agent workflow events.",
        ),
        (
            "Safe intervention",
            "Recovery guidance stays bounded to low-risk actions that fit a hackathon demo and telecom ops reality.",
        ),
    ]
    for column, (title, body) in zip(cards, overview):
        column.markdown(
            f"""
            <div class="command-card">
                <h4>{title}</h4>
                <p>{body}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_hackathon_alignment() -> None:
    st.subheader("Hackathon Alignment")
    alignment_rows = [
        {
            "Hackathon Area": "Multi-agent workflow",
            "How FlowWatch addresses it": "Four focused agents collaborate across monitoring, diagnosis, recovery, and communication.",
        },
        {
            "Hackathon Area": "Band usage",
            "How FlowWatch addresses it": "Band is now used as the live communication layer to publish room context, handoffs, and optional agent participant coordination.",
        },
        {
            "Hackathon Area": "AI/ML API usage",
            "How FlowWatch addresses it": "The diagnosis, recovery, and customer care agents call the AI/ML API with a user-selected model.",
        },
        {
            "Hackathon Area": "Business value",
            "How FlowWatch addresses it": "The app reduces churn risk by spotting likely streaming issues before the customer contacts support.",
        },
        {
            "Hackathon Area": "Demo app",
            "How FlowWatch addresses it": "The Streamlit UI behaves like a modern operations command center with editable telemetry and visible Band collaboration proof.",
        },
    ]
    st.table(alignment_rows)
