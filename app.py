from __future__ import annotations

import re
import time
from typing import Any

import streamlit as st
try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:  # pragma: no cover - fallback for environments missing the optional package
    st_autorefresh = None

from agents.customer_care_agent import customer_care_agent
from agents.diagnosis_agent import diagnosis_agent
from agents.qoe_monitoring_agent import qoe_monitoring_agent
from agents.recovery_action_agent import recovery_action_agent
from config import DEFAULT_MODEL, DEFAULT_TELEMETRY, MODEL_OPTIONS, get_secret
from services.band_service import (
    build_band_config,
    create_band_event,
    run_band_publish,
)
from services.playback_impact_gate import evaluate_playback_impact
from services.player_service import (
    DEFAULT_HLS_STREAM_URL,
    generate_dynamic_player_telemetry,
)
from services.telemetry_service import load_live_telemetry
from ui.components import (
    render_compact_header,
    render_embedded_player_panel,
    render_empty_state,
    render_kpi_cards,
    render_results_tabs,
    render_run_control,
    render_top_summary_cards,
)
from ui.styles import apply_theme
from utils.qoe_scoring import (
    calculate_qoe_score,
    generate_ideal_telemetry,
    generate_random_telemetry,
)


def initialize_session_state() -> None:
    if "telemetry_source_mode" not in st.session_state:
        st.session_state.telemetry_source_mode = "Manual"
    if "telemetry_values" not in st.session_state:
        st.session_state.telemetry_values = DEFAULT_TELEMETRY.copy()
    if "player_tick" not in st.session_state:
        st.session_state.player_tick = 0
    if "player_refresh_enabled" not in st.session_state:
        st.session_state.player_refresh_enabled = True
    if "player_refresh_interval_label" not in st.session_state:
        st.session_state.player_refresh_interval_label = "3 seconds"
    if "player_scenario" not in st.session_state:
        st.session_state.player_scenario = "Auto"
    if "player_stream_url" not in st.session_state:
        st.session_state.player_stream_url = DEFAULT_HLS_STREAM_URL
    if "player_auto_run_enabled" not in st.session_state:
        st.session_state.player_auto_run_enabled = False
    if "last_player_auto_run_ts" not in st.session_state:
        st.session_state.last_player_auto_run_ts = 0.0
    if "last_player_auto_run_key" not in st.session_state:
        st.session_state.last_player_auto_run_key = ""
    if "player_last_refresh_epoch" not in st.session_state:
        st.session_state.player_last_refresh_epoch = time.time()

