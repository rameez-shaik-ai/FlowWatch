from __future__ import annotations

import re
import time
from typing import Any

import streamlit as st

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
from services.telemetry_service import load_live_telemetry
from ui.components import (
    render_compact_header,
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


def render_sidebar_telemetry_inputs() -> tuple[str, dict[str, Any]]:
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
            ["Manual", "Live API fetch"],
            index=0 if st.session_state.telemetry_source_mode == "Manual" else 1,
            label_visibility="collapsed",
        )

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

        st.markdown("### Telemetry Fields")
        telemetry_defaults = st.session_state.telemetry_values
        telemetry = {
            "customer_id": st.text_input("Customer ID", value=telemetry_defaults["customer_id"]),
            "device_id": st.text_input("Device ID", value=telemetry_defaults["device_id"]),
            "service": st.text_input("Service", value=telemetry_defaults["service"]),
            "bitrate_mbps": st.number_input(
                "Bitrate Mbps",
                min_value=0.0,
                value=float(telemetry_defaults["bitrate_mbps"]),
                step=0.1,
            ),
            "buffering_ratio": st.number_input(
                "Buffering ratio %",
                min_value=0.0,
                value=float(telemetry_defaults["buffering_ratio"]),
                step=0.1,
            ),
            "latency_ms": st.number_input(
                "Latency ms",
                min_value=0,
                value=int(telemetry_defaults["latency_ms"]),
                step=1,
            ),
            "packet_loss": st.number_input(
                "Packet loss %",
                min_value=0.0,
                value=float(telemetry_defaults["packet_loss"]),
                step=0.1,
            ),
            "app_crashes": st.number_input(
                "App crashes",
                min_value=0,
                value=int(telemetry_defaults["app_crashes"]),
                step=1,
            ),
        }

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

    return selected_model, telemetry


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
) -> None:
    room_id = f"band-room-{telemetry['customer_id'].lower()}"
    communication_log: list[dict[str, Any]] = []
    band_result: dict[str, Any] | None = None
    agent_states = dict(default_agent_states)

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
            payload=qoe_result,
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
            )
        shared_context = {
            "room_status": "Monitoring complete",
            "customer_id": telemetry["customer_id"],
            "service": telemetry["service"],
            "active_agents": ["QoE Monitoring Agent"],
            "latest_status": qoe_result["qoe_status"],
            "next_action": "Continue passive monitoring",
        }
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
            )
        time.sleep(0.15)

        recovery_text = recovery_action_agent(telemetry, diagnosis_text, selected_model)
        agent_states["Recovery Action Agent"] = "done"
        communication_log.append(
            create_band_event(
                step=3,
                sender="Recovery Action Agent",
                receiver="Customer Care Agent",
                event_type="handoff",
                summary="Shared recommended safe actions and monitoring plan.",
                payload={
                    "recovery_plan": recovery_text,
                    "selected_model": selected_model,
                    "customer_id": telemetry["customer_id"],
                },
            )
        )

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
        "title": "Proactive outreach",
        "detail": "The incident summary, next action, and customer communication are ready.",
        "priority": extract_priority_level(customer_care_text),
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
        "next_action": "Proactive outreach and continued monitoring",
    }
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
    band_config = build_band_config()
    selected_model, telemetry = render_sidebar_telemetry_inputs()
    qoe_preview = qoe_monitoring_agent(telemetry)

    render_compact_header(
        band_config=band_config,
        aiml_ready=bool(get_secret("AIML_API_KEY")),
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

    summary_placeholder = st.empty()
    with summary_placeholder.container():
        render_top_summary_cards(
            telemetry=telemetry,
            qoe_preview=qoe_preview,
            workflow_state=default_agent_states,
            band_config=band_config,
            action_summary=action_summary,
        )

    render_kpi_cards(telemetry)
    run_clicked = render_run_control()

    if run_clicked:
        run_multi_agent_workflow(
            telemetry=telemetry,
            selected_model=selected_model,
            band_config=band_config,
            summary_placeholder=summary_placeholder,
            default_agent_states=default_agent_states,
            qoe_preview=qoe_preview,
        )
    else:
        render_empty_state()


if __name__ == "__main__":
    main()
