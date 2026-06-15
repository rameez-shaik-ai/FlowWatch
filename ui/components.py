from __future__ import annotations

from typing import Any

import streamlit as st

from models import BandConfig


def render_agent_orchestration_board(
    agent_states: dict[str, str],
    agent_messages: dict[str, str],
    band_config: BandConfig,
) -> None:
    agent_specs = [
        ("QoE Monitoring Agent", "Monitor thresholds", "📡"),
        ("Diagnosis Agent", "Infer root cause", "🧠"),
        ("Recovery Action Agent", "Plan safe actions", "🛠️"),
        ("Customer Care Agent", "Prepare outreach", "💬"),
    ]
    remote_count = len(band_config.participants) + (1 if band_config.agent_id else 0)
    with st.container(border=True):
        st.markdown(
            '<div class="section-title" style="margin-bottom:0.35rem;">Live Agent Orchestration</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="compact-note">Compact live agent cards show who is active right now and the latest handoff message for each specialist.</div>',
            unsafe_allow_html=True,
        )

        kpi_cols = st.columns(3, gap="medium")
        kpi_cols[0].markdown(
            '<div class="kpi-pill"><strong>4</strong><span>Core FlowWatch agents</span></div>',
            unsafe_allow_html=True,
        )
        kpi_cols[1].markdown(
            f'<div class="kpi-pill"><strong>{remote_count}</strong><span>Band-connected agents</span></div>',
            unsafe_allow_html=True,
        )
        kpi_cols[2].markdown(
            f'<div class="kpi-pill"><strong>{sum(1 for value in agent_states.values() if value == "done")}</strong><span>Completed steps</span></div>',
            unsafe_allow_html=True,
        )

        columns = st.columns(4, gap="medium")
        for column, (name, role, icon) in zip(columns, agent_specs):
            state = agent_states.get(name, "waiting")
            label = {
                "active": "Running",
                "done": "Complete",
                "waiting": "Standby",
            }.get(state, "Standby")
            message = agent_messages.get(name, "Awaiting handoff")
            with column:
                st.markdown(
                    f"""
                    <div class="agent-card {state}">
                        <div class="agent-head">
                            <div class="agent-icon">{icon}</div>
                            <div class="agent-state">
                                <p class="agent-name">{name}</p>
                                <p class="agent-role">{role}</p>
                            </div>
                        </div>
                        <div class="agent-message">{message}</div>
                        <div class="agent-meta">
                            <span class="agent-badge {state}">{label}</span>
                            <span class="agent-led {state}"></span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_agent_box(title: str, content: Any, is_json: bool = False) -> None:
    with st.container(border=True):
        st.subheader(title)
        if is_json:
            st.json(content)
        else:
            st.markdown(content)


def render_band_room(
    room_id: str,
    shared_context: dict[str, Any],
    communication_log: list[dict[str, Any]],
    band_result: dict[str, Any] | None,
) -> None:
    with st.container(border=True):
        st.subheader("Band Communication Layer")
        st.write(
            "FlowWatch uses Band as the agent communication fabric. Each run can publish "
            "structured workflow updates into a real Band room, while the trace below shows "
            "what was shared between specialists."
        )

        live_note = "Live Band publishing was skipped for this run."
        if band_result and band_result.get("published"):
            live_note = (
                f"Live Band room created successfully. Room ID: `{band_result['room_id']}`"
            )
        elif band_result and band_result.get("error"):
            live_note = f"Band publish failed: {band_result['error']}"

        st.caption(live_note)
        room_col, log_col = st.columns([1, 1.35], gap="large")

        with room_col:
            st.markdown("**Shared room context**")
            st.json(shared_context)
            if band_result:
                st.markdown("**Band publish result**")
                st.json(band_result)

        with log_col:
            st.markdown("**Agent handoff trace**")
            for event in communication_log:
                with st.container(border=True):
                    st.markdown(
                        f"**Step {event['step']} · {event['sender']} -> {event['receiver']}**"
                    )
                    st.caption(f"{event['event_type']} | {event['summary']}")
                    with st.expander("Shared payload"):
                        st.json(event["payload"])


def render_telemetry_metrics(telemetry: dict[str, Any]) -> None:
    metrics = st.columns(6)
    metrics[0].metric("QoE Score", telemetry["qoe_score"])
    metrics[1].metric("Ideal QoE", ">= 80", delta=f"{telemetry['qoe_score'] - 80}")
    metrics[2].metric("Bitrate", f"{telemetry['bitrate_mbps']} Mbps")
    metrics[3].metric("Buffering", f"{telemetry['buffering_ratio']}%")
    metrics[4].metric("Latency", f"{telemetry['latency_ms']} ms")
    metrics[5].metric("Packet Loss", f"{telemetry['packet_loss']}%")


def render_raw_telemetry_json(telemetry: dict[str, Any]) -> None:
    with st.expander("Raw telemetry JSON"):
        st.json(telemetry)


def render_workflow_status_panels(
    band_config: BandConfig,
    band_sdk_available: bool,
) -> None:
    readiness_col, band_col = st.columns([1.15, 0.85], gap="large")
    with readiness_col:
        with st.container(border=True):
            st.markdown('<div class="section-title">Workflow Control</div>', unsafe_allow_html=True)
            st.write(
                "Run the full pipeline below. FlowWatch first applies deterministic QoE rules, "
                "then escalates to AI-powered diagnosis, recovery, and communication only when "
                "customer impact is likely."
            )
    with band_col:
        with st.container(border=True):
            st.markdown('<div class="section-title">Band Mode</div>', unsafe_allow_html=True)
            if band_config.enabled and band_sdk_available and band_config.api_key:
                st.success("Band live room publishing is armed for this run.")
            elif band_config.enabled and not band_sdk_available:
                st.warning("Band publishing is enabled, but the SDK package is not available in this runtime.")
            elif band_config.enabled and not band_config.api_key:
                st.warning("Band publishing is enabled, but BAND_API_KEY is missing.")
            else:
                st.info("Band sync is optional. Enable it in the sidebar to publish the workflow into a real Band room.")
