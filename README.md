# FlowWatch

FlowWatch is a hackathon-ready Streamlit prototype for proactive telecom TV streaming QoE monitoring. It combines deterministic QoE rules, AI-assisted specialist agents, and optional Band collaboration publishing in a single demo-friendly dashboard.

## What The App Preserves

- Streamlit dashboard
- KPN/telecom-inspired UI theme
- Manual telemetry input
- Live API telemetry fetch
- Embedded HLS player telemetry mode
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
  components/
    __init__.py
    hls_telemetry_player/
      __init__.py
      frontend/
        index.html
  models.py
  services/
    __init__.py
    aiml_api.py
    band_service.py
    playback_impact_gate.py
    player_service.py
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
- `components/hls_telemetry_player/`
  Hosts the custom Streamlit component that streams live HLS browser metrics back into Python.
- `models.py`
  Holds shared dataclasses used by the Band layer.
- `services/aiml_api.py`
  Wraps AI/ML API calls and handles API error cases.
- `services/band_service.py`
  Handles Band SDK setup, configuration, publishing, and graceful fallback if the SDK is unavailable.
- `services/player_service.py`
  Builds the embedded HLS player HTML and generates dynamic mapped telemetry for the player prototype mode.
- `services/playback_impact_gate.py`
  Evaluates whether degraded QoE has become visible playback impact before agents are triggered.
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

The embedded player mode uses `hls.js` in the browser and `streamlit-autorefresh` for periodic KPI refresh in Streamlit.

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

## Embedded HLS Player Mode

FlowWatch now supports a third telemetry source: `Embedded HLS player`.

Default stream:

```text
https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8
```

This mode is implemented in 3 practical hackathon phases:

1. An embedded HLS video player is rendered in the dashboard.
2. Browser-side JavaScript telemetry is shown inside the player component.
3. Python-side FlowWatch telemetry is dynamically mapped and refreshed every few seconds.

### What is real vs simulated in the prototype

- Real in the browser:
  - HLS playback
  - Player state
  - Current playback time
  - Buffered-ahead seconds
  - Resolution
  - Frame counters when supported by the browser
- Simulated/mapped in Streamlit:
  - `bitrate_mbps`
  - `buffering_ratio`
  - `latency_ms`
  - `packet_loss`
  - `qoe_score`

This keeps the prototype simple while still demonstrating how a production player SDK or custom bidirectional Streamlit component would feed real playback telemetry into the backend.

### Embedded player controls

When `Embedded HLS player` is selected, FlowWatch exposes:

- HLS stream URL
- Auto-refresh player telemetry
- Refresh interval: 2s / 3s / 5s
- Scenario: Auto / Healthy / Degraded / Recovering / Live
- Auto-run agent analysis when QoE becomes poor

### Auto-analysis behavior

If auto-analysis is enabled in embedded player mode, FlowWatch first checks the Playback Impact Gate. A cooldown is used to prevent repeated runs every refresh cycle.

## Playback Impact Gate

QoE score alone does not always mean the customer can see playback impact.

FlowWatch now checks player smoothness signals before triggering agents in embedded HLS mode, including:

- buffer ahead
- player state
- playback progress
- dropped-frame ratio
- stall count
- resolution
- player errors

If QoE is risky but playback is still smooth, FlowWatch continues monitoring. Agents trigger only when playback impact is confirmed or critical.

## Live HLS Player Telemetry

Live mode uses a custom Streamlit component backed by `hls.js`.

- The browser player collects playback metrics every 2 seconds.
- Those metrics are passed into Python and used by the Playback Impact Gate.
- QoE, KPI cards, and trigger decisions update from live player behavior.
- True packet loss and network latency are still estimated in the demo from player behavior.
- In production, those values would come from CDN, device, and network telemetry.

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
