from __future__ import annotations

from html import escape
import time
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from components.hls_telemetry_player import hls_telemetry_player
from models import BandConfig
from services.player_service import build_hls_player_html


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
    state_labels = {
        "waiting": "Waiting",
        "active": "Running",
        "done": "Done",
        "fallback_used": "Fallback",
        "failed": "Failed",
    }
    for index, (agent_name, label, icon) in enumerate(steps):
        state = workflow_state.get(agent_name, "waiting")
        parts.append(
            f'<div class="workflow-step {state}">'
            f'<div class="workflow-step-inner">'
            f'<div class="workflow-icon">{icon}</div>'
            f'<div class="workflow-copy">'
            f'<span class="workflow-label">{label}</span>'
            f'<span class="workflow-status">{state_labels.get(state, "Waiting")}</span>'
            f"</div>"
            f"</div>"
            f"</div>"
        )
        if index < len(steps) - 1:
            connector_state = (
                "active" if state in {"active", "done", "fallback_used"} else "muted"
            )
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
    show_incident_card: bool = True,
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

    if show_incident_card:
        cols = st.columns([0.95, 2.05], gap="large")
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
        workflow_column = cols[1]
    else:
        workflow_column = st.container()

    workflow_column.markdown(
        f"""
        <div class="summary-card workflow-card">
            <div class="workflow-topline">
                <p class="summary-eyebrow">Agent Workflow</p>
                <div class="workflow-live-chip">{action_summary['title']}</div>
            </div>
            {render_workflow_stepper(workflow_state)}
            <div class="workflow-activity-panel">
                <p class="workflow-activity-text">{action_summary['detail']}</p>
                <div class="action-meta-row">
                    {render_status_chip(f"Priority: {action_summary['priority']}", "warning")}
                    {render_status_chip(f"Band: {action_summary['band']}", "info")}
                </div>
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


def render_run_control(*, primary: bool = True) -> bool:
    left, center, right = st.columns([1, 1.2, 1], gap="large")
    with center:
        return st.button(
            "Run FlowWatch Analysis",
            type="primary" if primary else "secondary",
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


def render_decision_dashboard(
    telemetry: dict[str, Any],
    qoe_preview: dict[str, Any],
    playback_impact: dict[str, Any] | None,
    commander_decision: dict[str, Any],
    source_config: dict[str, Any],
) -> None:
    qoe_status = str(qoe_preview.get("qoe_status", "Unknown"))
    qoe_tone = {
        "Good": "success",
        "Warning": "warning",
        "Poor": "critical",
    }.get(qoe_status, "neutral")
    decision = str(commander_decision.get("decision", "monitor_only")).replace("_", " ").title()
    action = str(commander_decision.get("recommended_healing_action", "none")).replace("_", " ").title()
    approval_required = "Yes" if commander_decision.get("human_approval_required") else "No"
    mode = source_config.get("mode")
    impact_label = "Manual Impact"
    impact_value = "Based on QoE and severe telemetry symptoms"
    impact_score = None
    if mode == "Embedded HLS player" and playback_impact is not None:
        impact_label = "Playback Impact"
        impact_value = str(playback_impact.get("impact_status", "Unknown"))
        impact_score = playback_impact.get("impact_score")

    cards: list[tuple[str, str, str]] = [
        ("QoE Score", str(int(telemetry.get("qoe_score", 0))), "neutral"),
        ("QoE Status", qoe_status, qoe_tone),
        (impact_label, impact_value, "neutral"),
        ("Commander Decision", decision, "info"),
        ("Recommended Action", action, "warning" if action.lower() != "none" else "neutral"),
        ("Approval Required", approval_required, "warning" if approval_required == "Yes" else "success"),
    ]
    if impact_score is not None:
        cards.insert(3, ("Impact Score", str(int(impact_score)), "neutral"))

    cols = st.columns(len(cards), gap="small")
    for column, (label, value, tone) in zip(cols, cards):
        column.markdown(
            f"""
            <div class="kpi-card dashboard-card {tone}">
                <p class="kpi-label">{escape(label)}</p>
                <div class="dashboard-value">{escape(value)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_commander_decision_card(commander_decision: dict[str, Any] | None) -> None:
    if not commander_decision:
        return
    decision = str(commander_decision.get("decision", "monitor_only")).replace("_", " ").title()
    severity = str(commander_decision.get("severity", "Low"))
    tone = {
        "Low": "success",
        "Medium": "warning",
        "High": "warning",
        "Critical": "critical",
    }.get(severity, "neutral")
    approval = "Required" if commander_decision.get("human_approval_required") else "Not required"
    action = str(commander_decision.get("recommended_healing_action", "none")).replace("_", " ").title()
    st.markdown(
        f"""
        <div class="summary-card commander-card">
            <div class="impact-gate-head">
                <p class="summary-eyebrow">Autonomous Decision</p>
                {render_status_chip(severity, tone)}
            </div>
            <div class="impact-gate-copy">
                <div><span>Commander decision</span><strong>{escape(decision)}</strong></div>
                <div><span>Recommended action</span><strong>{escape(action)}</strong></div>
                <div><span>Approval</span><strong>{escape(approval)}</strong></div>
                <div><span>Next step</span><strong>{escape(str(commander_decision.get('next_step', 'Continue monitoring.')))}</strong></div>
            </div>
            <div class="result-copy">{escape(str(commander_decision.get("reason", "")))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_self_healing_approval_card(commander_decision: dict[str, Any]) -> str | None:
    if not commander_decision:
        return None
    action = str(commander_decision.get("recommended_healing_action", "none"))
    decision = str(commander_decision.get("decision", "monitor_only"))
    if (
        decision not in {"self_heal", "escalate"}
        or action == "none"
        or not commander_decision.get("human_approval_required")
    ):
        return None
    approve_label = (
        "Approve Refresh" if action == "refresh_streaming_session" else "Approve Restart"
    )
    action_label = "refreshing the streaming session" if action == "refresh_streaming_session" else "restarting the streaming app"

    st.markdown(
        f"""
        <div class="summary-card commander-card">
            <div class="impact-gate-head">
                <p class="summary-eyebrow">Self-healing approval required</p>
                {render_status_chip("Approval required", "warning")}
            </div>
            <div class="result-copy">
                FlowWatch recommends {escape(action_label)} to restore playback stability.<br><br>
                <strong>Why this action?</strong><br>
                Playback impact was confirmed and this is a safe session-level recovery action.<br><br>
                <strong>Reason:</strong> {escape(str(commander_decision.get("reason", "Safe recovery was recommended.")))}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    approve_col, reject_col = st.columns(2, gap="small")
    with approve_col:
        if st.button(approve_label, type="primary", use_container_width=True):
            return "approved"
    with reject_col:
        if st.button("Reject", use_container_width=True):
            return "rejected"
    return None


def render_self_healing_result_card(self_healing_result: dict[str, Any] | None) -> None:
    if not self_healing_result:
        return
    status = str(self_healing_result.get("status", "pending")).title()
    tone = {
        "Completed": "success",
        "Rejected": "warning",
        "Approved": "info",
        "Pending": "warning",
    }.get(status, "neutral")
    action = escape(str(self_healing_result.get("action_label") or self_healing_result.get("action", "none")).replace("_", " ").title())
    approval_status = "Required" if self_healing_result.get("approval_required") else "Not required"
    execution = escape(str(self_healing_result.get("execution_status", "Awaiting action")))
    post_qoe = self_healing_result.get("post_healing_qoe_score")
    post_qoe_status = self_healing_result.get("post_healing_qoe_status")
    post_impact = self_healing_result.get("post_healing_playback_impact")
    if isinstance(post_impact, dict):
        post_impact = post_impact.get("impact_status")

    st.markdown(
        f"""
        <div class="summary-card commander-card">
            <div class="impact-gate-head">
                <p class="summary-eyebrow">Self-healing result</p>
                {render_status_chip(status, tone)}
            </div>
            <div class="impact-gate-copy">
                <div><span>Action</span><strong>{action}</strong></div>
                <div><span>Approval status</span><strong>{escape(approval_status)}</strong></div>
                <div><span>Execution</span><strong>{execution}</strong></div>
                <div><span>Post-healing QoE</span><strong>{escape(str(post_qoe)) if post_qoe is not None else "-"}</strong></div>
                <div><span>Post-healing status</span><strong>{escape(str(post_qoe_status or '-'))}</strong></div>
                <div><span>Playback impact</span><strong>{escape(str(post_impact or '-'))}</strong></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_embedded_player_panel(
    *,
    stream_url: str,
    scenario: str,
    refresh_interval_label: str,
    auto_refresh_enabled: bool,
    auto_run_enabled: bool,
    telemetry: dict[str, Any],
    qoe_preview: dict[str, Any],
    refresh_epoch: float,
    playback_impact: dict[str, Any] | None = None,
    live_metrics_status: str | None = None,
) -> dict[str, Any] | None:
    qoe_status = qoe_preview["qoe_status"]
    qoe_tone = {
        "Good": "success",
        "Warning": "warning",
        "Poor": "critical",
    }.get(qoe_status, "neutral")
    impact = playback_impact or {}
    impact_status = impact.get("impact_status", "Unknown")
    impact_tone = {
        "Stable": "success",
        "At Risk": "warning",
        "Impact Confirmed": "critical",
        "Critical": "critical",
    }.get(impact_status, "neutral")
    impact_reasons = impact.get("reasons", [])
    dropped_frame_ratio = float(impact.get("dropped_frame_ratio", 0.0)) * 100

    left, right = st.columns([1.7, 1], gap="large")
    live_metrics = None
    with left:
        st.markdown(
            f"""
            <div class="player-wrapper">
                <div class="player-panel-head">
                    <div>
                        <p class="summary-eyebrow">Embedded HLS Player</p>
                        <p class="player-panel-copy">
                            Live browser playback preview with JavaScript telemetry inside the player.
                        </p>
                    </div>
                    <div class="player-panel-meta">
                        {render_status_chip(f"Scenario: {scenario}", "success")}
                        {render_status_chip(f"Refresh: {refresh_interval_label if auto_refresh_enabled else 'Manual'}", "info")}
                        {render_status_chip(f"Auto-analysis: {'On' if auto_run_enabled else 'Off'}", "neutral")}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if not stream_url.strip():
            st.warning("Add an HLS stream URL to render the embedded player.")
        elif scenario == "Live":
            live_metrics = hls_telemetry_player(
                stream_url=stream_url,
                refresh_interval_ms=2000
                if refresh_interval_label == "2 seconds"
                else 3000
                if refresh_interval_label == "3 seconds"
                else 5000,
                height=620,
                key=f"flowwatch-live-hls-{stream_url}",
            )
        else:
            components.html(build_hls_player_html(stream_url), height=590)
        if scenario == "Live":
            tone = "success" if live_metrics_status == "received" else "neutral"
            label = (
                "Live player metrics received"
                if live_metrics_status == "received"
                else "Waiting for live player metrics. Press play on the video."
            )
            st.markdown(render_status_chip(label, tone), unsafe_allow_html=True)

    refresh_label = "Just now"
    if refresh_epoch:
        refresh_label = f"{max(0, int(time.time() - refresh_epoch))}s ago"

    with right:
        st.markdown(
            f"""
            <div class="summary-card impact-gate-card">
                <div class="impact-gate-head">
                    <p class="summary-eyebrow">Playback Impact Gate</p>
                    {render_status_chip(impact_status, impact_tone)}
                </div>
                <div class="impact-qoe-row">
                    <div class="impact-qoe-block">
                        <span>QoE</span>
                        <strong>{int(telemetry['qoe_score'])}</strong>
                        {render_status_chip(qoe_status, qoe_tone)}
                    </div>
                    <div class="impact-qoe-block impact-meta-block">
                        <span>Last refresh</span>
                        <strong>{escape(refresh_label)}</strong>
                    </div>
                </div>
                <div class="impact-gate-copy">
                    <div><span>Decision</span><strong>{escape(str(impact.get('decision', 'Monitoring embedded playback impact.')))}</strong></div>
                    <div><span>Impact score</span><strong>{int(impact.get('impact_score', 0))}</strong></div>
                </div>
                <div class="impact-gate-grid">
                    <div><span>Buffered ahead</span><strong>{float(telemetry.get('buffered_ahead_seconds', 0.0)):.1f}s</strong></div>
                    <div><span>Player state</span><strong>{escape(str(telemetry.get('player_state', '-')))}</strong></div>
                    <div><span>Dropped-frame ratio</span><strong>{dropped_frame_ratio:.1f}%</strong></div>
                    <div><span>Stall events</span><strong>{int(telemetry.get('stall_count', 0))}</strong></div>
                    <div><span>Resolution</span><strong>{escape(str(telemetry.get('resolution', '-')))}</strong></div>
                    <div><span>Playback moving</span><strong>{'Yes' if telemetry.get('playback_time_moving') else 'No'}</strong></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if impact_reasons:
            with st.expander("Why this decision?"):
                for reason in impact_reasons:
                    st.markdown(f"- {reason}")
    return live_metrics


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
    commander_decision: dict[str, Any] | None = None,
    self_healing_result: dict[str, Any] | None = None,
) -> None:
    tab_specs: list[tuple[str, str, Any, bool]] = []
    if commander_decision is not None:
        tab_specs.append(("Commander", "Incident Commander Agent", commander_decision, True))
    tab_specs.append(("Monitor", "QoE Monitoring Agent", qoe_result, True))
    if diagnosis_text is not None:
        tab_specs.append(("Diagnose", "Diagnosis Agent", diagnosis_text, False))
    if recovery_text is not None:
        tab_specs.append(("Recover", "Recovery Action Agent", recovery_text, False))
    if self_healing_result is not None:
        tab_specs.append(("Self-Healing", "Self-Healing Service", self_healing_result, True))
    if customer_care_text is not None:
        tab_specs.append(("Communicate", "Customer Care Agent", customer_care_text, False))
    tab_names = [item[0] for item in tab_specs] + ["Band Trace", "Raw Telemetry"]
    tabs = st.tabs(tab_names)
    for tab, (_, title, content, is_json) in zip(tabs, tab_specs):
        with tab:
            render_agent_box(title, content, is_json=is_json)
    with tabs[len(tab_specs)]:
        render_band_room(room_id, shared_context, communication_log, band_result)
    with tabs[len(tab_specs) + 1]:
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
        elif band_result and band_result.get("reason"):
            live_note = str(band_result["reason"])

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
