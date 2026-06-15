# FlowWatch

FlowWatch is a hackathon-ready Streamlit prototype for proactive Quality of Experience monitoring in telecom TV streaming services. It demonstrates how a multi-agent workflow can detect likely customer pain early, diagnose the probable issue, recommend safe recovery steps, and prepare customer care outputs before a complaint arrives.

## Team

**Team Name:** Stream Innovators

## Problem Statement

TV streaming customers often experience buffering, low bitrate, crashes, or instability before contacting support. Operations teams need a lightweight way to identify at-risk sessions early, trigger guided diagnosis, and prepare proactive outreach without exposing internal technical details to the customer.

## Solution Overview

FlowWatch combines deterministic QoE monitoring with AI-assisted diagnosis, recovery planning, and customer communication. The prototype uses editable telemetry in a Streamlit dashboard so judges or operators can simulate scenarios and observe each agent handoff in a single presentation-ready app.

## Architecture

- **Frontend:** Streamlit
- **Rule-based agent:** QoE Monitoring Agent
- **AI-powered agents:** Diagnosis Agent, Recovery Action Agent, Customer Care Agent
- **LLM provider:** AI/ML API at `https://api.aimlapi.com/v1/chat/completions`
- **Configuration:** `.env` using `python-dotenv`

## Agent Workflow

1. **Monitor:** The QoE Monitoring Agent scores session health using deterministic thresholds.
2. **Diagnose:** The Diagnosis Agent identifies the most likely root cause category.
3. **Recover:** The Recovery Action Agent proposes safe automated next steps.
4. **Communicate:** The Customer Care Agent drafts customer-friendly outreach and an internal support summary.

## Technology Stack

- Python 3.11+
- Streamlit
- Requests
- python-dotenv
- AI/ML API

## How to Run Locally

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and add your API key.
4. Start the app:

```bash
streamlit run app.py
```

## Environment Variable Setup

Add the following to `.env`:

```env
AIML_API_KEY=your_ai_ml_api_key_here
BAND_AGENT_ID=your_band_remote_agent_uuid
BAND_API_KEY=your_band_remote_agent_api_key
BAND_REST_URL=https://app.band.ai
```

FlowWatch never hardcodes secrets in the source code.

## How Band Is Used

Band is used as the live multi-agent communication layer. FlowWatch can create a real Band room for each analysis run, publish monitoring and handoff events into that room, and optionally add specialized remote agents as participants so the workflow is visible inside Band as well as inside the Streamlit dashboard.

## How AI/ML API Is Used

The AI/ML API powers:

- Root cause diagnosis
- Safe recovery recommendations
- Proactive customer care outputs

The sidebar includes a model selector so the demo can switch between supported model routes if one fails.

## Future Improvements

- Add autonomous Band remote agents that reply directly in the room
- Connect to real telemetry streams instead of simulated inputs
- Persist case history and operator actions
- Add confidence scoring and trend analysis over time
- Introduce approval workflows for automated remediation

## Submission Notes

FlowWatch is designed for the Band of Agents Hackathon as a practical, product-shaped prototype. It emphasizes clear agent boundaries, demo stability, safe automation, and business value for proactive telecom support.