def render_sidebar_telemetry_inputs() -> tuple[str, dict[str, Any], dict[str, Any]]:
    with st.sidebar:
        st.markdown("### Model")
        selected_model = st.selectbox(
            "AI/ML model",
            MODEL_OPTIONS,
            index=MODEL_OPTIONS.index(DEFAULT_MODEL),
            help="Switch models if one provider route is temporarily unavailable.",
            label_visibility="collapsed",
        )

        st.markdown("### Telemetry Source")
        st.session_state.telemetry_source_mode = st.radio(
            "Telemetry source",
            ["Manual", "Live API fetch", "Embedded HLS player"],
            index=["Manual", "Live API fetch", "Embedded HLS player"].index(
                st.session_state.telemetry_source_mode
            ),
            label_visibility="collapsed",
        )

        source_config = {
            "mode": st.session_state.telemetry_source_mode,
            "player_stream_url": st.session_state.player_stream_url,
            "player_refresh_enabled": st.session_state.player_refresh_enabled,
            "player_refresh_interval_label": st.session_state.player_refresh_interval_label,
            "player_refresh_interval_ms": {"2 seconds": 2000, "3 seconds": 3000, "5 seconds": 5000}[
                st.session_state.player_refresh_interval_label
            ],
            "player_scenario": st.session_state.player_scenario,
            "player_auto_run_enabled": st.session_state.player_auto_run_enabled,
        }

        if st.session_state.telemetry_source_mode == "Manual":
            random_col, ideal_col = st.columns(2, gap="small")
            with random_col:
                if st.button("Random", use_container_width=True):
                    st.session_state.telemetry_values = generate_random_telemetry()
                    st.rerun()
            with ideal_col:
                if st.button("Ideal", use_container_width=True):
                    st.session_state.telemetry_values = generate_ideal_telemetry()
                    st.rerun()

        if st.session_state.telemetry_source_mode == "Live API fetch":
            live_endpoint = st.text_input(
                "Telemetry API URL",
                value=st.session_state.get("live_endpoint", ""),
                help="Endpoint should return JSON with the same telemetry keys used by FlowWatch.",
            )
            st.session_state.live_endpoint = live_endpoint
            if st.button("Load live telemetry", use_container_width=True):
                telemetry_data, error = load_live_telemetry(live_endpoint)
                if error:
                    st.error(error)
                elif telemetry_data is not None:
                    st.session_state.telemetry_values = telemetry_data
                    st.success("Live telemetry loaded into the dashboard.")

        if st.session_state.telemetry_source_mode == "Embedded HLS player":
            st.markdown("### Player Mode")
            st.session_state.player_stream_url = st.text_input(
                "HLS stream URL",
                value=st.session_state.player_stream_url,
            )
            st.session_state.player_refresh_enabled = st.toggle(
                "Auto-refresh player telemetry",
                value=st.session_state.player_refresh_enabled,
            )
            st.session_state.player_refresh_interval_label = st.selectbox(
                "Refresh interval",
                ["2 seconds", "3 seconds", "5 seconds"],
                index=["2 seconds", "3 seconds", "5 seconds"].index(
                    st.session_state.player_refresh_interval_label
                ),
            )
            st.session_state.player_scenario = st.selectbox(
                "Player telemetry scenario",
                ["Auto", "Healthy", "Degraded", "Recovering"],
                index=["Auto", "Healthy", "Degraded", "Recovering"].index(
                    st.session_state.player_scenario
                ),
            )
            st.session_state.player_auto_run_enabled = st.toggle(
                "Auto-run agent analysis when QoE is Poor",
                value=st.session_state.player_auto_run_enabled,
            )
            if st.button("Refresh player telemetry", use_container_width=True):
                st.session_state.player_tick += 1
                st.session_state.player_last_refresh_epoch = time.time()
                st.rerun()
            st.session_state.telemetry_values = generate_dynamic_player_telemetry(
                st.session_state.player_tick,
                st.session_state.player_scenario,
            )
            source_config = {
                "mode": "Embedded HLS player",
                "player_stream_url": st.session_state.player_stream_url,
                "player_refresh_enabled": st.session_state.player_refresh_enabled,
                "player_refresh_interval_label": st.session_state.player_refresh_interval_label,
                "player_refresh_interval_ms": {
                    "2 seconds": 2000,
                    "3 seconds": 3000,
                    "5 seconds": 5000,
                }[st.session_state.player_refresh_interval_label],
                "player_scenario": st.session_state.player_scenario,
                "player_auto_run_enabled": st.session_state.player_auto_run_enabled,
            }
        telemetry_defaults = st.session_state.telemetry_values
        telemetry_disabled = st.session_state.telemetry_source_mode == "Embedded HLS player"
        if st.session_state.telemetry_source_mode == "Embedded HLS player":
            telemetry = {
                "customer_id": telemetry_defaults["customer_id"],
                "device_id": telemetry_defaults["device_id"],
                "service": telemetry_defaults["service"],
                "bitrate_mbps": float(telemetry_defaults["bitrate_mbps"]),
                "buffering_ratio": float(telemetry_defaults["buffering_ratio"]),
                "latency_ms": int(telemetry_defaults["latency_ms"]),
                "packet_loss": float(telemetry_defaults["packet_loss"]),
                "app_crashes": int(telemetry_defaults["app_crashes"]),
            }
            with st.expander("Mapped telemetry fields", expanded=False):
                st.text_input("Customer ID", value=telemetry_defaults["customer_id"], disabled=True)
                st.text_input("Device ID", value=telemetry_defaults["device_id"], disabled=True)
                st.text_input("Service", value=telemetry_defaults["service"], disabled=True)
                st.number_input(
                    "Bitrate Mbps",
                    min_value=0.0,
                    value=float(telemetry_defaults["bitrate_mbps"]),
                    step=0.1,
                    disabled=True,
                )
                st.number_input(
                    "Buffering ratio %",
                    min_value=0.0,
                    value=float(telemetry_defaults["buffering_ratio"]),
                    step=0.1,
                    disabled=True,
                )
                st.number_input(
                    "Latency ms",
                    min_value=0,
                    value=int(telemetry_defaults["latency_ms"]),
                    step=1,
                    disabled=True,
                )
                st.number_input(
                    "Packet loss %",
                    min_value=0.0,
                    value=float(telemetry_defaults["packet_loss"]),
                    step=0.1,
                    disabled=True,
                )
                st.number_input(
                    "App crashes",
                    min_value=0,
                    value=int(telemetry_defaults["app_crashes"]),
                    step=1,
                    disabled=True,
                )
                st.number_input(
                    "QoE score",
                    min_value=0,
                    max_value=100,
                    value=int(telemetry_defaults["qoe_score"]),
                    step=1,
                    disabled=True,
                    help="Mapped from the embedded player telemetry scenario for this prototype.",
                )
        else:
            st.markdown("### Telemetry Fields")
            telemetry = {
                "customer_id": st.text_input(
                    "Customer ID", value=telemetry_defaults["customer_id"], disabled=telemetry_disabled
                ),
                "device_id": st.text_input(
                    "Device ID", value=telemetry_defaults["device_id"], disabled=telemetry_disabled
                ),
                "service": st.text_input(
                    "Service", value=telemetry_defaults["service"], disabled=telemetry_disabled
                ),
                "bitrate_mbps": st.number_input(
                    "Bitrate Mbps",
                    min_value=0.0,
                    value=float(telemetry_defaults["bitrate_mbps"]),
                    step=0.1,
                    disabled=telemetry_disabled,
                ),
                "buffering_ratio": st.number_input(
                    "Buffering ratio %",
                    min_value=0.0,
                    value=float(telemetry_defaults["buffering_ratio"]),
                    step=0.1,
                    disabled=telemetry_disabled,
                ),
                "latency_ms": st.number_input(
                    "Latency ms",
                    min_value=0,
                    value=int(telemetry_defaults["latency_ms"]),
                    step=1,
                    disabled=telemetry_disabled,
                ),
                "packet_loss": st.number_input(
                    "Packet loss %",
                    min_value=0.0,
                    value=float(telemetry_defaults["packet_loss"]),
                    step=0.1,
                    disabled=telemetry_disabled,
                ),
                "app_crashes": st.number_input(
                    "App crashes",
                    min_value=0,
                    value=int(telemetry_defaults["app_crashes"]),
                    step=1,
                    disabled=telemetry_disabled,
                ),
            }

        if st.session_state.telemetry_source_mode == "Embedded HLS player":
            telemetry.update(
                {
                    "player_state": telemetry_defaults.get("player_state", "playing"),
                    "playback_time_seconds": float(
                        telemetry_defaults.get("playback_time_seconds", 0.0)
                    ),
                    "buffered_ahead_seconds": float(
                        telemetry_defaults.get("buffered_ahead_seconds", 0.0)
                    ),
                    "resolution": telemetry_defaults.get("resolution", "1280x720"),
                    "dropped_frames": int(telemetry_defaults.get("dropped_frames", 0)),
                    "total_frames": int(telemetry_defaults.get("total_frames", 0)),
                    "ready_state": int(telemetry_defaults.get("ready_state", 0)),
                    "network_state": int(telemetry_defaults.get("network_state", 0)),
                    "stall_count": int(telemetry_defaults.get("stall_count", 0)),
                    "playback_time_moving": bool(
                        telemetry_defaults.get("playback_time_moving", False)
                    ),
                }
            )

        if st.session_state.telemetry_source_mode == "Manual":
            telemetry["qoe_score"] = calculate_qoe_score(telemetry)
            st.number_input(
                "QoE score",
                min_value=0,
                max_value=100,
                value=int(telemetry["qoe_score"]),
                step=1,
                disabled=True,
                help="Calculated automatically from bitrate, buffering, latency, packet loss, and app crashes.",
            )
        elif st.session_state.telemetry_source_mode == "Embedded HLS player":
            telemetry["qoe_score"] = int(telemetry_defaults["qoe_score"])
        else:
            telemetry["qoe_score"] = st.number_input(
                "QoE score",
                min_value=0,
                max_value=100,
                value=int(telemetry_defaults["qoe_score"]),
                step=1,
                help="Provided by the live telemetry source.",
            )

        st.session_state.telemetry_values = telemetry.copy()

    return selected_model, telemetry, source_config


