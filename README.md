# FlowWatch

FlowWatch is a hackathon-ready Streamlit application for proactive TV streaming QoE monitoring. It combines telecom telemetry, a multi-agent workflow, optional Band collaboration, an embedded HLS player demo, and a self-healing approval flow in one dashboard.

This project is designed to answer a simple demo question:

`Can we detect streaming quality problems early, understand the likely cause, recommend safe recovery actions, and coordinate the response with agents before the customer complains?`

## What FlowWatch Does

FlowWatch monitors a TV streaming session and turns raw telemetry into an operator-friendly incident workflow.

It can:

- calculate a QoE score from streaming telemetry
- classify the session as `Good`, `Warning`, or `Poor`
- trigger specialist agents only when needed
- show likely root cause and recovery guidance
- prepare customer-care communication
- simulate safe self-healing with operator approval
- publish incident collaboration events to Band

## Who This Is For

FlowWatch is useful for:

- hackathon demos
- telecom operations and NOC walkthroughs
- product stakeholders reviewing AI-assisted support workflows
- teams exploring proactive QoE monitoring concepts

## Main Features

- Streamlit dashboard with a telecom-inspired UI
- Manual telemetry mode for controlled demos
- Live API fetch mode with a built-in demo feed
- Embedded HLS player mode with browser playback telemetry
- QoE Monitoring, Diagnosis, Recovery, Customer Care, and Incident Commander agents
- Playback Impact Gate to reduce false positives
- Self-healing recommendation and approval flow
- Optional Band room publishing and agent handoff trace
- Random and ideal dataset generators for fast demos

## How The Demo Works

FlowWatch supports three telemetry source modes.

### 1. Manual

Use this when you want full control of the numbers.

You can:

- type values directly
- generate a random session
- generate an ideal session
- instantly see the recalculated QoE score

Best for:

- judge demos
- deterministic screenshots
- explaining how QoE logic behaves

### 2. Live API Fetch

Use this when you want a “live feed” experience without running a separate backend.

FlowWatch includes a built-in demo endpoint:

```text
flowwatch://demo/live-api/flowwatch-session
```

The built-in feed cycles through realistic states:

- Healthy
- Warning
- Poor
- Recovering

Best for:

- reliable Streamlit Cloud demos
- showing changing telemetry over time
- demonstrating that FlowWatch can ingest external-style telemetry

### 3. Embedded HLS Player

Use this when you want a visible video player plus live playback telemetry.

Default stream:

```text
https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8
```

This mode shows:

- live browser playback preview
- buffered-ahead depth
- playback progress
- dropped frames
- resolution
- player state

FlowWatch then maps those player metrics into telecom-style telemetry for scoring and agent decisions.

Best for:

- the most visual demo experience
- showing how player behavior affects QoE
- demonstrating playback-aware agent triggering

## End-to-End Workflow

FlowWatch follows this high-level flow:

1. Telemetry is collected from manual input, demo API, or the embedded HLS player.
2. QoE is calculated from bitrate, buffering, latency, packet loss, and app stability.
3. The QoE Monitoring Agent classifies the session.
4. The Playback Impact Gate checks whether degraded playback is actually customer-visible.
5. The Incident Commander decides whether to keep monitoring, investigate further, or trigger recovery.
6. The Diagnosis Agent identifies likely root cause.
7. The Recovery Action Agent recommends safe next actions.
8. The Customer Care Agent prepares customer-facing and support-ready communication.
9. If enabled, FlowWatch publishes the incident workflow into Band.
10. If self-healing is recommended, the operator can approve or reject the action.

## Agent Overview

### QoE Monitoring Agent

- calculates QoE
- checks thresholds
- classifies health state
- decides whether escalation is needed

### Diagnosis Agent

- analyzes degraded telemetry
- identifies likely root cause
- explains evidence and confidence

### Recovery Action Agent

