from __future__ import annotations

import random
from textwrap import dedent
from typing import Any

from utils.qoe_scoring import calculate_qoe_score


DEFAULT_HLS_STREAM_URL = "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"


def build_hls_player_html(stream_url: str) -> str:
    return dedent(
        f"""
        <!doctype html>
        <html>
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
          <style>
            body {{
              margin: 0;
              font-family: Inter, Segoe UI, Roboto, Arial, sans-serif;
              background: #0b1710;
              color: #f8fafc;
            }}
            .player-shell {{
              background: linear-gradient(180deg, #102218 0%, #0c1b14 100%);
              border: 1px solid rgba(74, 222, 128, 0.18);
              border-radius: 20px;
              padding: 14px;
              box-sizing: border-box;
            }}
            .player-title {{
              display: flex;
              align-items: center;
              justify-content: space-between;
              gap: 12px;
              margin-bottom: 12px;
            }}
            .player-title h3 {{
              margin: 0;
              font-size: 16px;
              font-weight: 800;
              color: #f8fafc;
            }}
            .player-badge {{
              display: inline-flex;
              align-items: center;
              border-radius: 999px;
              padding: 6px 10px;
              background: rgba(34, 197, 94, 0.12);
              border: 1px solid rgba(34, 197, 94, 0.24);
              color: #86efac;
              font-size: 12px;
              font-weight: 700;
              white-space: nowrap;
            }}
            video {{
              width: 100%;
              max-height: 300px;
              border-radius: 16px;
              background: #000;
              display: block;
            }}
            .telemetry-panel {{
              margin-top: 10px;
              display: grid;
              grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
              gap: 8px;
            }}
            .metric {{
              background: rgba(14, 31, 22, 0.92);
              border: 1px solid rgba(74, 222, 128, 0.16);
              border-radius: 14px;
              padding: 9px;
              min-height: 66px;
              box-sizing: border-box;
            }}
            .metric-label {{
              font-size: 10px;
              color: #a7f3d0;
              margin-bottom: 5px;
              text-transform: uppercase;
              letter-spacing: 0.06em;
            }}
            .metric-value {{
              font-size: 13px;
              font-weight: 700;
              color: #f8fafc;
              word-break: break-word;
              line-height: 1.25;
            }}
            .player-note {{
              margin-top: 10px;
              font-size: 11px;
              color: #a7f3d0;
              line-height: 1.45;
              padding: 9px 11px;
              border-radius: 14px;
              background: rgba(34, 197, 94, 0.08);
              border: 1px solid rgba(74, 222, 128, 0.12);
            }}
          </style>
        </head>
        <body>
          <div class="player-shell">
            <div class="player-title">
              <h3>Embedded HLS Player</h3>
              <span class="player-badge">Live browser telemetry preview</span>
            </div>
            <video id="video" controls playsinline muted></video>
            <div class="telemetry-panel">
              <div class="metric"><div class="metric-label">Player state</div><div class="metric-value" id="playerState">idle</div></div>
              <div class="metric"><div class="metric-label">Playback time</div><div class="metric-value" id="currentTime">0.0 s</div></div>
              <div class="metric"><div class="metric-label">Buffered ahead</div><div class="metric-value" id="bufferedAhead">0.0 s</div></div>
              <div class="metric"><div class="metric-label">Resolution</div><div class="metric-value" id="resolution">-</div></div>
              <div class="metric"><div class="metric-label">Dropped frames</div><div class="metric-value" id="droppedFrames">-</div></div>
              <div class="metric"><div class="metric-label">Total frames</div><div class="metric-value" id="totalFrames">-</div></div>
              <div class="metric"><div class="metric-label">Ready state</div><div class="metric-value" id="readyState">0</div></div>
              <div class="metric"><div class="metric-label">Network state</div><div class="metric-value" id="networkState">0</div></div>
            </div>
            <div class="player-note">
              Browser player telemetry preview — mapped values are simulated in Streamlit for this prototype.
              Production would stream actual player SDK telemetry back into the backend via a custom bidirectional component.
            </div>
          </div>
          <script>
            const video = document.getElementById("video");
            let playerState = "idle";

            function setText(id, value) {{
              const el = document.getElementById(id);
              if (el) el.textContent = value;
            }}

            function updateState(nextState) {{
              playerState = nextState;
              setText("playerState", nextState);
            }}

            function bufferedAheadSeconds() {{
              try {{
                if (!video.buffered || video.buffered.length === 0) return 0;
                const end = video.buffered.end(video.buffered.length - 1);
                return Math.max(0, end - video.currentTime);
              }} catch (e) {{
                return 0;
              }}
            }}

            function updateTelemetry() {{
              setText("playerState", playerState);
              setText("currentTime", `${{video.currentTime.toFixed(1)}} s`);
              setText("bufferedAhead", `${{bufferedAheadSeconds().toFixed(1)}} s`);
              const resolution = video.videoWidth && video.videoHeight
                ? `${{video.videoWidth}}x${{video.videoHeight}}`
                : "-";
              setText("resolution", resolution);
              setText("readyState", String(video.readyState));
              setText("networkState", String(video.networkState));

              if (typeof video.getVideoPlaybackQuality === "function") {{
                const quality = video.getVideoPlaybackQuality();
                setText("droppedFrames", String(quality.droppedVideoFrames ?? "-"));
                setText("totalFrames", String(quality.totalVideoFrames ?? "-"));
              }} else {{
                setText("droppedFrames", "-");
                setText("totalFrames", "-");
              }}
            }}

            ["play", "playing"].forEach((eventName) =>
              video.addEventListener(eventName, () => updateState("playing"))
            );
            ["pause"].forEach((eventName) =>
              video.addEventListener(eventName, () => updateState("paused"))
            );
            ["waiting", "stalled"].forEach((eventName) =>
              video.addEventListener(eventName, () => updateState("buffering"))
            );
            video.addEventListener("error", () => updateState("error"));
            video.addEventListener("ended", () => updateState("ended"));

            if (video.canPlayType("application/vnd.apple.mpegurl")) {{
              video.src = "{stream_url}";
            }} else if (window.Hls && Hls.isSupported()) {{
              const hls = new Hls();
              hls.loadSource("{stream_url}");
              hls.attachMedia(video);
              hls.on(Hls.Events.MANIFEST_PARSED, () => updateState("ready"));
              hls.on(Hls.Events.ERROR, () => updateState("error"));
            }} else {{
              updateState("unsupported");
              const fallback = document.createElement("div");
              fallback.className = "player-note";
              fallback.textContent = "This browser does not support HLS playback in this embedded preview.";
              document.querySelector(".player-shell").appendChild(fallback);
            }}

            updateTelemetry();
            setInterval(updateTelemetry, 1000);
          </script>
        </body>
        </html>
        """
    )


