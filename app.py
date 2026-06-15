import asyncio
import json
import os
import time
from dataclasses import dataclass
from textwrap import dedent
from typing import Any

import requests
import streamlit as st
from dotenv import load_dotenv

try:
    from band.client.rest import (
        AsyncRestClient,
        ChatEventRequest,
        ChatMessageRequest,
        ChatMessageRequestMentionsItem,
        ChatRoomRequest,
        DEFAULT_REQUEST_OPTIONS,
        ParticipantRequest,
    )

    BAND_SDK_AVAILABLE = True
    BAND_IMPORT_ERROR = ""
except ImportError as exc:
    BAND_SDK_AVAILABLE = False
    BAND_IMPORT_ERROR = str(exc)


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
ARCHITECTURE_DIAGRAM_PATH = "assets/flowwatch-architecture.png"

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


@dataclass
class BandParticipant:
    role: str
    participant_id: str
    display_name: str


@dataclass
class BandConfig:
    enabled: bool
    agent_id: str
    api_key: str
    rest_url: str
    participants: list[BandParticipant]


def get_secret(name: str, default: str = "") -> str:
    return st.secrets.get(name, os.getenv(name, default))


def inject_custom_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #08224a;
            --muted: #54708f;
            --line: rgba(22, 73, 122, 0.16);
            --panel: rgba(255, 255, 255, 0.9);
            --accent: #1ec7c0;
            --accent-2: #0d5cab;
            --accent-3: #10376f;
            --glow: rgba(30, 199, 192, 0.22);
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(30, 199, 192, 0.18), transparent 28%),
                radial-gradient(circle at top right, rgba(13, 92, 171, 0.16), transparent 30%),
                linear-gradient(180deg, #f4f8fd 0%, #edf4fb 100%);
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1220px;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #08224a 0%, #0d3569 100%);
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }

        [data-testid="stSidebar"] * {
            color: #f6f9fc;
        }

        [data-testid="stSidebar"] .stTextInput label,
        [data-testid="stSidebar"] .stNumberInput label,
        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stCheckbox label {
            color: #d8e4f0;
        }

        .hero-shell {
            background: linear-gradient(135deg, rgba(255,255,255,0.97) 0%, rgba(245,251,255,0.92) 100%);
            border: 1px solid var(--line);
            border-radius: 26px;
            padding: 1.4rem 1.5rem 1.5rem 1.5rem;
            box-shadow: 0 24px 80px rgba(8, 34, 74, 0.09);
            position: relative;
            overflow: hidden;
        }

        .hero-shell::after {
            content: "";
            position: absolute;
            inset: auto -80px -90px auto;
            width: 240px;
            height: 240px;
            background: radial-gradient(circle, rgba(30, 199, 192, 0.24), transparent 65%);
        }

        .hero-kicker {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--accent-2);
            background: rgba(13, 92, 171, 0.09);
            border: 1px solid rgba(13, 92, 171, 0.15);
            border-radius: 999px;
            padding: 0.45rem 0.8rem;
            width: fit-content;
        }

        .hero-title {
            font-size: 3.2rem;
            line-height: 1;
            font-weight: 800;
            margin: 0.95rem 0 0.7rem 0;
            color: var(--ink);
        }

        .hero-copy {
            color: var(--muted);
            font-size: 1.02rem;
            line-height: 1.7;
            max-width: 54rem;
            margin: 0;
        }

        .flow-line {
            display: flex;
            flex-wrap: wrap;
            gap: 0.7rem;
            margin-top: 1.2rem;
        }

        .flow-pill {
            border-radius: 999px;
            padding: 0.58rem 0.92rem;
            background: rgba(13, 92, 171, 0.05);
            border: 1px solid rgba(13, 92, 171, 0.1);
            font-weight: 700;
            color: var(--ink);
            font-size: 0.92rem;
        }

        .status-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.65rem;
            margin-top: 0.6rem;
        }

        .status-chip {
            border-radius: 999px;
            padding: 0.4rem 0.75rem;
            font-size: 0.85rem;
            font-weight: 700;
        }

        .status-chip.ready {
            color: #0c6e67;
            background: rgba(30, 199, 192, 0.16);
        }

        .status-chip.warn {
            color: #945300;
            background: rgba(255, 192, 73, 0.18);
        }

        .status-chip.band {
            color: #0d5cab;
            background: rgba(13, 92, 171, 0.12);
        }

        .command-card {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 22px;
            padding: 1.1rem 1.15rem;
            box-shadow: 0 16px 48px rgba(8, 34, 74, 0.05);
        }

        .command-card h4 {
            margin: 0 0 0.45rem 0;
            color: var(--ink);
            font-size: 1rem;
        }

        .command-card p {
            margin: 0;
            color: var(--muted);
            line-height: 1.6;
            font-size: 0.94rem;
        }

        .agent-card {
            background: linear-gradient(180deg, rgba(255,255,255,0.97) 0%, rgba(243,249,255,0.95) 100%);
            border: 1px solid var(--line);
            border-radius: 22px;
            padding: 1rem;
            box-shadow: 0 18px 40px rgba(8, 34, 74, 0.06);
            position: relative;
            overflow: hidden;
            min-height: 152px;
        }

        .agent-card::before {
            content: "";
            position: absolute;
            inset: 0 0 auto 0;
            height: 4px;
            background: linear-gradient(90deg, var(--accent-2), var(--accent));
            opacity: 0.9;
        }

        .agent-card.active {
            border-color: rgba(30, 199, 192, 0.45);
            box-shadow: 0 0 0 1px rgba(30, 199, 192, 0.18), 0 18px 42px var(--glow);
            animation: agentPulse 1.1s ease-in-out infinite;
        }

        .agent-card.done {
            border-color: rgba(30, 199, 192, 0.32);
        }

        .agent-card.waiting {
            opacity: 0.88;
        }

        .agent-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 0.7rem;
        }

        .agent-icon {
            width: 52px;
            height: 52px;
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.4rem;
            background: linear-gradient(135deg, rgba(13, 92, 171, 0.12), rgba(30, 199, 192, 0.16));
            color: var(--accent-3);
        }

        .agent-state {
            min-width: 0;
        }

        .agent-name {
            font-size: 0.98rem;
            font-weight: 800;
            color: var(--ink);
            margin: 0;
        }

        .agent-role {
            margin: 0.18rem 0 0 0;
            color: var(--muted);
            font-size: 0.86rem;
        }

        .agent-badge {
            border-radius: 999px;
            padding: 0.24rem 0.56rem;
            font-size: 0.76rem;
            font-weight: 800;
            white-space: nowrap;
        }

        .agent-badge.active {
            background: rgba(30, 199, 192, 0.18);
            color: #0b736c;
        }

        .agent-badge.done {
            background: rgba(13, 92, 171, 0.12);
            color: #0d5cab;
        }

        .agent-badge.waiting {
            background: rgba(84, 112, 143, 0.12);
            color: #5e738e;
        }

        .agent-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 0.85rem;
        }

        .agent-led {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #9fb0c3;
            box-shadow: 0 0 0 rgba(30, 199, 192, 0);
        }

        .agent-led.active {
            background: var(--accent);
            box-shadow: 0 0 0 8px rgba(30, 199, 192, 0.14);
            animation: ledBlink 0.9s ease-in-out infinite;
        }

        .agent-led.done {
            background: var(--accent-2);
        }

        .agent-led.waiting {
            background: #aab8c6;
        }

        .kpi-pill {
            padding: 0.58rem 0.8rem;
            border-radius: 16px;
            background: rgba(13, 92, 171, 0.07);
            border: 1px solid rgba(13, 92, 171, 0.1);
            margin-bottom: 0.6rem;
        }

        .kpi-pill strong {
            display: block;
            font-size: 1rem;
            color: var(--ink);
        }

        .kpi-pill span {
            font-size: 0.8rem;
            color: #3f5e82;
        }

        @keyframes agentPulse {
            0% { transform: translateY(0); box-shadow: 0 0 0 0 rgba(30, 199, 192, 0.16), 0 18px 42px rgba(8, 34, 74, 0.06); }
            50% { transform: translateY(-2px); box-shadow: 0 0 0 8px rgba(30, 199, 192, 0.07), 0 22px 48px rgba(8, 34, 74, 0.08); }
            100% { transform: translateY(0); box-shadow: 0 0 0 0 rgba(30, 199, 192, 0.16), 0 18px 42px rgba(8, 34, 74, 0.06); }
        }

        @keyframes ledBlink {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.55; transform: scale(1.15); }
        }

        [data-testid="stMetric"] {
            background: linear-gradient(180deg, rgba(255,255,255,0.92) 0%, rgba(248,250,252,0.94) 100%);
            border: 1px solid var(--line);
            border-radius: 22px;
            padding: 0.7rem 0.95rem;
            box-shadow: 0 12px 34px rgba(8, 34, 74, 0.05);
        }

        [data-testid="stMetricLabel"] {
            color: var(--muted);
            font-weight: 700;
        }

        [data-testid="stMetricValue"] {
            color: var(--ink);
        }

        .section-title {
            font-size: 1.2rem;
            font-weight: 800;
            color: var(--ink);
            margin-bottom: 0.8rem;
        }

        .stButton > button {
            background: linear-gradient(90deg, #0d5cab 0%, #1ec7c0 100%);
            border: none;
            color: white;
            font-weight: 800;
            border-radius: 16px;
            padding: 0.85rem 1rem;
            box-shadow: 0 14px 30px rgba(13, 92, 171, 0.28);
        }

        .stButton > button:hover {
            background: linear-gradient(90deg, #094b8f 0%, #18b6b0 100%);
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


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


def render_architecture_diagram() -> None:
    with st.container(border=True):
        st.markdown(
            '<div class="section-title">Technical Architecture</div>',
            unsafe_allow_html=True,
        )
        st.write(
            "This architecture view now sits inside the product demo so you can explain "
            "telemetry ingestion, agent orchestration, Band collaboration, and outputs "
            "without leaving the app."
        )
        if os.path.exists(ARCHITECTURE_DIAGRAM_PATH):
            st.image(
                ARCHITECTURE_DIAGRAM_PATH,
                caption="FlowWatch technical architecture for the hackathon demo",
                use_container_width=True,
            )
        else:
            st.info("Architecture diagram asset not found.")


def render_agent_orchestration_board(
    agent_states: dict[str, str], band_config: BandConfig
) -> None:
    agent_specs = [
        ("QoE Monitoring Agent", "Monitor thresholds", "📡"),
        ("Diagnosis Agent", "Infer root cause", "🧠"),
        ("Recovery Action Agent", "Plan safe actions", "🛠️"),
        ("Customer Care Agent", "Prepare outreach", "💬"),
    ]
    remote_count = len(band_config.participants) + (1 if band_config.agent_id else 0)
    with st.container(border=True):
        header_col, kpi_col = st.columns([1.8, 1.2], gap="large")
        with header_col:
            st.markdown(
                '<div class="section-title" style="margin-bottom:0.35rem;">Live Agent Orchestration</div>',
                unsafe_allow_html=True,
            )
            st.write(
                "This board shows how many agents are available for the demo and which specialist "
                "is actively processing the case right now. Active agents pulse while their step runs."
            )
        with kpi_col:
            st.markdown(
                f'<div class="kpi-pill"><strong>4</strong><span>Core FlowWatch agents</span></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="kpi-pill"><strong>{remote_count}</strong><span>Band-connected agents</span></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="kpi-pill"><strong>{sum(1 for value in agent_states.values() if value == "done")}</strong><span>Completed steps</span></div>',
                unsafe_allow_html=True,
            )

        columns = st.columns(4, gap="large")
        for column, (name, role, icon) in zip(columns, agent_specs):
            state = agent_states.get(name, "waiting")
            label = {
                "active": "Running",
                "done": "Complete",
                "waiting": "Standby",
            }.get(state, "Standby")
            with column:
                st.markdown(
                    f"""
                    <div class="agent-card {state}">
                        <div class="agent-head">
                            <div style="display:flex; gap:0.8rem; align-items:center;">
                                <div class="agent-icon">{icon}</div>
                                <div class="agent-state">
                                    <p class="agent-name">{name}</p>
                                    <p class="agent-role">{role}</p>
                                </div>
                            </div>
                            <span class="agent-badge {state}">{label}</span>
                        </div>
                        <div class="agent-meta">
                            <span style="font-size:0.82rem; color:#3f5e82;">Core specialist</span>
                            <span class="agent-led {state}"></span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def qoe_monitoring_agent(telemetry: dict[str, Any]) -> dict[str, Any]:
    qoe_score = float(telemetry["qoe_score"])
    evidence: list[str] = []

    if float(telemetry["buffering_ratio"]) > 5:
        evidence.append(
            f"Buffering ratio is {telemetry['buffering_ratio']}%, above the 5% threshold."
        )
    if float(telemetry["latency_ms"]) > 150:
        evidence.append(
            f"Latency is {telemetry['latency_ms']} ms, above the 150 ms threshold."
        )
    if float(telemetry["packet_loss"]) > 2:
        evidence.append(
            f"Packet loss is {telemetry['packet_loss']}%, above the 2% threshold."
        )
    if float(telemetry["bitrate_mbps"]) < 3:
        evidence.append(
            f"Bitrate is {telemetry['bitrate_mbps']} Mbps, below the 3 Mbps threshold."
        )
    if int(telemetry["app_crashes"]) > 0:
        evidence.append(
            f"Application crashed {telemetry['app_crashes']} time(s) during the session."
        )

    if qoe_score >= 80:
        qoe_status = "Good"
    elif qoe_score >= 50:
        qoe_status = "Warning"
    else:
        qoe_status = "Poor"

    if evidence:
        qoe_status = "Poor"

    if qoe_status == "Good":
        impact_summary = (
            "Streaming experience appears healthy and no proactive intervention is required."
        )
    elif qoe_status == "Warning":
        impact_summary = (
            "Customer experience may degrade soon, so closer monitoring is recommended."
        )
    else:
        impact_summary = (
            "Customer is likely experiencing noticeable streaming disruption and needs proactive support."
        )

    return {
        "agent": "QoE Monitoring Agent",
        "qoe_status": qoe_status,
        "key_evidence": evidence,
        "customer_impact_summary": impact_summary,
        "recommended_next_agent": (
            "Diagnosis Agent" if qoe_status != "Good" else "None"
        ),
    }


def call_aiml_api(system_prompt: str, user_prompt: str, model_name: str) -> str:
    api_key = get_secret("AIML_API_KEY")
    if not api_key:
        return (
            "Error: AIML_API_KEY is missing. Add it to your .env file or Streamlit secrets "
            "before running AI-powered agents."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 500,
    }

    try:
        response = requests.post(
            AIML_API_URL,
            headers=headers,
            json=payload,
            timeout=45,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        details = exc.response.text[:500] if exc.response is not None else str(exc)
        return f"HTTP error while calling AI/ML API: {details}"
    except requests.exceptions.RequestException as exc:
        return f"Request error while calling AI/ML API: {exc}"

    try:
        data = response.json()
    except ValueError:
        return "Error: AI/ML API returned a non-JSON response."

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, AttributeError, TypeError):
        return (
            "Error: Unexpected AI/ML API response format. "
            f"Received: {json.dumps(data)[:500]}"
        )


def diagnosis_agent(
    telemetry: dict[str, Any], qoe_result: dict[str, Any], model_name: str
) -> str:
    system_prompt = (
        "You are the Diagnosis Agent in a telecom TV streaming QoE monitoring workflow. "
        "Diagnose the most likely root cause using only these categories: "
        "Network congestion, Wi-Fi / home network issue, Set-top box or device issue, "
        "TV streaming app issue, CDN / content delivery issue, Backend platform issue, "
        "Unknown / needs human investigation. Respond with concise markdown using the "
        "headings: Likely Root Cause, Why, Confidence, Evidence Used, and Suggested "
        "Validation Checks."
    )
    user_prompt = (
        "Analyze this telemetry and QoE summary, then diagnose the most likely root cause.\n\n"
        f"Telemetry:\n{json.dumps(telemetry, indent=2)}\n\n"
        f"QoE summary:\n{json.dumps(qoe_result, indent=2)}"
    )
    return call_aiml_api(system_prompt, user_prompt, model_name)


def recovery_action_agent(
    telemetry: dict[str, Any], diagnosis_text: str, model_name: str
) -> str:
    system_prompt = (
        "You are the Recovery Action Agent for a telecom TV streaming service. "
        "Recommend only safe automated recovery actions. Prefer these actions when appropriate: "
        "Refresh streaming session, Retry playback session, Adjust adaptive bitrate profile, "
        "Switch to alternative CDN route if CDN issue is suspected, Restart TV app session on "
        "set-top box, Clear temporary session/cache state, Continue monitoring after action. "
        "Do not suggest billing or account changes, manual router configuration, technician "
        "dispatch as a first step, large network configuration changes, or actions that could "
        "impact many customers. Respond with concise markdown using the headings: Recommended "
        "Actions, Why These Are Safe, Automation Order, and Monitoring Plan."
    )
    user_prompt = (
        "Given the telemetry and diagnosis below, recommend safe recovery actions.\n\n"
        f"Telemetry:\n{json.dumps(telemetry, indent=2)}\n\n"
        f"Diagnosis:\n{diagnosis_text}"
    )
    return call_aiml_api(system_prompt, user_prompt, model_name)


def customer_care_agent(
    telemetry: dict[str, Any],
    diagnosis_text: str,
    recovery_text: str,
    model_name: str,
) -> str:
    system_prompt = (
        "You are the Customer Care Agent for a telecom TV streaming service. "
        "Generate a non-technical customer-friendly message, an internal support ticket summary, "
        "a priority level, and a recommended next step. Do not expose QoE score, packet loss, "
        "CDN, internal agent names, backend details, or technical root cause wording to the "
        "customer-facing message. Respond with concise markdown using the headings: Customer "
        "Message, Internal Support Ticket, Priority Level, and Recommended Next Step."
    )
    user_prompt = (
        "Create the communication outputs based on the telemetry, diagnosis, and recovery plan.\n\n"
        f"Telemetry:\n{json.dumps(telemetry, indent=2)}\n\n"
        f"Diagnosis:\n{diagnosis_text}\n\n"
        f"Recovery plan:\n{recovery_text}"
    )
    return call_aiml_api(system_prompt, user_prompt, model_name)


def render_agent_box(title: str, content: Any, is_json: bool = False) -> None:
    with st.container(border=True):
        st.subheader(title)
        if is_json:
            st.json(content)
        else:
            st.markdown(content)


def create_band_event(
    step: int,
    sender: str,
    receiver: str,
    event_type: str,
    summary: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "step": step,
        "sender": sender,
        "receiver": receiver,
        "event_type": event_type,
        "summary": summary,
        "payload": payload,
    }


def build_band_config() -> BandConfig:
    participants: list[BandParticipant] = []

    with st.sidebar:
        st.header("Band Live Layer")
        band_enabled = st.checkbox(
            "Enable Band room publishing",
            value=bool(get_secret("BAND_API_KEY")),
            help="Publish the workflow into a real Band room using the official SDK client.",
        )
        band_agent_id = st.text_input(
            "Band orchestrator agent ID",
            value=get_secret("BAND_AGENT_ID"),
        )
        band_api_key = st.text_input(
            "Band orchestrator API key",
            value=get_secret("BAND_API_KEY"),
            type="password",
        )
        band_rest_url = st.text_input(
            "Band REST URL",
            value=get_secret("BAND_REST_URL", DEFAULT_BAND_REST_URL),
        )

        with st.expander("Optional Band participant agents"):
            role_fields = [
                ("Diagnosis Agent", "BAND_DIAGNOSIS_AGENT_ID", "BAND_DIAGNOSIS_AGENT_NAME"),
                ("Recovery Action Agent", "BAND_RECOVERY_AGENT_ID", "BAND_RECOVERY_AGENT_NAME"),
                ("Customer Care Agent", "BAND_CUSTOMER_AGENT_ID", "BAND_CUSTOMER_AGENT_NAME"),
            ]
            for role, id_key, name_key in role_fields:
                participant_id = st.text_input(role + " participant ID", value=get_secret(id_key))
                display_name = st.text_input(
                    role + " display name",
                    value=get_secret(name_key, role),
                )
                if participant_id:
                    participants.append(
                        BandParticipant(
                            role=role,
                            participant_id=participant_id,
                            display_name=display_name or role,
                        )
                    )

        if band_enabled and not BAND_SDK_AVAILABLE:
            st.warning(
                "Band SDK package is not installed in this environment yet. "
                "Add `band-sdk` to requirements before expecting live room publishing."
            )

    return BandConfig(
        enabled=band_enabled,
        agent_id=band_agent_id,
        api_key=band_api_key,
        rest_url=band_rest_url,
        participants=participants,
    )


async def publish_workflow_to_band(
    band_config: BandConfig,
    telemetry: dict[str, Any],
    qoe_result: dict[str, Any],
    diagnosis_text: str | None,
    recovery_text: str | None,
    customer_care_text: str | None,
    model_name: str,
) -> dict[str, Any]:
    if not band_config.enabled:
        return {"published": False, "reason": "Band publishing disabled"}
    if not BAND_SDK_AVAILABLE:
        return {
            "published": False,
            "error": f"Band SDK unavailable in runtime: {BAND_IMPORT_ERROR}",
        }
    if not band_config.api_key:
        return {"published": False, "error": "Missing BAND_API_KEY"}

    client = AsyncRestClient(
        api_key=band_config.api_key,
        base_url=band_config.rest_url.rstrip("/"),
    )
    task_id = f"flowwatch-{telemetry['customer_id'].lower()}"
    room_response = await client.agent_api_chats.create_agent_chat(
        chat=ChatRoomRequest(task_id=task_id),
        request_options=DEFAULT_REQUEST_OPTIONS,
    )
    room_id = room_response.data.id

    added_participants: list[str] = []
    for participant in band_config.participants:
        await client.agent_api_participants.add_agent_chat_participant(
            chat_id=room_id,
            participant=ParticipantRequest(participant_id=participant.participant_id),
            request_options=DEFAULT_REQUEST_OPTIONS,
        )
        added_participants.append(participant.display_name)

    await client.agent_api_events.create_agent_chat_event(
        chat_id=room_id,
        event=ChatEventRequest(
            content="FlowWatch started a proactive QoE investigation.",
            message_type="task",
            metadata={
                "customer_id": telemetry["customer_id"],
                "service": telemetry["service"],
                "orchestrator_agent_id": band_config.agent_id or "not_provided",
                "model_name": model_name,
            },
        ),
        request_options=DEFAULT_REQUEST_OPTIONS,
    )

    await client.agent_api_events.create_agent_chat_event(
        chat_id=room_id,
        event=ChatEventRequest(
            content=f"QoE monitoring classified the session as {qoe_result['qoe_status']}.",
            message_type="thought",
            metadata=qoe_result,
        ),
        request_options=DEFAULT_REQUEST_OPTIONS,
    )

    if diagnosis_text:
        await client.agent_api_events.create_agent_chat_event(
            chat_id=room_id,
            event=ChatEventRequest(
                content="Diagnosis completed and published to the room.",
                message_type="task",
                metadata={"diagnosis": diagnosis_text},
            ),
            request_options=DEFAULT_REQUEST_OPTIONS,
        )

    if recovery_text:
        await client.agent_api_events.create_agent_chat_event(
            chat_id=room_id,
            event=ChatEventRequest(
                content="Recovery plan completed and published to the room.",
                message_type="task",
                metadata={"recovery_plan": recovery_text},
            ),
            request_options=DEFAULT_REQUEST_OPTIONS,
        )

    if customer_care_text:
        await client.agent_api_events.create_agent_chat_event(
            chat_id=room_id,
            event=ChatEventRequest(
                content="Customer care communication package completed.",
                message_type="task",
                metadata={"customer_care": customer_care_text},
            ),
            request_options=DEFAULT_REQUEST_OPTIONS,
        )

    published_messages = 0
    role_messages = [
        (
            "Diagnosis Agent",
            dedent(
                f"""
                Please review this streaming session and assess likely root cause.

                Customer: {telemetry['customer_id']}
                QoE status: {qoe_result['qoe_status']}
                Evidence: {', '.join(qoe_result['key_evidence']) or 'No threshold breach evidence'}
                """
            ).strip(),
        ),
        (
            "Recovery Action Agent",
            dedent(
                f"""
                Please review the current diagnosis and publish safe remediation actions.

                Diagnosis:
                {diagnosis_text or 'Not available'}
                """
            ).strip(),
        ),
        (
            "Customer Care Agent",
            dedent(
                f"""
                Please prepare customer-friendly outreach and an internal support note.

                Recovery plan:
                {recovery_text or 'Not available'}
                """
            ).strip(),
        ),
    ]

    for role, message in role_messages:
        participant = next((item for item in band_config.participants if item.role == role), None)
        if participant is None:
            continue
        await client.agent_api_messages.create_agent_chat_message(
            chat_id=room_id,
            message=ChatMessageRequest(
                content=message,
                mentions=[
                    ChatMessageRequestMentionsItem(
                        id=participant.participant_id,
                        name=participant.display_name,
                    )
                ],
            ),
            request_options=DEFAULT_REQUEST_OPTIONS,
        )
        published_messages += 1

    return {
        "published": True,
        "room_id": room_id,
        "task_id": task_id,
        "participants_added": added_participants,
        "participant_messages_sent": published_messages,
        "rest_url": band_config.rest_url,
    }


def run_band_publish(
    band_config: BandConfig,
    telemetry: dict[str, Any],
    qoe_result: dict[str, Any],
    diagnosis_text: str | None,
    recovery_text: str | None,
    customer_care_text: str | None,
    model_name: str,
) -> dict[str, Any]:
    try:
        return asyncio.run(
            publish_workflow_to_band(
                band_config,
                telemetry,
                qoe_result,
                diagnosis_text,
                recovery_text,
                customer_care_text,
                model_name,
            )
        )
    except Exception as exc:
        return {"published": False, "error": str(exc)}


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


def main() -> None:
    st.set_page_config(page_title="FlowWatch", page_icon="📺", layout="wide")
    inject_custom_css()
    band_config = build_band_config()

    with st.sidebar:
        st.header("Model & Telemetry")
        selected_model = st.selectbox(
            "AI/ML model",
            MODEL_OPTIONS,
            index=MODEL_OPTIONS.index(DEFAULT_MODEL),
            help="Switch models if one provider route is temporarily unavailable.",
        )
        telemetry = {
            "customer_id": st.text_input(
                "Customer ID", value=DEFAULT_TELEMETRY["customer_id"]
            ),
            "device_id": st.text_input(
                "Device ID", value=DEFAULT_TELEMETRY["device_id"]
            ),
            "service": st.text_input("Service", value=DEFAULT_TELEMETRY["service"]),
            "bitrate_mbps": st.number_input(
                "Bitrate Mbps",
                min_value=0.0,
                value=float(DEFAULT_TELEMETRY["bitrate_mbps"]),
                step=0.1,
            ),
            "buffering_ratio": st.number_input(
                "Buffering ratio %",
                min_value=0.0,
                value=float(DEFAULT_TELEMETRY["buffering_ratio"]),
                step=0.1,
            ),
            "latency_ms": st.number_input(
                "Latency ms",
                min_value=0,
                value=int(DEFAULT_TELEMETRY["latency_ms"]),
                step=1,
            ),
            "packet_loss": st.number_input(
                "Packet loss %",
                min_value=0.0,
                value=float(DEFAULT_TELEMETRY["packet_loss"]),
                step=0.1,
            ),
            "app_crashes": st.number_input(
                "App crashes",
                min_value=0,
                value=int(DEFAULT_TELEMETRY["app_crashes"]),
                step=1,
            ),
            "qoe_score": st.number_input(
                "QoE score",
                min_value=0,
                max_value=100,
                value=int(DEFAULT_TELEMETRY["qoe_score"]),
                step=1,
            ),
        }

    render_hero(band_config)
    st.write("")
    render_overview_cards()
    st.write("")

    default_agent_states = {
        "QoE Monitoring Agent": "waiting",
        "Diagnosis Agent": "waiting",
        "Recovery Action Agent": "waiting",
        "Customer Care Agent": "waiting",
    }
    orchestration_placeholder = st.empty()
    orchestration_placeholder.markdown("")
    with orchestration_placeholder.container():
        render_agent_orchestration_board(default_agent_states, band_config)

    metrics = st.columns(5)
    metrics[0].metric("QoE Score", telemetry["qoe_score"])
    metrics[1].metric("Bitrate", f"{telemetry['bitrate_mbps']} Mbps")
    metrics[2].metric("Buffering", f"{telemetry['buffering_ratio']}%")
    metrics[3].metric("Latency", f"{telemetry['latency_ms']} ms")
    metrics[4].metric("Packet Loss", f"{telemetry['packet_loss']}%")

    with st.expander("Raw telemetry JSON"):
        st.json(telemetry)

    render_architecture_diagram()

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
            if band_config.enabled and BAND_SDK_AVAILABLE and band_config.api_key:
                st.success("Band live room publishing is armed for this run.")
            elif band_config.enabled and not BAND_SDK_AVAILABLE:
                st.warning("Band publishing is enabled, but the SDK package is not available in this runtime.")
            elif band_config.enabled and not band_config.api_key:
                st.warning("Band publishing is enabled, but BAND_API_KEY is missing.")
            else:
                st.info("Band sync is optional. Enable it in the sidebar to publish the workflow into a real Band room.")

    if st.button(
        "🚀 Run FlowWatch Multi-Agent Analysis",
        type="primary",
        use_container_width=True,
    ):
        room_id = f"band-room-{telemetry['customer_id'].lower()}"
        communication_log: list[dict[str, Any]] = []
        band_result: dict[str, Any] | None = None
        agent_states = dict(default_agent_states)

        agent_states["QoE Monitoring Agent"] = "active"
        with orchestration_placeholder.container():
            render_agent_orchestration_board(agent_states, band_config)
        time.sleep(0.25)

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
        render_agent_box("1. QoE Monitoring Agent", qoe_result, is_json=True)

        if qoe_result["qoe_status"] == "Good":
            with orchestration_placeholder.container():
                render_agent_orchestration_board(agent_states, band_config)
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
            render_band_room(room_id, shared_context, communication_log, band_result)
            st.success(
                "QoE looks healthy. FlowWatch stopped after monitoring because no further action is required."
            )
            render_hackathon_alignment()
            return

        agent_states["Diagnosis Agent"] = "active"
        with orchestration_placeholder.container():
            render_agent_orchestration_board(agent_states, band_config)
        time.sleep(0.2)

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
            with orchestration_placeholder.container():
                render_agent_orchestration_board(agent_states, band_config)
            time.sleep(0.2)

            recovery_text = recovery_action_agent(
                telemetry, diagnosis_text, selected_model
            )
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
            with orchestration_placeholder.container():
                render_agent_orchestration_board(agent_states, band_config)
            time.sleep(0.2)

            customer_care_text = customer_care_agent(
                telemetry, diagnosis_text, recovery_text, selected_model
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

        with orchestration_placeholder.container():
            render_agent_orchestration_board(agent_states, band_config)

        render_agent_box("2. Diagnosis Agent", diagnosis_text)
        render_agent_box("3. Recovery Action Agent", recovery_text)
        render_agent_box("4. Customer Care Agent", customer_care_text)

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
        render_band_room(room_id, shared_context, communication_log, band_result)
        render_hackathon_alignment()
        st.success(
            "FlowWatch analysis complete. The multi-agent workflow and Band communication layer are ready for demo."
        )


if __name__ == "__main__":
    main()
