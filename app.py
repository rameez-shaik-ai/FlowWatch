import json
import os
from typing import Any

import requests
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
    api_key = st.secrets.get("AIML_API_KEY", os.getenv("AIML_API_KEY", ""))
    if not api_key:
        return (
            "Error: AIML_API_KEY is missing. Add it to your .env file before running "
            "AI-powered agents."
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
        "Unknown / needs human investigation. "
        "Respond with concise markdown using the headings: Likely Root Cause, Why, Confidence, "
        "Evidence Used, and Suggested Validation Checks."
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


def render_hackathon_alignment() -> None:
    st.subheader("Hackathon Alignment")
    alignment_rows = [
        {
            "Hackathon Area": "Multi-agent workflow",
            "How FlowWatch addresses it": "Four focused agents collaborate across monitoring, diagnosis, recovery, and communication.",
        },
        {
            "Hackathon Area": "Band usage",
            "How FlowWatch addresses it": "Band is positioned as the shared collaboration layer for agent context, handoff, and room-based coordination.",
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
            "How FlowWatch addresses it": "Streamlit provides a fast, presentation-ready prototype with adjustable telemetry and visible agent outputs.",
        },
    ]
    st.table(alignment_rows)


def main() -> None:
    st.set_page_config(page_title="FlowWatch", page_icon="📺", layout="wide")

    st.title("📺 FlowWatch")
    st.caption("AI multi-agent proactive QoE monitoring for TV streaming")
    st.write("**Workflow:** Monitor -> Diagnose -> Recover -> Communicate")

    with st.sidebar:
        st.header("Configuration")
        selected_model = st.selectbox(
            "AI/ML model",
            MODEL_OPTIONS,
            index=MODEL_OPTIONS.index(DEFAULT_MODEL),
            help="Switch models if one provider route is temporarily unavailable.",
        )

        st.header("Telemetry Simulator")
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

    metrics = st.columns(5)
    metrics[0].metric("QoE Score", telemetry["qoe_score"])
    metrics[1].metric("Bitrate", f"{telemetry['bitrate_mbps']} Mbps")
    metrics[2].metric("Buffering", f"{telemetry['buffering_ratio']}%")
    metrics[3].metric("Latency", f"{telemetry['latency_ms']} ms")
    metrics[4].metric("Packet Loss", f"{telemetry['packet_loss']}%")

    with st.expander("Raw telemetry JSON"):
        st.json(telemetry)

    with st.container(border=True):
        st.subheader("Band Collaboration Context")
        st.write(
            "Band is used to demonstrate agent collaboration, shared context, and task "
            "handoff in a Band room. This Streamlit app provides the stable product demo "
            "powered by AI/ML API."
        )

    if st.button("🚀 Run FlowWatch Multi-Agent Analysis", type="primary", use_container_width=True):
        qoe_result = qoe_monitoring_agent(telemetry)
        render_agent_box("1. QoE Monitoring Agent", qoe_result, is_json=True)

        if qoe_result["qoe_status"] == "Good":
            st.success(
                "QoE looks healthy. FlowWatch stopped after monitoring because no further action is required."
            )
            render_hackathon_alignment()
            return

        with st.spinner("Running diagnosis, recovery, and customer care agents..."):
            diagnosis_text = diagnosis_agent(telemetry, qoe_result, selected_model)
            recovery_text = recovery_action_agent(
                telemetry, diagnosis_text, selected_model
            )
            customer_care_text = customer_care_agent(
                telemetry, diagnosis_text, recovery_text, selected_model
            )

        render_agent_box("2. Diagnosis Agent", diagnosis_text)
        render_agent_box("3. Recovery Action Agent", recovery_text)
        render_agent_box("4. Customer Care Agent", customer_care_text)
        render_hackathon_alignment()
        st.success("FlowWatch analysis complete. The multi-agent workflow is ready for demo.")


if __name__ == "__main__":
    main()