def get_initial_player_telemetry() -> dict[str, Any]:
    telemetry = {
        "customer_id": "LIVE_PLAYER_001",
        "device_id": "BROWSER_HLS_PLAYER",
        "service": "Embedded HLS stream",
        "bitrate_mbps": 7.2,
        "buffering_ratio": 0.6,
        "latency_ms": 58,
        "packet_loss": 0.2,
        "app_crashes": 0,
        "player_state": "playing",
        "playback_time_seconds": 14.0,
        "buffered_ahead_seconds": 18.5,
        "resolution": "1920x1080",
        "dropped_frames": 6,
        "total_frames": 980,
        "ready_state": 4,
        "network_state": 1,
        "stall_count": 0,
        "playback_time_moving": True,
    }
    telemetry["qoe_score"] = calculate_qoe_score(telemetry)
    return telemetry


def generate_dynamic_player_telemetry(tick: int, scenario: str = "Auto") -> dict[str, Any]:
    scenario = scenario or "Auto"
    rng = random.Random(1000 + tick * 17)

    if scenario == "Healthy":
        telemetry = {
            "customer_id": "LIVE_PLAYER_001",
            "device_id": "BROWSER_HLS_PLAYER",
            "service": "Embedded HLS stream",
            "bitrate_mbps": round(5.5 + (tick % 4) * 0.7 + rng.uniform(0.0, 0.25), 1),
            "buffering_ratio": round(0.2 + rng.uniform(0.0, 1.2), 1),
            "latency_ms": int(40 + (tick % 5) * 9 + rng.uniform(0, 6)),
            "packet_loss": round(rng.uniform(0.0, 0.6), 1),
            "app_crashes": 0,
            "player_state": "playing",
            "playback_time_seconds": round(8 + tick * 2.8, 1),
            "buffered_ahead_seconds": round(rng.uniform(12.0, 25.0), 1),
            "resolution": "1920x1080" if tick % 3 else "1280x720",
            "dropped_frames": 4 + (tick % 5),
            "total_frames": 900 + tick * 45,
            "ready_state": 4,
            "network_state": 1,
            "stall_count": 0,
            "playback_time_moving": True,
        }
    elif scenario == "Degraded":
        total_frames = 760 + tick * 26
        dropped_frames = max(24, int(total_frames * (0.032 + (tick % 3) * 0.011)))
        telemetry = {
            "customer_id": "LIVE_PLAYER_001",
            "device_id": "BROWSER_HLS_PLAYER",
            "service": "Embedded HLS stream",
            "bitrate_mbps": round(1.2 + rng.uniform(0.0, 1.6), 1),
            "buffering_ratio": round(5.5 + rng.uniform(0.0, 5.0), 1),
            "latency_ms": int(150 + rng.uniform(0, 110)),
            "packet_loss": round(2.0 + rng.uniform(0.0, 2.5), 1),
            "app_crashes": 0 if tick % 5 else 1,
            "player_state": "buffering" if tick % 2 == 0 else "waiting",
            "playback_time_seconds": round(18 + tick * 0.3, 1),
            "buffered_ahead_seconds": round(rng.uniform(0.5, 4.0), 1),
            "resolution": "854x480" if tick % 2 == 0 else "640x360",
            "dropped_frames": dropped_frames,
            "total_frames": total_frames,
            "ready_state": 2 if tick % 2 == 0 else 1,
            "network_state": 2,
            "stall_count": 1 + (1 if tick % 4 == 0 else 0),
            "playback_time_moving": False if tick % 3 else True,
        }
    elif scenario == "Recovering":
        progress = min(1.0, max(0.0, tick / 6))
        total_frames = 820 + tick * 34
        dropped_frames = max(6, int(total_frames * max(0.007, 0.04 - progress * 0.028)))
        telemetry = {
            "customer_id": "LIVE_PLAYER_001",
            "device_id": "BROWSER_HLS_PLAYER",
            "service": "Embedded HLS stream",
            "bitrate_mbps": round(2.2 + progress * 5.2 + rng.uniform(-0.2, 0.2), 1),
            "buffering_ratio": round(max(0.2, 8.0 - progress * 6.8 + rng.uniform(-0.3, 0.3)), 1),
            "latency_ms": int(max(45, 220 - progress * 150 + rng.uniform(-10, 8))),
            "packet_loss": round(max(0.0, 3.4 - progress * 3.0 + rng.uniform(-0.2, 0.2)), 1),
            "app_crashes": 0,
            "player_state": "playing" if progress >= 0.5 else "waiting",
            "playback_time_seconds": round(12 + tick * (0.9 + progress * 1.8), 1),
            "buffered_ahead_seconds": round(min(14.0, 2.0 + progress * 11.0 + rng.uniform(-0.4, 0.4)), 1),
            "resolution": (
                "640x360"
                if progress < 0.25
                else "854x480"
                if progress < 0.55
                else "1280x720"
                if progress < 0.85
                else "1920x1080"
            ),
            "dropped_frames": dropped_frames,
            "total_frames": total_frames,
            "ready_state": 3 if progress < 0.5 else 4,
            "network_state": 2 if progress < 0.4 else 1,
            "stall_count": 1 if progress < 0.6 else 0,
            "playback_time_moving": progress >= 0.35,
        }
    else:
        cycle = tick % 24
        if cycle <= 7:
            return generate_dynamic_player_telemetry(tick, "Healthy")
        if cycle <= 12:
            telemetry = generate_dynamic_player_telemetry(tick, "Healthy")
            telemetry.update(
                {
                    "bitrate_mbps": round(max(4.4, telemetry["bitrate_mbps"] - 1.2), 1),
                    "buffering_ratio": round(min(3.2, telemetry["buffering_ratio"] + 1.4), 1),
                    "latency_ms": int(min(135, telemetry["latency_ms"] + 42)),
                    "packet_loss": round(min(1.6, telemetry["packet_loss"] + 0.7), 1),
                    "buffered_ahead_seconds": round(rng.uniform(5.5, 9.5), 1),
                    "resolution": "1280x720",
                    "dropped_frames": 18 + (tick % 4),
                    "total_frames": 920 + tick * 30,
                    "stall_count": 0,
                    "playback_time_moving": True,
                }
            )
            telemetry["qoe_score"] = calculate_qoe_score(telemetry)
            return telemetry
        if cycle <= 17:
            return generate_dynamic_player_telemetry(tick, "Degraded")
        return generate_dynamic_player_telemetry(cycle - 17, "Recovering")

    telemetry["qoe_score"] = calculate_qoe_score(telemetry)
    return telemetry


