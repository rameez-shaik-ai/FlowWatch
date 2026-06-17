from __future__ import annotations

import unittest

from services.playback_impact_gate import evaluate_playback_impact


class PlaybackImpactGateTests(unittest.TestCase):
    def test_good_qoe_with_raw_stalls_and_healthy_buffer_is_not_critical(self) -> None:
        telemetry = {
            "qoe_score": 89,
            "player_state": "buffering",
            "buffered_ahead_seconds": 11.2,
            "playback_time_moving": True,
            "resolution": "1920x1080",
            "dropped_frames": 6,
            "total_frames": 1310,
            "stall_count": 2,
        }
        result = evaluate_playback_impact(telemetry, "Good")
        self.assertIn(result["impact_status"], {"Stable", "At Risk"})
        self.assertFalse(result["should_run_diagnosis"])
        self.assertFalse(result["should_run_recovery"])
        self.assertFalse(result["should_run_customer_care"])

    def test_poor_qoe_with_critical_buffer_and_stuck_playback_is_critical(self) -> None:
        telemetry = {
            "player_state": "buffering",
            "buffered_ahead_seconds": 1.5,
            "playback_time_moving": False,
            "resolution": "640x360",
            "dropped_frames": 120,
            "total_frames": 1800,
            "stall_count": 2,
        }
        result = evaluate_playback_impact(telemetry, "Poor")
        self.assertEqual(result["impact_status"], "Critical")

    def test_warning_qoe_with_usable_buffer_and_raw_stall_is_at_risk(self) -> None:
        telemetry = {
            "player_state": "playing",
            "buffered_ahead_seconds": 7.0,
            "playback_time_moving": True,
            "resolution": "1280x720",
            "dropped_frames": 12,
            "total_frames": 700,
            "stall_count": 1,
        }
        result = evaluate_playback_impact(telemetry, "Warning")
        self.assertEqual(result["impact_status"], "At Risk")

    def test_poor_qoe_with_low_buffer_and_stuck_buffering_is_confirmed_or_critical(self) -> None:
        telemetry = {
            "player_state": "buffering",
            "buffered_ahead_seconds": 3.0,
            "playback_time_moving": False,
            "resolution": "854x480",
            "dropped_frames": 40,
            "total_frames": 1000,
            "stall_count": 1,
        }
        result = evaluate_playback_impact(telemetry, "Poor")
        self.assertIn(result["impact_status"], {"Impact Confirmed", "Critical"})


if __name__ == "__main__":
    unittest.main()