def extract_priority_level(customer_care_text: str | None) -> str:
    if not customer_care_text:
        return "Pending"
    match = re.search(
        r"Priority Level\s+([A-Za-z]+)",
        customer_care_text,
        flags=re.IGNORECASE,
    )
    return match.group(1).title() if match else "Available"


def run_multi_agent_workflow(
    *,
    telemetry: dict[str, Any],
    selected_model: str,
    band_config,
    summary_placeholder,
    default_agent_states: dict[str, str],
    qoe_preview: dict[str, Any],
    source_config: dict[str, Any],
    auto_triggered: bool = False,
    playback_impact: dict[str, Any] | None = None,
) -> None:
    room_id = f"band-room-{telemetry['customer_id'].lower()}"
    communication_log: list[dict[str, Any]] = []
    band_result: dict[str, Any] | None = None
    agent_states = dict(default_agent_states)
    embedded_mode = source_config["mode"] == "Embedded HLS player"
    allow_customer_care = (
        playback_impact.get("should_run_customer_care", True)
        if playback_impact is not None
        else True
    )

    action_summary = {
        "title": "Monitoring in progress",
        "detail": "Checking the session against FlowWatch QoE thresholds.",
        "priority": "Pending",
        "band": "Enabled" if band_config.enabled else "Disabled",
    }
    agent_states["QoE Monitoring Agent"] = "active"
    with summary_placeholder.container():
        render_top_summary_cards(
            telemetry=telemetry,
            qoe_preview=qoe_preview,
            workflow_state=agent_states,
            band_config=band_config,
            action_summary=action_summary,
            show_incident_card=not embedded_mode,
        )
    time.sleep(0.2)

    qoe_result = qoe_monitoring_agent(telemetry)
    agent_states["QoE Monitoring Agent"] = "done"
    communication_log.append(
        create_band_event(
            step=1,
            sender="QoE Monitoring Agent",
            receiver=qoe_result["recommended_next_agent"],
            event_type="room_publish",
            summary=f"Classified session as {qoe_result['qoe_status']}.",
            payload=(
                {
                    **qoe_result,
                    "playback_impact_gate": playback_impact,
                }
                if playback_impact is not None
                else qoe_result
            ),
        )
    )

    if qoe_result["qoe_status"] == "Good":
        action_summary = {
            "title": "Passive monitoring",
            "detail": "QoE is healthy. No escalation or customer outreach is required.",
            "priority": "Low",
            "band": "Published" if band_config.enabled else "Disabled",
        }
        with summary_placeholder.container():
            render_top_summary_cards(
                telemetry=telemetry,
                qoe_preview=qoe_result,
                workflow_state=agent_states,
                band_config=band_config,
                action_summary=action_summary,
                show_incident_card=not embedded_mode,
            )
        shared_context = {
            "room_status": "Monitoring complete",
            "customer_id": telemetry["customer_id"],
            "service": telemetry["service"],
            "active_agents": ["QoE Monitoring Agent"],
            "latest_status": qoe_result["qoe_status"],
            "next_action": "Continue passive monitoring",
        }
        if source_config["mode"] == "Embedded HLS player":
            shared_context.update(
                {
                    "source": "Embedded HLS player",
                    "trigger": "QoE degradation" if auto_triggered else "Manual review",
                    "auto_triggered": auto_triggered,
                    "playback_impact_gate": playback_impact,
                }
            )
        band_result = run_band_publish(
            band_config,
            telemetry,
            qoe_result,
            diagnosis_text=None,
            recovery_text=None,
            customer_care_text=None,
            model_name=selected_model,
        )
        st.success(
            "QoE looks healthy. FlowWatch stopped after monitoring because no further action is required."
        )
        render_results_tabs(
            room_id=room_id,
            shared_context=shared_context,
            communication_log=communication_log,
            band_result=band_result,
            qoe_result=qoe_result,
            diagnosis_text=None,
            recovery_text=None,
            customer_care_text=None,
            telemetry=telemetry,
        )
        return

    agent_states["Diagnosis Agent"] = "active"
    action_summary = {
        "title": "Diagnosis running",
        "detail": "Telemetry is being analyzed to identify the likely root cause.",
        "priority": "Medium",
        "band": "Enabled" if band_config.enabled else "Disabled",
    }
    with summary_placeholder.container():
        render_top_summary_cards(
            telemetry=telemetry,
            qoe_preview=qoe_result,
            workflow_state=agent_states,
            band_config=band_config,
            action_summary=action_summary,
            show_incident_card=not embedded_mode,
        )
    time.sleep(0.15)

    with st.spinner("Running diagnosis, recovery, customer care, and Band sync..."):
        diagnosis_text = diagnosis_agent(telemetry, qoe_result, selected_model)
        agent_states["Diagnosis Agent"] = "done"
        communication_log.append(
            create_band_event(
                step=2,
                sender="Diagnosis Agent",
                receiver="Recovery Action Agent",
                event_type="handoff",
                summary="Published root cause assessment to the shared collaboration layer.",
                payload={
                    "diagnosis_summary": diagnosis_text,
                    "customer_id": telemetry["customer_id"],
                    "qoe_status": qoe_result["qoe_status"],
                },
            )
        )

        agent_states["Recovery Action Agent"] = "active"
        action_summary = {
            "title": "Recovery planning",
            "detail": "FlowWatch is preparing safe remediation guidance for this incident.",
            "priority": "High",
            "band": "Enabled" if band_config.enabled else "Disabled",
        }
        with summary_placeholder.container():
                render_top_summary_cards(
                    telemetry=telemetry,
                    qoe_preview=qoe_result,
                    workflow_state=agent_states,
                    band_config=band_config,
                    action_summary=action_summary,
                    show_incident_card=not embedded_mode,
                )
        time.sleep(0.15)

        recovery_text = recovery_action_agent(telemetry, diagnosis_text, selected_model)
        agent_states["Recovery Action Agent"] = "done"
        communication_log.append(
            create_band_event(
                step=3,
                sender="Recovery Action Agent",
                receiver="Customer Care Agent" if allow_customer_care else "Support Operations",
                event_type="handoff",
                summary="Shared recommended safe actions and monitoring plan.",
                payload={
                    "recovery_plan": recovery_text,
                    "selected_model": selected_model,
                    "customer_id": telemetry["customer_id"],
                },
            )
        )

        customer_care_text = None
        if allow_customer_care:
            agent_states["Customer Care Agent"] = "active"
            action_summary = {
                "title": "Communication drafting",
                "detail": "Preparing customer-safe messaging and support-team summary.",
                "priority": "High",
                "band": "Enabled" if band_config.enabled else "Disabled",
            }
            with summary_placeholder.container():
                render_top_summary_cards(
                    telemetry=telemetry,
                    qoe_preview=qoe_result,
                    workflow_state=agent_states,
                    band_config=band_config,
                    action_summary=action_summary,
                    show_incident_card=not embedded_mode,
                )
            time.sleep(0.15)

            customer_care_text = customer_care_agent(
                telemetry,
                diagnosis_text,
                recovery_text,
                selected_model,
            )
            agent_states["Customer Care Agent"] = "done"
            communication_log.append(
                create_band_event(
                    step=4,
                    sender="Customer Care Agent",
                    receiver="Support Operations",
                    event_type="room_publish",
                    summary="Published customer communication and support summary.",
                    payload={
                        "customer_care_output": customer_care_text,
                        "device_id": telemetry["device_id"],
                        "service": telemetry["service"],
                    },
                )
            )

        band_result = run_band_publish(
            band_config,
            telemetry,
            qoe_result,
            diagnosis_text,
            recovery_text,
            customer_care_text,
            selected_model,
        )

    action_summary = {
        "title": "Proactive outreach" if allow_customer_care else "Recovery plan ready",
        "detail": (
            "The incident summary, next action, and customer communication are ready."
            if allow_customer_care
            else "Diagnosis and recovery are complete. Continue technical monitoring before customer outreach."
        ),
        "priority": extract_priority_level(customer_care_text) if allow_customer_care else "High",
        "band": (
            "Published"
            if band_result and band_result.get("published")
            else "Failed"
            if band_config.enabled
            else "Disabled"
        ),
    }
    with summary_placeholder.container():
        render_top_summary_cards(
            telemetry=telemetry,
            qoe_preview=qoe_result,
            workflow_state=agent_states,
            band_config=band_config,
            action_summary=action_summary,
            show_incident_card=not embedded_mode,
        )

    shared_context = {
        "room_status": "Escalation coordinated",
        "customer_id": telemetry["customer_id"],
        "device_id": telemetry["device_id"],
        "service": telemetry["service"],
        "active_agents": [
            "QoE Monitoring Agent",
            "Diagnosis Agent",
            "Recovery Action Agent",
            "Customer Care Agent",
        ],
        "latest_status": qoe_result["qoe_status"],
        "selected_model": selected_model,
        "next_action": (
            "Proactive outreach and continued monitoring"
            if allow_customer_care
            else "Continue technical recovery monitoring"
        ),
    }
    if source_config["mode"] == "Embedded HLS player":
        shared_context.update(
            {
                "source": "Embedded HLS player",
                "trigger": "QoE degradation" if auto_triggered else "Manual review",
                "auto_triggered": auto_triggered,
                "playback_impact_gate": playback_impact,
            }
        )
    render_results_tabs(
        room_id=room_id,
        shared_context=shared_context,
        communication_log=communication_log,
        band_result=band_result,
        qoe_result=qoe_result,
        diagnosis_text=diagnosis_text,
        recovery_text=recovery_text,
        customer_care_text=customer_care_text,
        telemetry=telemetry,
    )
    st.success(
        "FlowWatch analysis complete. The multi-agent workflow and Band communication layer are ready for demo."
    )