- recommends safe recovery steps
- suggests monitoring checks
- keeps the demo bounded to low-risk actions

### Customer Care Agent

- prepares customer-friendly communication
- creates internal support summary content
- suggests next follow-up steps

### Incident Commander Agent

- decides whether to monitor, escalate, heal, or collaborate
- routes the workflow
- gates self-healing through approval logic

## Playback Impact Gate

Poor QoE should not automatically mean “the customer is definitely affected.”

FlowWatch includes a Playback Impact Gate to reduce false positives, especially in embedded HLS player mode.

It looks at signals such as:

- buffered-ahead depth
- whether playback time is moving
- dropped-frame ratio
- waiting or stalled states
- low resolution under degraded conditions
- explicit player errors

This means FlowWatch can distinguish between:

- telemetry that looks risky but playback is still stable
- telemetry that has become a real viewer-impacting issue

## Self-Healing Approval Flow

FlowWatch can recommend limited, safe demo actions such as:

- refresh streaming session
- retry playback
- restart streaming app

These actions are:

- recommendation-based
- approval-gated
- safety-checked in Python before execution

Unsupported or unsafe actions are blocked instead of executed automatically.

## Band Integration

Band is used as the collaboration layer for the hackathon demo.

When enabled, FlowWatch can publish:

- incident room context
- commander decision
- specialist handoff trace
- approval state
- recovery outcome
- final incident summary

Band is optional. The app still works without it.

## Project Structure

```text
FlowWatch/
  app.py
  config.py
  models.py
  README.md
  requirements.txt
  assets/
    flowwatch-architecture.png
  agents/
    customer_care_agent.py
    diagnosis_agent.py
    incident_commander_agent.py
    qoe_monitoring_agent.py
    recovery_action_agent.py
  components/
    hls_telemetry_player/
      frontend/
        index.html
  services/
    aiml_api.py
    band_service.py
    playback_impact_gate.py
    player_service.py
    self_healing_service.py
    telemetry_service.py
  ui/
    components.py
    layout.py
    styles.py
  utils/
    qoe_scoring.py
  workflow/
    autonomous_orchestrator.py
```

## Module Guide

- `app.py`
  Main Streamlit entry point. Coordinates sidebar state, telemetry source handling, workflow execution, and page rendering.
- `config.py`
  Shared defaults, model list, and secret-loading helpers.
- `utils/qoe_scoring.py`
  QoE scoring rules plus random and ideal telemetry generators.
- `services/telemetry_service.py`
  Live API loading, validation, and built-in demo feed generation.
- `services/player_service.py`
  Embedded HLS player setup and mapping of player metrics into FlowWatch telemetry.
- `services/playback_impact_gate.py`
  Logic that decides whether degraded playback is truly customer-visible.
- `services/self_healing_service.py`
  Safe self-healing action handling and post-healing telemetry updates.
- `services/band_service.py`
  Band configuration, event formatting, and publishing helpers.
- `services/aiml_api.py`
  AI/ML API wrapper for diagnosis, recovery, and customer-care reasoning.
- `agents/`
  Specialist agent implementations.
- `workflow/autonomous_orchestrator.py`
  Incident Commander routing and workflow eligibility helpers.
- `ui/styles.py`
  Global visual theme.
- `ui/layout.py`
  Page-level layout helpers.
- `ui/components.py`
  Reusable UI cards, sections, panels, tabs, and workflow visuals.

## QoE Logic

The QoE score is calculated from the telemetry fields in `utils/qoe_scoring.py`.

The score is influenced by:

- bitrate
- buffering ratio
- latency
- packet loss
- app crashes

In the app:

- changing manual telemetry updates the score
- `Random` generates mixed-quality demo sessions
- `Ideal` generates strong sessions, usually above 80 QoE

## Running Locally

### 1. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure secrets

Copy `.env.example` to `.env` and add the keys you want to use.

### 4. Start the app

