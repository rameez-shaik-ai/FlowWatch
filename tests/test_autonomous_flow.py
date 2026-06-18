from __future__ import annotations

import unittest

from agents.incident_commander_agent import fallback_incident_commander_decision
from services.self_healing_service import (
    apply_post_healing_telemetry,
    is_unsupported_healing_action,
    sanitize_healing_action,
)
from workflow.autonomous_orchestrator import is_self_healing_eligible


class AutonomousFlowTests(unittest.TestCase):
    def test_fallback_commander_uses_monitor_only_for_stable_playback(self) -> None:
        decision = fallback_incident_commander_decision(
            telemetry={"customer_id": "C1"},
            qoe_result={"qoe_status": "Good"},
            playback_impact={"impact_status": "Stable"},
        )
        self.assertEqual(decision["decision"], "monitor_only")
        self.assertEqual(decision["severity"], "Low")
        self.assertFalse(decision["band_room_required"])

    def test_fallback_commander_escalates_critical_playback(self) -> None:
        decision = fallback_incident_commander_decision(
            telemetry={"customer_id": "C1"},
            qoe_result={"qoe_status": "Poor"},
            playback_impact={"impact_status": "Critical"},
        )
        self.assertEqual(decision["decision"], "escalate")
        self.assertTrue(decision["customer_care_required"])
        self.assertIn("Customer Care Agent", decision["agents_to_run"])

    def test_post_healing_telemetry_improves_health_signals(self) -> None:
        healed = apply_post_healing_telemetry(
            {
                "bitrate_mbps": 2.1,
                "buffering_ratio": 8.5,
                "latency_ms": 180,
                "packet_loss": 3.2,
                "app_crashes": 1,
                "buffered_ahead_seconds": 1.5,
                "stall_count": 2,
            }
        )
        self.assertGreaterEqual(healed["bitrate_mbps"], 5.8)
        self.assertLessEqual(healed["buffering_ratio"], 1.2)
        self.assertEqual(healed["app_crashes"], 0)
        self.assertEqual(healed["stall_count"], 0)
        self.assertIn("qoe_score", healed)

    def test_unsupported_healing_action_is_blocked(self) -> None:
        self.assertEqual(sanitize_healing_action("router_factory_reset"), "none")
        self.assertTrue(is_unsupported_healing_action("router_factory_reset"))
        self.assertFalse(is_unsupported_healing_action("restart_streaming_app"))

    def test_manual_self_healing_requires_poor_qoe_and_two_severe_signals(self) -> None:
        eligible = is_self_healing_eligible(
            source_config={"mode": "Manual"},
            telemetry={
                "buffering_ratio": 7.0,
                "latency_ms": 190,
                "packet_loss": 0.8,
                "app_crashes": 0,
            },
            qoe_preview={"qoe_status": "Poor"},
            playback_impact=None,
            commander_decision={
                "decision": "self_heal",
                "recommended_healing_action": "restart_streaming_app",
                "human_approval_required": True,
            },
        )
        self.assertTrue(eligible)

    def test_live_embedded_self_healing_requires_confirmed_impact(self) -> None:
        eligible = is_self_healing_eligible(
            source_config={"mode": "Embedded HLS player", "player_scenario": "Live"},
            telemetry={},
            qoe_preview={"qoe_status": "Warning"},
            playback_impact={"impact_status": "Stable"},
            commander_decision={
                "decision": "self_heal",
                "recommended_healing_action": "refresh_streaming_session",
                "human_approval_required": True,
            },
        )
        self.assertFalse(eligible)


if __name__ == "__main__":
    unittest.main()