def main() -> None:
    st.set_page_config(page_title="FlowWatch", page_icon="📺", layout="wide")
    apply_theme()
    initialize_session_state()

    if (
        st.session_state.telemetry_source_mode == "Embedded HLS player"
        and st.session_state.player_refresh_enabled
        and st_autorefresh is not None
    ):
        st.session_state.player_tick = st_autorefresh(
            interval={
                "2 seconds": 2000,
                "3 seconds": 3000,
                "5 seconds": 5000,
            }[st.session_state.player_refresh_interval_label],
            key="player_telemetry_refresh",
        )
        st.session_state.player_last_refresh_epoch = time.time()

    band_config = build_band_config()
    selected_model, telemetry, source_config = render_sidebar_telemetry_inputs()
    qoe_preview = qoe_monitoring_agent(telemetry)
    playback_impact = None
    if source_config["mode"] == "Embedded HLS player":
        playback_impact = evaluate_playback_impact(telemetry, qoe_preview["qoe_status"])

    render_compact_header(
        band_config=band_config,
        aiml_ready=bool(get_secret("AIML_API_KEY")),
    )

    if source_config["mode"] == "Embedded HLS player":
        render_embedded_player_panel(
            stream_url=source_config["player_stream_url"],
            scenario=source_config["player_scenario"],
            refresh_interval_label=source_config["player_refresh_interval_label"],
            auto_refresh_enabled=source_config["player_refresh_enabled"],
            auto_run_enabled=source_config["player_auto_run_enabled"],
            telemetry=telemetry,
            qoe_preview=qoe_preview,
            refresh_epoch=st.session_state.player_last_refresh_epoch,
            playback_impact=playback_impact,
        )
        if st_autorefresh is None and source_config["player_refresh_enabled"]:
            st.info(
                "Auto-refresh dependency is unavailable in this environment. Use the manual refresh button to advance the embedded player telemetry."
            )

    default_agent_states = {
        "QoE Monitoring Agent": "waiting",
        "Diagnosis Agent": "waiting",
        "Recovery Action Agent": "waiting",
        "Customer Care Agent": "waiting",
    }
    action_summary = {
        "title": "Ready to analyze",
        "detail": "FlowWatch will monitor QoE, diagnose root cause, recommend safe actions, and prepare customer communication.",
        "priority": "Pending",
        "band": "Enabled" if band_config.enabled else "Disabled",
    }
    if source_config["mode"] == "Embedded HLS player" and playback_impact is not None:
        action_summary = {
            "title": {
                "Stable": "Playback stable",
                "At Risk": "QoE risk",
                "Impact Confirmed": "Impact confirmed",
                "Critical": "Critical impact",
            }.get(playback_impact["impact_status"], "Playback monitor"),
            "detail": {
                "Stable": "Monitoring only — no playback impact confirmed.",
                "At Risk": "QoE risk detected — watching for playback impact.",
                "Impact Confirmed": "Playback impact confirmed — diagnosis and recovery recommended.",
                "Critical": "Critical impact — full workflow recommended.",
            }.get(playback_impact["impact_status"], "Monitoring embedded playback telemetry."),
            "priority": "High"
            if playback_impact["impact_status"] in {"Impact Confirmed", "Critical"}
            else "Pending",
            "band": "Enabled" if band_config.enabled else "Disabled",
        }

    summary_placeholder = st.empty()
    with summary_placeholder.container():
        render_top_summary_cards(
            telemetry=telemetry,
            qoe_preview=qoe_preview,
            workflow_state=default_agent_states,
            band_config=band_config,
            action_summary=action_summary,
            show_incident_card=source_config["mode"] != "Embedded HLS player",
        )

    render_kpi_cards(telemetry)
    run_clicked = render_run_control()
    auto_triggered = False

    if (
        source_config["mode"] == "Embedded HLS player"
        and source_config["player_auto_run_enabled"]
        and playback_impact is not None
        and playback_impact["should_run_diagnosis"]
    ):
        incident_key = (
            f"{telemetry['customer_id']}|{telemetry['device_id']}|{qoe_preview['qoe_status']}|"
            f"{playback_impact['impact_status']}|"
            f"{source_config['player_scenario']}"
        )
        now = time.time()
        if (
            incident_key != st.session_state.last_player_auto_run_key
            or now - st.session_state.last_player_auto_run_ts >= 30
        ):
            st.session_state.last_player_auto_run_key = incident_key
            st.session_state.last_player_auto_run_ts = now
            auto_triggered = True
            st.info(
                f"{playback_impact['decision']} FlowWatch analysis triggered."
            )

    if run_clicked or auto_triggered:
        run_multi_agent_workflow(
            telemetry=telemetry,
            selected_model=selected_model,
            band_config=band_config,
            summary_placeholder=summary_placeholder,
            default_agent_states=default_agent_states,
            qoe_preview=qoe_preview,
            source_config=source_config,
            auto_triggered=auto_triggered,
            playback_impact=playback_impact,
        )
    else:
        if source_config["mode"] != "Embedded HLS player":
            render_empty_state()


if __name__ == "__main__":
    main()