```bash
streamlit run app.py
```

Then open the local Streamlit URL shown in your terminal.

## Environment Variables

Typical local `.env` values:

```env
AIML_API_KEY=your_ai_ml_api_key_here
BAND_AGENT_ID=your_band_remote_agent_uuid
BAND_API_KEY=your_band_remote_agent_api_key
BAND_REST_URL=https://app.band.ai
```

Optional participant agent configuration:

```env
BAND_DIAGNOSIS_AGENT_ID=
BAND_DIAGNOSIS_AGENT_NAME=Diagnosis Agent
BAND_RECOVERY_AGENT_ID=
BAND_RECOVERY_AGENT_NAME=Recovery Action Agent
BAND_CUSTOMER_AGENT_ID=
BAND_CUSTOMER_AGENT_NAME=Customer Care Agent
```

## AI/ML API Usage

FlowWatch uses the AI/ML API for:

- diagnosis reasoning
- recovery recommendations
- customer-care output
- incident commander guidance when available

Endpoint:

```text
https://api.aimlapi.com/v1/chat/completions
```

Auth:

- Bearer token via `AIML_API_KEY`

If the model call is unavailable, parts of the workflow fall back to deterministic logic so the demo can still continue.

## Streamlit Cloud Deployment

### 1. Push the repo to GitHub

Make sure `app.py` is in the repo root.

### 2. Create a Streamlit Cloud app

Point the app to:

- repository: your GitHub repo
- branch: usually `main`
- main file path: `app.py`

### 3. Add secrets

Add these in Streamlit Cloud secrets if needed:

```toml
AIML_API_KEY = "your_ai_ml_api_key_here"
BAND_AGENT_ID = "your_band_remote_agent_uuid"
BAND_API_KEY = "your_band_remote_agent_api_key"
BAND_REST_URL = "https://app.band.ai"
```

### 4. Deploy

Streamlit Cloud will rebuild and redeploy on every new push to the connected branch.

## Demo Tips

### Best quick demo path

1. Start in `Manual`
2. Click `Random`
3. Show the QoE score and agent recommendation
4. If the score is poor, run the full analysis
5. Show approval flow and Band trace

### Best visual demo path

1. Switch to `Embedded HLS player`
2. Use `Degraded` scenario
3. Enable refresh
4. Show playback impact scoring
5. Trigger the agent workflow

### Best reliable “live” demo path

1. Switch to `Live API fetch`
2. Use the built-in demo feed
3. Let the feed cycle through healthy and degraded states

## Troubleshooting

### The app loads but Band features fail

Check:

- `BAND_API_KEY`
- `BAND_AGENT_ID`
- `BAND_REST_URL`
- whether your Band SDK/package is installed correctly

### Live API mode does not work with `localhost`

That is expected on Streamlit Cloud. Use:

- the built-in demo endpoint
- or a publicly reachable API

### Embedded player mode looks blank

Check:

- the stream URL is valid
- your browser/network allows the stream
- the Streamlit component assets loaded correctly

### The AI features are missing or weaker than expected

Check:

- `AIML_API_KEY`
- model availability
- network access from the runtime

The app can still fall back to deterministic behavior for some flows.

## Production Adaptation Ideas

This demo is intentionally lightweight. In a production version, you would likely replace or add:

- real telemetry ingestion from STBs, apps, CDNs, and probes
- persistent incident storage
- true ticketing integration
- alerting integration
- real player SDK telemetry
- authenticated operator workflows
- more policy controls around autonomous healing

## Summary

FlowWatch is a modern demo app that shows how telecom streaming telemetry, agent orchestration, self-healing approval, and collaboration tooling can work together in a single proactive QoE operations experience.

If you want to understand the project quickly, start with:

1. `app.py`
2. `utils/qoe_scoring.py`
3. `services/telemetry_service.py`
4. `services/player_service.py`
5. `workflow/autonomous_orchestrator.py`