def map_live_player_metrics_to_telemetry(
    metrics: dict[str, Any] | None,
    previous_telemetry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    previous = previous_telemetry or get_initial_player_telemetry()
    if not metrics:
        return previous.copy()

    resolution = str(metrics.get("resolution") or "unknown")
    bitrate_lookup = {
        "1920x1080": 6.0,
        "1280x720": 3.5,
        "854x480": 1.8,
        "640x360": 1.0,
    }
    bitrate_mbps = bitrate_lookup.get(
        resolution, float(previous.get("bitrate_mbps", 3.0))
    )

    player_state = str(metrics.get("player_state") or "idle")
    buffered_ahead_seconds = float(metrics.get("buffered_ahead_seconds", 0.0) or 0.0)
    playback_time_moving = bool(metrics.get("playback_time_moving", False))

    if player_state in {"buffering", "waiting"} and not playback_time_moving:
        buffering_ratio = 8.0
    elif buffered_ahead_seconds < 3:
        buffering_ratio = 6.5
    elif buffered_ahead_seconds < 5:
        buffering_ratio = 4.0
    elif buffered_ahead_seconds < 10:
        buffering_ratio = 2.0
    else:
        buffering_ratio = 0.8

    if player_state == "error":
        latency_ms = 250
    elif buffered_ahead_seconds < 3:
        latency_ms = 190
    elif buffered_ahead_seconds < 5:
        latency_ms = 150
    elif buffered_ahead_seconds < 10:
        latency_ms = 110
    else:
        latency_ms = 65

    dropped_frames = int(metrics.get("dropped_frames", 0) or 0)
    total_frames = int(metrics.get("total_frames", 0) or 0)
    dropped_frame_ratio = (dropped_frames / total_frames) if total_frames > 0 else 0.0
    if dropped_frame_ratio >= 0.05:
        packet_loss = 3.5
    elif dropped_frame_ratio >= 0.03:
        packet_loss = 2.5
    elif dropped_frame_ratio >= 0.02:
        packet_loss = 1.5
    else:
        packet_loss = 0.4

    telemetry = {
        "customer_id": "LIVE_PLAYER_001",
        "device_id": "BROWSER_HLS_PLAYER",
        "service": "Embedded HLS stream",
        "bitrate_mbps": bitrate_mbps,
        "buffering_ratio": buffering_ratio,
        "latency_ms": latency_ms,
        "packet_loss": packet_loss,
        "app_crashes": 1 if player_state == "error" else 0,
        "player_state": player_state,
        "playback_time_seconds": float(metrics.get("playback_time_seconds", 0.0) or 0.0),
        "buffered_ahead_seconds": buffered_ahead_seconds,
        "resolution": resolution,
        "dropped_frames": dropped_frames,
        "total_frames": total_frames,
        "ready_state": int(metrics.get("ready_state", 0) or 0),
        "network_state": int(metrics.get("network_state", 0) or 0),
        "stall_count": int(metrics.get("stall_count", 0) or 0),
        "playback_time_moving": playback_time_moving,
        "last_update_epoch_ms": int(metrics.get("last_update_epoch_ms", 0) or 0),
    }
    telemetry["qoe_score"] = calculate_qoe_score(telemetry)
    return telemetry
