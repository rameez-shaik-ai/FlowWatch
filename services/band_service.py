from __future__ import annotations

import asyncio
from textwrap import dedent
from typing import Any

import streamlit as st

from config import DEFAULT_BAND_REST_URL, get_secret
from models import BandConfig, BandParticipant

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


def _safe_event_metadata(payload: dict[str, Any]) -> dict[str, str]:
    """Keep Band metadata compact and string-based for demo reliability."""
    metadata: dict[str, str] = {}
    for key, value in payload.items():
        if value is None:
            continue
        if isinstance(value, (dict, list, tuple)):
            metadata[key] = str(value)
        else:
            metadata[key] = str(value)
    return metadata


def build_band_config() -> BandConfig:
    """Render sidebar Band settings and return the current configuration."""
    participants: list[BandParticipant] = []

    with st.sidebar:
        with st.expander("Band Live Layer", expanded=False):
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
            force_publish_monitoring = st.checkbox(
                "Force publish monitoring events to Band",
                value=False,
                help="Useful for demos where you want a Band room even when the commander chooses monitor-only.",
            )

            with st.expander("Optional Band participant agents"):
                role_fields = [
                    ("Diagnosis Agent", "BAND_DIAGNOSIS_AGENT_ID", "BAND_DIAGNOSIS_AGENT_NAME"),
                    ("Recovery Action Agent", "BAND_RECOVERY_AGENT_ID", "BAND_RECOVERY_AGENT_NAME"),
                    ("Customer Care Agent", "BAND_CUSTOMER_AGENT_ID", "BAND_CUSTOMER_AGENT_NAME"),
                ]
                for role, id_key, name_key in role_fields:
                    participant_id = st.text_input(
                        f"{role} participant ID",
                        value=get_secret(id_key),
                    )
                    display_name = st.text_input(
                        f"{role} display name",
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
        force_publish_monitoring=force_publish_monitoring,
    )


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


async def publish_workflow_to_band(
    band_config: BandConfig,
    telemetry: dict[str, Any],
    qoe_result: dict[str, Any],
    diagnosis_text: str | None,
    recovery_text: str | None,
    customer_care_text: str | None,
    model_name: str,
    playback_impact: dict[str, Any] | None = None,
    commander_decision: dict[str, Any] | None = None,
    self_healing_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Publish the FlowWatch workflow into a Band room when enabled."""
    if not band_config.enabled:
        return {"published": False, "reason": "Band publishing disabled"}
    if not BAND_SDK_AVAILABLE:
        return {
            "published": False,
            "error": f"Band SDK unavailable in runtime: {BAND_IMPORT_ERROR}",
        }
    if not band_config.api_key:
        return {"published": False, "error": "Missing BAND_API_KEY"}
    if (
        commander_decision
        and not commander_decision.get("band_room_required", False)
        and not band_config.force_publish_monitoring
    ):
        return {
            "published": False,
            "reason": "Commander did not require a Band room for this incident.",
        }

    client = AsyncRestClient(
        api_key=band_config.api_key,
        base_url=band_config.rest_url.rstrip("/"),
    )
    room_response = await client.agent_api_chats.create_agent_chat(
        chat=ChatRoomRequest(),
        request_options=DEFAULT_REQUEST_OPTIONS,
    )
    room_id = room_response.data.id

    added_participants: list[str] = []
    warnings: list[str] = []
    for participant in band_config.participants:
        try:
            await client.agent_api_participants.add_agent_chat_participant(
                chat_id=room_id,
                participant=ParticipantRequest(participant_id=participant.participant_id),
                request_options=DEFAULT_REQUEST_OPTIONS,
            )
            added_participants.append(participant.display_name)
        except Exception as exc:
            warnings.append(f"Could not add {participant.display_name}: {exc}")

    async def publish_event(content: str, metadata: dict[str, Any]) -> None:
        await client.agent_api_events.create_agent_chat_event(
            chat_id=room_id,
            event=ChatEventRequest(
                content=content,
                message_type="thought",
                metadata=_safe_event_metadata(metadata),
            ),
            request_options=DEFAULT_REQUEST_OPTIONS,
        )

    await publish_event(
        "FlowWatch started a proactive QoE investigation.",
        {
            "customer_id": telemetry["customer_id"],
            "service": telemetry["service"],
            "orchestrator_agent_id": band_config.agent_id or "not_provided",
            "model_name": model_name,
        },
    )

    if playback_impact is not None:
        await publish_event(
            f"Playback Impact Gate evaluated the session as {playback_impact.get('impact_status', 'Unknown')}.",
            playback_impact,
        )

    if commander_decision is not None:
        await publish_event(
            (
                f"Incident Commander selected {commander_decision.get('decision', 'monitor_only')} "
                f"with severity {commander_decision.get('severity', 'Low')}."
            ),
            commander_decision,
        )

    await publish_event(
        f"QoE monitoring classified the session as {qoe_result['qoe_status']}.",
        qoe_result,
    )

    if diagnosis_text:
        await publish_event(
            "Diagnosis completed and published to the room.",
            {"diagnosis": diagnosis_text},
        )

    if recovery_text:
        await publish_event(
            "Recovery plan completed and published to the room.",
            {"recovery_plan": recovery_text},
        )

    if self_healing_result and self_healing_result.get("approval_required"):
        await publish_event(
            "Self-healing approval was requested for the current incident.",
            self_healing_result,
        )
    if self_healing_result and self_healing_result.get("status") in {
        "approved",
        "rejected",
        "completed",
    }:
        await publish_event(
            f"Self-healing status: {self_healing_result.get('status')}.",
            self_healing_result,
        )

    if customer_care_text:
        await publish_event(
            "Customer care communication package completed.",
            {"customer_care": customer_care_text},
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
        assigned_agents = set((commander_decision or {}).get("agents_to_run", []))
        if assigned_agents and role not in assigned_agents:
            continue
        participant = next(
            (item for item in band_config.participants if item.role == role),
            None,
        )
        if participant is None:
            continue
        try:
            await client.agent_api_messages.create_agent_chat_message(
                chat_id=room_id,
                message=ChatMessageRequest(
                    content=f"@{participant.display_name}\n\n{message}",
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
        except Exception as exc:
            warnings.append(f"Could not message {participant.display_name}: {exc}")

    outcome = {
        "qoe_status": qoe_result.get("qoe_status"),
        "playback_impact": (playback_impact or {}).get("impact_status"),
        "commander_decision": (commander_decision or {}).get("decision"),
        "self_healing_status": (self_healing_result or {}).get("status"),
    }
    await publish_event("Incident outcome recorded.", outcome)

    return {
        "published": True,
        "room_id": room_id,
        "participants_added": added_participants,
        "participant_messages_sent": published_messages,
        "rest_url": band_config.rest_url,
        "warnings": warnings,
    }


def run_band_publish(
    band_config: BandConfig,
    telemetry: dict[str, Any],
    qoe_result: dict[str, Any],
    diagnosis_text: str | None,
    recovery_text: str | None,
    customer_care_text: str | None,
    model_name: str,
    playback_impact: dict[str, Any] | None = None,
    commander_decision: dict[str, Any] | None = None,
    self_healing_result: dict[str, Any] | None = None,
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
                playback_impact,
                commander_decision,
                self_healing_result,
            )
        )
    except Exception as exc:
        return {"published": False, "error": str(exc)}
