from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from models import BandConfig


def render_status_chip(label: str, tone: str = "neutral") -> str:
    return f'<span class="status-chip-ui {tone}">{label}</span>'


def render_compact_header(
    *,
    band_config: BandConfig,
    aiml_ready: bool,
) -> None:
    ai_chip = render_status_chip(
        "AI/ML API", "success" if aiml_ready else "warning"
    )
    band_chip = render_status_chip(
        "Band live"
        if band_config.enabled and band_config.api_key
        else "Band optional",
        "info" if band_config.enabled and band_config.api_key else "neutral",
    )
    streamlit_chip = render_status_chip("Streamlit", "neutral")

    st.markdown(
        f"""
        <section class="compact-header">
            <div class="header-badge">Telecom AI Command Center</div>
            <div class="header-main">
                <div>
                    <h1>FlowWatch</h1>
                    <p>Proactive TV streaming QoE monitoring with AI agents</p>
                </div>
                <div class="header-chip-row">
                    {ai_chip}
                    {band_chip}
                    {streamlit_chip}
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_workflow_stepper(workflow_state: dict[str, str]) -> str:
    steps = [
        ("QoE Monitoring Agent", "Monitor", "📡"),
        ("Diagnosis Agent", "Diagnose", "🧠"),
        ("Recovery Action Agent", "Recover", "🛠️"),
        ("Customer Care Agent", "Communicate", "💬"),
    ]
    parts: list[str] = []
    for index, (agent_name, label, icon) in enumerate(steps):
        state = workflow_state.get(agent_name, "waiting")
        parts.append(
            f'<div class="workflow-step {state}">'
            f'<div class="workflow-step-inner">'
            f'<div class="workflow-icon">{icon}</div>'
            f'<div class="workflow-copy">'
            f'<span class="workflow-label">{label}</span>'
            f'<span class="workflow-status">{state.title()}</span>'
            f"</div>"
            f"</div>"
            f"</div>"
        )
        if index < len(steps) - 1:
            connector_state = "active" if state in {"active", "done"} else "muted"
            parts.append(
                f'<div class="flow-connector {connector_state}"><span>→</span></div>'
            )
    return f'<div class="workflow-stepper">{"".join(parts)}</div>'


def render_top_summary_cards(
    *,
    telemetry: dict[str, Any],
    qoe_preview: dict[str, Any],
    workflow_state: dict[str, str],
    band_config: BandConfig,
    action_summary: dict[str, str] | None = None,
) -> None:
    qoe_status = qoe_preview["qoe_status"].lower()
    status_tone = {
        "good": "success",
        "warning": "warning",
        "poor": "critical",
    }.get(qoe_status, "neutral")
    action_summary = action_summary or {
        "title": "Ready to analyze",
        "detail": "Waiting to run the four-agent workflow.",
        "priority": "Pending",
        "band": "Enabled" if band_config.enabled else "Disabled",
    }

    cols = st.columns([1.05, 1.55, 1.15], gap="large")
    cols[0].markdown(
        f"""
        <div class="summary-card incident-card {qoe_status}">
            <p class="summary-eyebrow">Incident Health</p>
            <div class="incident-score">{telemetry['qoe_score']}</div>
            <div class="incident-status-row">
                {render_status_chip(qoe_preview['qoe_status'], status_tone)}
            </div>
            <div class="incident-meta">
                <span>{telemetry['customer_id']}</span>
                <span>{telemetry['service']}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols[1].markdown(
        f"""
        <div class="summary-card workflow-card">
            <p class="summary-eyebrow">Agent Workflow</p>
            {render_workflow_stepper(workflow_state)}
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols[2].markdown(
        f"""
        <div class="summary-card action-card">
            <p class="summary-eyebrow">Action Summary</p>
            <h3>{action_summary['title']}</h3>
            <p>{action_summary['detail']}</p>
            <div class="action-meta-row">
                {render_status_chip(f"Priority: {action_summary['priority']}", "warning")}
                {render_status_chip(f"Band: {action_summary['band']}", "info")}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_cards(telemetry: dict[str, Any]) -> None:
    metrics = [
        (
            "Bitrate",
            f"{float(telemetry['bitrate_mbps']):.1f} Mbps",
            _telemetry_tone("bitrate_mbps", telemetry["bitrate_mbps"]),
        ),
        (
            "Buffering",
            f"{float(telemetry['buffering_ratio']):.1f}%",
            _telemetry_tone("buffering_ratio", telemetry["buffering_ratio"]),
        ),
        (
            "Latency",
            f"{int(telemetry['latency_ms'])} ms",
            _telemetry_tone("latency_ms", telemetry["latency_ms"]),
        ),
        (
            "Packet Loss",
            f"{float(telemetry['packet_loss']):.1f}%",
            _telemetry_tone("packet_loss", telemetry["packet_loss"]),
        ),
        (
            "App Crashes",
            f"{int(telemetry['app_crashes'])}",
            _telemetry_tone("app_crashes", telemetry["app_crashes"]),
        ),
    ]
    cols = st.columns(5, gap="medium")
    for column, (label, value, tone) in zip(cols, metrics):
        column.markdown(
            f"""
            <div class="kpi-card {tone}">
                <p class="kpi-label">{label}</p>
                <div class="kpi-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_run_control() -> bool:
    left, center, right = st.columns([1, 1.2, 1], gap="large")
    with center:
        return st.button(
            "Run FlowWatch Analysis",
            type="primary",
            use_container_width=True,
        )


def render_empty_state() -> None:
    st.markdown(
        """
        <div class="empty-state-card">
            <h3>Ready to analyze this TV streaming session</h3>
            <p>
                FlowWatch will monitor QoE, diagnose root cause, recommend safe actions,
                and prepare customer communication.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_results_tabs(
    *,
    room_id: str,
    shared_context: dict[str, Any],
    communication_log: list[dict[str, Any]],
    band_result: dict[str, Any] | None,
    qoe_result: dict[str, Any],
    diagnosis_text: str | None,
    recovery_text: str | None,
    customer_care_text: str | None,
    telemetry: dict[str, Any],
) -> None:
    if diagnosis_text is None:
        tabs = st.tabs(["Monitor", "Band Trace", "Raw Telemetry"])
        with tabs[0]:
            render_agent_box("QoE Monitoring Agent", qoe_result, is_json=True)
        with tabs[1]:
            render_band_room(room_id, shared_context, communication_log, band_result)
        with tabs[2]:
            render_raw_telemetry_json(telemetry)
        return

    tabs = st.tabs(["Monitor", "Diagnose", "Recover", "Communicate", "Band Trace", "Raw Telemetry"])
    with tabs[0]:
        render_agent_box("QoE Monitoring Agent", qoe_result, is_json=True)
    with tabs[1]:
        render_agent_box("Diagnosis Agent", diagnosis_text)
    with tabs[2]:
        render_agent_box("Recovery Action Agent", recovery_text or "")
    with tabs[3]:
        render_agent_box("Customer Care Agent", customer_care_text or "")
    with tabs[4]:
        render_band_room(room_id, shared_context, communication_log, band_result)
    with tabs[5]:
        render_raw_telemetry_json(telemetry)


def render_agent_box(title: str, content: Any, is_json: bool = False) -> None:
    with st.container(border=False):
        st.markdown('<div class="result-card">', unsafe_allow_html=True)
        st.markdown(f"### {title}")
        if is_json:
            st.json(content)
        else:
            text_content = escape(str(content)).replace("\n", "<br>")
            st.markdown(
                f'<div class="result-copy">{text_content}</div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)


def render_band_room(
    room_id: str,
    shared_context: dict[str, Any],
    communication_log: list[dict[str, Any]],
    band_result: dict[str, Any] | None,
) -> None:
    with st.container(border=False):
        st.markdown('<div class="result-card">', unsafe_allow_html=True)
        st.subheader("Band Trace")

        live_note = "Live Band publishing was skipped for this run."
        if band_result and band_result.get("published"):
            live_note = f"Live Band room created successfully. Room ID: `{band_result['room_id']}`"
        elif band_result and band_result.get("error"):
            live_note = f"Band publish failed: {band_result['error']}"

        if band_result and band_result.get("published"):
            st.success(live_note)
        elif band_result and band_result.get("error"):
            st.warning(live_note)
        else:
            st.info(live_note)
        room_col, log_col = st.columns([1, 1.35], gap="large")

        with room_col:
            st.markdown("**Shared room context**")
            st.json(shared_context)
            if band_result:
                with st.expander("Band publish result"):
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
        st.markdown("</div>", unsafe_allow_html=True)


def render_raw_telemetry_json(telemetry: dict[str, Any]) -> None:
    with st.container(border=False):
        st.markdown('<div class="result-card">', unsafe_allow_html=True)
        st.subheader("Raw Telemetry")
        st.json(telemetry)
        st.markdown("</div>", unsafe_allow_html=True)


def _telemetry_tone(metric: str, value: float | int) -> str:
    if metric == "bitrate_mbps":
        return "good" if value >= 6 else "warn" if value >= 3 else "poor"
    if metric == "buffering_ratio":
        return "good" if value <= 1 else "warn" if value <= 5 else "poor"
    if metric == "latency_ms":
        return "good" if value <= 50 else "warn" if value <= 150 else "poor"
    if metric == "packet_loss":
        return "good" if value <= 0.5 else "warn" if value <= 2 else "poor"
    if metric == "app_crashes":
        return "good" if value == 0 else "warn" if value == 1 else "poor"
    return "neutral"
