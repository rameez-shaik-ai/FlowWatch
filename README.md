# FlowWatch

FlowWatch is a hackathon-ready Streamlit prototype for proactive telecom TV streaming QoE monitoring. It combines deterministic QoE rules, AI-assisted specialist agents, and optional Band collaboration publishing in a single demo-friendly dashboard.

## What The App Preserves

- Streamlit dashboard
- KPN/telecom-inspired UI theme
- Manual telemetry input
- Live API telemetry fetch
- Random telemetry generation
- Ideal telemetry generation
- QoE Monitoring Agent
- Diagnosis Agent
- Recovery Action Agent
- Customer Care Agent
- AI/ML API integration
- Band live publishing layer
- Band participant configuration
- Band handoff trace
- Hackathon alignment section

## Modular Architecture

```text
FlowWatch/
  app.py
  config.py
  models.py
  services/
    __init__.py
    aiml_api.py
    band_service.py
    telemetry_service.py
  agents/
    __init__.py
    qoe_monitoring_agent.py
    diagnosis_agent.py
    recovery_action_agent.py
    customer_care_agent.py
  ui/
    __init__.py
    styles.py
    layout.py
    components.py
  utils/
    __init__.py
    qoe_scoring.py
  assets/
    flowwatch-architecture.png
  requirements.txt
  README.md
  .env.example
  .gitignore
```

## Module Guide

- `app.py`
  Coordinates Streamlit page setup, sidebar input flow, workflow execution, and result rendering.
- `config.py`
  Holds constants and the secret-loading helper.
- `models.py`
  Holds shared dataclasses used by the Band layer.
- `services/aiml_api.py`
  Wraps AI/ML API calls and handles API error cases.
- `services/band_service.py`
  Handles Band SDK setup, configuration, publishing, and graceful fallback if the SDK is unavailable.
- `services/telemetry_service.py`
  Loads and validates telemetry from live endpoints.
- `agents/`
  Contains the four specialist agent implementations.
- `ui/styles.py`
  Applies the FlowWatch visual theme.
- `ui/layout.py`
  Renders page-level layout sections such as the hero and hackathon alignment.
- `ui/components.py`
  Renders reusable UI blocks such as orchestration cards, metrics, and Band trace views.
- `utils/qoe_scoring.py`
  Provides QoE score calculation and demo telemetry generators.

## How To Run Locally

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and add your keys.
4. Start the app:

```bash
streamlit run app.py
```

## Environment Variables

Add these values to `.env` for local runs:

```env
AIML_API_KEY=your_ai_ml_api_key_here
BAND_AGENT_ID=your_band_remote_agent_uuid
BAND_API_KEY=your_band_remote_agent_api_key
BAND_REST_URL=https://app.band.ai
```

Optional Band participant agent values:

```env
BAND_DIAGNOSIS_AGENT_ID=
BAND_DIAGNOSIS_AGENT_NAME=Diagnosis Agent
BAND_RECOVERY_AGENT_ID=
BAND_RECOVERY_AGENT_NAME=Recovery Action Agent
BAND_CUSTOMER_AGENT_ID=
BAND_CUSTOMER_AGENT_NAME=Customer Care Agent
```

## AI/ML API Setup

FlowWatch uses:

- Endpoint: `https://api.aimlapi.com/v1/chat/completions`
- Auth: Bearer token via `AIML_API_KEY`

The AI/ML API powers:

- Root cause diagnosis
- Safe recovery recommendations
- Customer-facing and internal support communication

## Band Setup

FlowWatch can optionally publish each run into a live Band room.

To enable it:

1. Provide `BAND_API_KEY`
2. Optionally provide `BAND_AGENT_ID`
3. Optionally add participant agent IDs for diagnosis, recovery, and customer-care roles

If `band-sdk` is not installed or not available at runtime, the app still works and shows a warning instead of crashing.

Note:
- `band-sdk` is included in `requirements.txt`
- If your environment uses a different package name or a private index for the Band SDK, install that version and keep the same Python imports used in `services/band_service.py`

## Streamlit Cloud Deployment Notes

1. Push the project to GitHub.
2. Create a Streamlit Cloud app pointing at `app.py`.
3. Add secrets in the Streamlit Cloud app settings if you do not want to rely on `.env`.
4. Recommended secrets:

```toml
AIML_API_KEY = "your_ai_ml_api_key_here"
BAND_AGENT_ID = "your_band_remote_agent_uuid"
BAND_API_KEY = "your_band_remote_agent_api_key"
BAND_REST_URL = "https://app.band.ai"
```

Streamlit Cloud redeploys automatically when a new commit reaches the selected branch.

## How The Workflow Works

1. The QoE Monitoring Agent evaluates the current session using deterministic rules.
2. If the session is healthy, FlowWatch stops after monitoring.
3. If the session is degraded, FlowWatch calls the Diagnosis Agent.
4. The Recovery Action Agent proposes safe next steps.
5. The Customer Care Agent prepares outreach and internal support outputs.
6. If Band is enabled, FlowWatch publishes the workflow into a live Band room.

## Developer Notes

- Secrets are never hardcoded in source code.
- The refactor keeps the app beginner-friendly and modular.
- The current UI and behavior are preserved while reducing the amount of logic inside `app.py`.
