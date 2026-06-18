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
from agents.incident_commander_agent import incident_commander_agent
from agents.qoe_monitoring_agent import qoe_monitoring_agent
from agents.recovery_action_agent import recovery_action_agent
from config import DEFAULT_MODEL, DEFAULT_TELEMETRY, MODEL_OPTIONS, get_secret
from services.band_service import (
    build_band_config,
    create_band_event,
    run_band_publish,
)
from services.playback_impact_gate import evaluate_playback_impact
from services.self_healing_service import (
    apply_post_healing_telemetry,
    get_restart_steps,
    get_healing_action_description,
    get_healing_action_label,
    sanitize_healing_action,
)
from services.player_service import (
    DEFAULT_HLS_STREAM_URL,
    generate_dynamic_player_telemetry,
    get_initial_player_telemetry,
    map_live_player_metrics_to_telemetry,
)
from services.telemetry_service import load_live_telemetry
from ui.components import (
    render_compact_header,
    render_decision_dashboard,
    render_embedded_player_panel,
    render_empty_state,
    render_kpi_cards,
    render_results_tabs,
    render_run_control,
    render_self_healing_approval_card,
    render_self_healing_result_card,
    render_top_summary_cards,
)
from ui.styles import apply_theme
from utils.qoe_scoring import (
    calculate_qoe_score,
    generate_ideal_telemetry,
    generate_random_telemetry,
)
from workflow.autonomous_orchestrator import (
    get_action_summary_from_commander,
    is_self_healing_eligible,
    should_run_agent,
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
    if "live_player_metrics" not in st.session_state:
        st.session_state.live_player_metrics = None
    if "commander_decision" not in st.session_state:
        st.session_state.commander_decision = None
    if "self_healing_status" not in st.session_state:
        st.session_state.self_healing_status = "none"
    if "self_healing_action" not in st.session_state:
        st.session_state.self_healing_action = None
    if "self_healing_result" not in st.session_state:
        st.session_state.self_healing_result = None
    if "post_healing_telemetry" not in st.session_state:
        st.session_state.post_healing_telemetry = None
    if "post_healing_playback_impact" not in st.session_state:
        st.session_state.post_healing_playback_impact = None
    if "self_healing_log" not in st.session_state:
        st.session_state.self_healing_log = []
    if "workflow_visible" not in st.session_state:
        st.session_state.workflow_visible = False
    if "approval_popup_armed" not in st.session_state:
        st.session_state.approval_popup_armed = False
    if "player_refresh_paused" not in st.session_state:
        st.session_state.player_refresh_paused = False
    if "agent_workflow_running" not in st.session_state:
        st.session_state.agent_workflow_running = False
    if "previous_telemetry_source_mode" not in st.session_state:
        st.session_state.previous_telemetry_source_mode = st.session_state.telemetry_source_mode
    if "previous_player_scenario" not in st.session_state:
        st.session_state.previous_player_scenario = st.session_state.player_scenario


def clear_workflow_state() -> None:
    st.session_state.self_healing_status = "none"
    st.session_state.self_healing_action = None
    st.session_state.self_healing_result = None
    st.session_state.post_healing_telemetry = None
    st.session_state.post_healing_playback_impact = None
    st.session_state.self_healing_log = []
    st.session_state.commander_decision = None
    st.session_state.last_player_auto_run_key = ""
    st.session_state.last_player_auto_run_ts = 0.0
    st.session_state.workflow_visible = False
    st.session_state.approval_popup_armed = False
    st.session_state.player_refresh_paused = False
    st.session_state.agent_workflow_running = False


def reset_demo_state() -> None:
    st.session_state.telemetry_values = DEFAULT_TELEMETRY.copy()
    st.session_state.live_player_metrics = None
    st.session_state.player_tick = 0
    st.session_state.player_last_refresh_epoch = time.time()
    clear_workflow_state()

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
        if (
            st.session_state.previous_telemetry_source_mode
            != st.session_state.telemetry_source_mode
        ):
            st.session_state.previous_telemetry_source_mode = (
                st.session_state.telemetry_source_mode
            )
            st.session_state.previous_player_scenario = st.session_state.player_scenario
            reset_demo_state()
            st.rerun()
        if st.button("Reset demo", use_container_width=True):
            reset_demo_state()
            st.rerun()

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
                    random_telemetry = generate_random_telemetry()
                    clear_workflow_state()
                    st.session_state.telemetry_values = random_telemetry
                    st.session_state.approval_popup_armed = random_telemetry["qoe_score"] < 80
                    st.rerun()
            with ideal_col:
                if st.button("Ideal", use_container_width=True):
                    clear_workflow_state()
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
                ["Auto", "Healthy", "Degraded", "Recovering", "Live"],
                index=["Auto", "Healthy", "Degraded", "Recovering", "Live"].index(
                    st.session_state.player_scenario
                ),
            )
            if st.session_state.previous_player_scenario != st.session_state.player_scenario:
                st.session_state.previous_player_scenario = st.session_state.player_scenario
                st.session_state.live_player_metrics = None
                st.session_state.player_tick = 0
                st.session_state.player_last_refresh_epoch = time.time()
                clear_workflow_state()
                st.rerun()
            st.session_state.player_auto_run_enabled = st.toggle(
                "Auto-run agent analysis when QoE is Poor",
                value=st.session_state.player_auto_run_enabled,
            )
            if st.button("Refresh player telemetry", use_container_width=True):
                st.session_state.player_refresh_paused = False
                st.session_state.workflow_visible = False
                st.session_state.player_tick += 1
                st.session_state.player_last_refresh_epoch = time.time()
                st.rerun()
            if st.session_state.player_scenario != "Live":
                st.session_state.telemetry_values = generate_dynamic_player_telemetry(
                    st.session_state.player_tick,
                    st.session_state.player_scenario,
                )
            elif "player_state" not in st.session_state.telemetry_values:
                st.session_state.telemetry_values = get_initial_player_telemetry()
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
    commander_decision: dict[str, Any] | None = None,
    self_healing_result: dict[str, Any] | None = None,
) -> None:
    st.session_state.agent_workflow_running = True
    room_id = f"band-room-{telemetry['customer_id'].lower()}"
    communication_log: list[dict[str, Any]] = []
    if st.session_state.self_healing_log:
        communication_log.extend(st.session_state.self_healing_log)
    band_result: dict[str, Any] | None = None
    agent_states = dict(default_agent_states)
    embedded_mode = source_config["mode"] == "Embedded HLS player"
    commander_decision = commander_decision or {
        "decision": "monitor_only",
        "severity": "Low",
        "band_room_required": False,
        "agents_to_run": [],
        "customer_care_required": False,
    }
    allow_customer_care = should_run_agent(commander_decision, "Customer Care Agent")
    run_diagnosis = should_run_agent(commander_decision, "Diagnosis Agent")
    run_recovery = should_run_agent(commander_decision, "Recovery Action Agent")

    action_summary = get_action_summary_from_commander(commander_decision)
    if st.session_state.self_healing_status == "pending":
        action_summary["detail"] = "Waiting for approval"
    elif st.session_state.self_healing_status == "completed":
        action_summary["detail"] = "Self-healing completed"
    elif st.session_state.self_healing_status == "approved":
        action_summary["detail"] = "Diagnosis and recovery running"
    elif st.session_state.self_healing_status == "rejected":
        action_summary["detail"] = "Monitoring only"
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

    try:
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
        communication_log.append(
            create_band_event(
                step=len(communication_log) + 1,
                sender="Incident Commander Agent",
                receiver=", ".join(commander_decision.get("agents_to_run", [])) or "Monitoring Console",
                event_type="decision",
                summary=(
                    f"Selected {commander_decision.get('decision', 'monitor_only')} "
                    f"with severity {commander_decision.get('severity', 'Low')}."
                ),
                payload=commander_decision,
            )
        )

        if not run_diagnosis and not run_recovery and not allow_customer_care:
            action_summary = get_action_summary_from_commander(commander_decision)
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
                "next_action": commander_decision.get("next_step", "Continue passive monitoring"),
                "commander_decision": commander_decision,
                "self_healing": self_healing_result,
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
                playback_impact=playback_impact,
                commander_decision=commander_decision,
                self_healing_result=self_healing_result,
            )
            st.success(
                "Commander kept this incident in monitoring mode. No further agent escalation is required right now."
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
                commander_decision=commander_decision,
                self_healing_result=self_healing_result,
            )
            return

        with st.spinner("Running diagnosis, recovery, customer care, and Band sync..."):
            diagnosis_text = None
            if run_diagnosis:
                agent_states["Diagnosis Agent"] = "active"
                action_summary = {
                    "title": "Diagnosis running",
                    "detail": "Commander assigned Diagnosis Agent to identify the likely root cause.",
                    "priority": commander_decision.get("severity", "Medium"),
                    "band": "Required" if commander_decision.get("band_room_required") else "Optional",
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
                diagnosis_text = diagnosis_agent(telemetry, qoe_result, selected_model)
                agent_states["Diagnosis Agent"] = "done"
                communication_log.append(
                    create_band_event(
                        step=len(communication_log) + 1,
                        sender="Diagnosis Agent",
                        receiver="Recovery Action Agent" if run_recovery else "Support Operations",
                        event_type="handoff",
                        summary="Published root cause assessment to the shared collaboration layer.",
                        payload={
                            "diagnosis_summary": diagnosis_text,
                            "customer_id": telemetry["customer_id"],
                            "qoe_status": qoe_result["qoe_status"],
                        },
                    )
                )

            recovery_text = None
            if run_recovery:
                agent_states["Recovery Action Agent"] = "active"
                action_summary = {
                    "title": "Recovery planning",
                    "detail": "Commander assigned Recovery Action Agent to prepare safe remediation guidance.",
                    "priority": commander_decision.get("severity", "High"),
                    "band": "Required" if commander_decision.get("band_room_required") else "Optional",
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
                recovery_text = recovery_action_agent(
                    telemetry,
                    diagnosis_text or qoe_result["customer_impact_summary"],
                    selected_model,
                )
                agent_states["Recovery Action Agent"] = "done"
                communication_log.append(
                    create_band_event(
                        step=len(communication_log) + 1,
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
                        step=len(communication_log) + 1,
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
                playback_impact=playback_impact,
                commander_decision=commander_decision,
                self_healing_result=self_healing_result,
            )
        action_summary = {
            "title": "Proactive outreach" if allow_customer_care else get_action_summary_from_commander(commander_decision)["title"],
            "detail": (
                "The incident summary, next action, and customer communication are ready."
                if allow_customer_care
                else commander_decision.get("next_step", "Diagnosis and recovery are complete.")
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
                *([name for name in ["Diagnosis Agent", "Recovery Action Agent", "Customer Care Agent"] if should_run_agent(commander_decision, name)]),
            ],
            "latest_status": qoe_result["qoe_status"],
            "selected_model": selected_model,
            "next_action": commander_decision.get("next_step", "Continue monitoring"),
            "commander_decision": commander_decision,
            "self_healing": self_healing_result,
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
            commander_decision=commander_decision,
            self_healing_result=self_healing_result,
        )
        st.success(
            "FlowWatch analysis complete. The commander-led workflow and Band collaboration trace are ready for demo."
        )
    finally:
        st.session_state.agent_workflow_running = False


def main() -> None:
    st.set_page_config(page_title="FlowWatch", page_icon="📺", layout="wide")
    apply_theme()
    initialize_session_state()

    if (
        st.session_state.telemetry_source_mode == "Embedded HLS player"
        and st.session_state.player_refresh_enabled
        and st.session_state.player_scenario != "Live"
        and not st.session_state.player_refresh_paused
        and not st.session_state.agent_workflow_running
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
    telemetry["source_mode"] = source_config["mode"]
    live_metrics_status = None
    if (
        source_config["mode"] == "Embedded HLS player"
        and source_config["player_scenario"] == "Live"
    ):
        latest_live_metrics = st.session_state.live_player_metrics
        if latest_live_metrics and (
            int(latest_live_metrics.get("last_update_epoch_ms", 0) or 0)
            >= int((time.time() - 6) * 1000)
        ):
            live_metrics_status = "received"
        else:
            live_metrics_status = "waiting"
        telemetry = map_live_player_metrics_to_telemetry(
            st.session_state.live_player_metrics,
            st.session_state.telemetry_values,
        )
        telemetry["source_mode"] = source_config["mode"]
        st.session_state.telemetry_values = telemetry.copy()
    qoe_preview = qoe_monitoring_agent(telemetry)
    playback_impact = None
    if source_config["mode"] == "Embedded HLS player":
        playback_impact = evaluate_playback_impact(telemetry, qoe_preview["qoe_status"])
    commander_decision = incident_commander_agent(
        telemetry,
        qoe_preview,
        playback_impact,
        selected_model,
    )
    requested_healing_action = commander_decision.get("recommended_healing_action", "none")
    commander_decision["recommended_healing_action"] = sanitize_healing_action(
        requested_healing_action
    )
    if (
        source_config["mode"] == "Manual"
        and st.session_state.approval_popup_armed
        and qoe_preview.get("qoe_status") == "Poor"
    ):
        commander_decision = {
            **commander_decision,
            "decision": "self_heal",
            "severity": "High",
            "band_room_required": True,
            "agents_to_run": ["Diagnosis Agent", "Recovery Action Agent"],
            "customer_care_required": False,
            "human_approval_required": True,
            "recommended_healing_action": "refresh_streaming_session",
            "reason": "Manual demo mode detected Poor QoE, so FlowWatch is requesting operator approval for a safe recovery action.",
            "next_step": "Approve the streaming session refresh to continue the assisted recovery workflow.",
        }
    st.session_state.commander_decision = commander_decision
    self_healing_eligible = is_self_healing_eligible(
        source_config=source_config,
        telemetry=telemetry,
        qoe_preview=qoe_preview,
        playback_impact=playback_impact,
        commander_decision=commander_decision,
    )
    if (
        self_healing_eligible
        and st.session_state.approval_popup_armed
        and st.session_state.self_healing_status in {"none", "pending"}
    ):
        st.session_state.self_healing_status = "pending"
        st.session_state.self_healing_result = {
            "action": commander_decision["recommended_healing_action"],
            "action_label": get_healing_action_label(
                commander_decision["recommended_healing_action"]
            ),
            "description": get_healing_action_description(
                commander_decision["recommended_healing_action"]
            ),
            "approval_required": commander_decision.get("human_approval_required", False),
            "status": "pending",
            "execution_status": "Awaiting approval",
            "post_healing_qoe_status": None,
            "post_healing_playback_impact": None,
        }
        st.session_state.self_healing_log = [
            create_band_event(
                step=1,
                sender="Incident Commander Agent",
                receiver="Operator Approval",
                event_type="approval_request",
                summary="Self-healing approval requested.",
                payload=st.session_state.self_healing_result,
            )
        ]
    elif not self_healing_eligible and st.session_state.self_healing_status == "pending":
        clear_workflow_state()

    render_compact_header(
        band_config=band_config,
        aiml_ready=bool(get_secret("AIML_API_KEY")),
    )
    if requested_healing_action != commander_decision["recommended_healing_action"]:
        st.warning(
            f"Commander requested unsupported healing action `{requested_healing_action}`. "
            "FlowWatch blocked it and kept the action set to `none`."
        )

    if source_config["mode"] == "Embedded HLS player":
        live_metrics = render_embedded_player_panel(
            stream_url=source_config["player_stream_url"],
            scenario=source_config["player_scenario"],
            refresh_interval_label=source_config["player_refresh_interval_label"],
            auto_refresh_enabled=source_config["player_refresh_enabled"],
            auto_run_enabled=source_config["player_auto_run_enabled"],
            telemetry=telemetry,
            qoe_preview=qoe_preview,
            refresh_epoch=st.session_state.player_last_refresh_epoch,
            playback_impact=playback_impact,
            live_metrics_status=live_metrics_status,
        )
        if source_config["player_scenario"] == "Live":
            if live_metrics is not None:
                st.session_state.live_player_metrics = live_metrics
                st.session_state.player_last_refresh_epoch = time.time()
        if (
            st_autorefresh is None
            and source_config["player_refresh_enabled"]
            and source_config["player_scenario"] != "Live"
        ):
            st.info(
                "Auto-refresh dependency is unavailable in this environment. Use the manual refresh button to advance the embedded player telemetry."
            )

    render_decision_dashboard(
        telemetry=telemetry,
        qoe_preview=qoe_preview,
        playback_impact=playback_impact,
        commander_decision=commander_decision,
        source_config=source_config,
    )

    default_agent_states = {
        "QoE Monitoring Agent": "waiting",
        "Diagnosis Agent": "waiting",
        "Recovery Action Agent": "waiting",
        "Customer Care Agent": "waiting",
    }
    action_summary = get_action_summary_from_commander(commander_decision)
    if st.session_state.self_healing_status == "pending":
        action_summary["detail"] = "Waiting for approval"
    elif st.session_state.self_healing_status == "completed":
        action_summary["detail"] = "Self-healing completed"
    elif st.session_state.self_healing_status == "approved":
        action_summary["detail"] = "Diagnosis and recovery running"
    elif st.session_state.self_healing_status == "rejected":
        action_summary["detail"] = "Monitoring only"

    render_kpi_cards(telemetry)
    summary_placeholder = st.empty()
    with summary_placeholder.container():
        render_top_summary_cards(
            telemetry=telemetry,
            qoe_preview=qoe_preview,
            workflow_state=default_agent_states,
            band_config=band_config,
            action_summary=action_summary,
            show_incident_card=False,
        )

    approval_response = None
    if self_healing_eligible and st.session_state.self_healing_status == "pending":
        approval_response = render_self_healing_approval_card(commander_decision)

    if approval_response == "approved":
        action = commander_decision["recommended_healing_action"]
        action_label = get_healing_action_label(action)
        st.session_state.approval_popup_armed = False
        st.session_state.self_healing_status = "approved"
        st.session_state.self_healing_action = action
        st.session_state.workflow_visible = True
        st.session_state.self_healing_log.append(
            create_band_event(
                step=len(st.session_state.self_healing_log) + 1,
                sender="Operator Approval",
                receiver="Self-Healing Service",
                event_type="approval_response",
                summary=f"{action_label} approved.",
                payload={"action": action, "status": "approved"},
            )
        )
        progress = st.progress(0)
        status_box = st.empty()
        steps = get_restart_steps()
        for index, step in enumerate(steps, start=1):
            status_box.info(step)
            time.sleep(0.75)
            progress.progress(int(index / len(steps) * 100))
        healed_telemetry = apply_post_healing_telemetry(telemetry)
        healed_qoe = qoe_monitoring_agent(healed_telemetry)
        healed_playback = (
            evaluate_playback_impact(healed_telemetry, healed_qoe["qoe_status"])
            if source_config["mode"] == "Embedded HLS player"
            else None
        )
        st.session_state.telemetry_values = healed_telemetry.copy()
        st.session_state.self_healing_status = "completed"
        st.session_state.self_healing_action = action
        st.session_state.post_healing_telemetry = healed_telemetry
        st.session_state.post_healing_playback_impact = healed_playback
        st.session_state.self_healing_result = {
            "action": action,
            "action_label": action_label,
            "description": get_healing_action_description(action),
            "approval_required": True,
            "status": "completed",
            "execution_status": f"{action_label} simulation completed",
            "post_healing_qoe_status": healed_qoe["qoe_status"],
            "post_healing_qoe_score": healed_telemetry["qoe_score"],
            "post_playback_impact_status": healed_playback["impact_status"] if healed_playback else None,
            "post_healing_playback_impact": healed_playback,
            "post_healing_telemetry": healed_telemetry,
        }
        st.session_state.self_healing_log.extend(
            [
                create_band_event(
                    step=len(st.session_state.self_healing_log) + 1,
                    sender="Self-Healing Service",
                    receiver="Incident Commander Agent",
                    event_type="execution",
                    summary=f"{action_label} simulation completed.",
                    payload=st.session_state.self_healing_result,
                ),
                create_band_event(
                    step=len(st.session_state.self_healing_log) + 2,
                    sender="QoE Monitoring Agent",
                    receiver="Playback Impact Gate",
                    event_type="recheck",
                    summary="Post-healing QoE and playback impact re-evaluated.",
                    payload={
                        "post_qoe_status": healed_qoe["qoe_status"],
                        "post_qoe_score": healed_telemetry["qoe_score"],
                        "post_playback_impact_status": healed_playback["impact_status"] if healed_playback else None,
                    },
                ),
            ]
        )
        st.success(f"{action_label} completed. FlowWatch is monitoring playback recovery.")
        st.rerun()
    elif approval_response == "rejected":
        st.session_state.approval_popup_armed = False
        st.session_state.self_healing_status = "rejected"
        st.session_state.self_healing_action = commander_decision["recommended_healing_action"]
        st.session_state.workflow_visible = True
        st.session_state.self_healing_result = {
            "action": commander_decision["recommended_healing_action"],
            "action_label": get_healing_action_label(commander_decision["recommended_healing_action"]),
            "description": get_healing_action_description(commander_decision["recommended_healing_action"]),
            "approval_required": True,
            "status": "rejected",
            "execution_status": "Operator rejected the self-healing action",
            "post_healing_qoe_status": None,
            "post_healing_playback_impact": None,
        }
        st.session_state.self_healing_log.append(
            create_band_event(
                step=len(st.session_state.self_healing_log) + 1,
                sender="Operator Approval",
                receiver="Incident Commander Agent",
                event_type="approval_response",
                summary="Self-healing was rejected.",
                payload=st.session_state.self_healing_result,
            )
        )
        st.warning("Self-healing was rejected. FlowWatch will continue monitoring and may recommend customer care or escalation.")

    if st.session_state.self_healing_status in {"approved", "completed", "rejected"}:
        render_self_healing_result_card(st.session_state.self_healing_result)
    run_clicked = False if st.session_state.self_healing_status == "pending" else render_run_control()
    auto_triggered = False

    if run_clicked and self_healing_eligible and st.session_state.self_healing_status == "none":
        st.session_state.approval_popup_armed = True
        st.rerun()

    if (
        source_config["mode"] == "Embedded HLS player"
        and source_config["player_auto_run_enabled"]
        and not st.session_state.player_refresh_paused
        and not st.session_state.agent_workflow_running
        and playback_impact is not None
        and playback_impact["should_run_diagnosis"]
        and commander_decision.get("decision") in {"diagnose", "self_heal", "customer_care", "escalate"}
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
            st.session_state.player_refresh_paused = True
            auto_triggered = True
            st.session_state.workflow_visible = True
            st.info(
                f"{commander_decision['decision'].replace('_', ' ').title()} triggered automatically."
            )

    if run_clicked or auto_triggered:
        st.session_state.workflow_visible = True
        if source_config["mode"] == "Embedded HLS player":
            st.session_state.player_refresh_paused = True
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
            commander_decision=commander_decision,
            self_healing_result=st.session_state.self_healing_result,
        )
    else:
        if st.session_state.self_healing_status in {"completed", "rejected"}:
            render_results_tabs(
                room_id=f"band-room-{telemetry['customer_id'].lower()}",
                shared_context={
                    "room_status": "Self-healing completed"
                    if st.session_state.self_healing_status == "completed"
                    else "Self-healing rejected",
                    "customer_id": telemetry["customer_id"],
                    "device_id": telemetry["device_id"],
                    "service": telemetry["service"],
                    "commander_decision": commander_decision,
                    "self_healing": st.session_state.self_healing_result,
                    "next_action": commander_decision.get("next_step", "Continue monitoring"),
                },
                communication_log=st.session_state.self_healing_log,
                band_result=None,
                qoe_result=qoe_preview,
                diagnosis_text=None,
                recovery_text=None,
                customer_care_text=None,
                telemetry=telemetry,
                commander_decision=commander_decision,
                self_healing_result=st.session_state.self_healing_result,
            )
        elif (
            source_config["mode"] != "Embedded HLS player"
            and st.session_state.self_healing_status
            not in {"pending", "approved", "completed", "rejected"}
        ):
            render_empty_state()


if __name__ == "__main__":
    main()
