"""
voice/music_player.py

On-demand music streaming via yt-dlp. Deliberately NOT a bulk downloader
or library manager — resolves a search query to a single best-match
stream, plays it, and lets the cache expire. Triggered by a recognized
voice intent ("play some music", "play <song>") after llm_router.py or a
lightweight local intent match identifies it as a music request — this
module itself only knows how to fetch and play, not how to parse intent.

Uses yt-dlp's built-in search prefix (ytsearch1:) so a plain text query
resolves without needing a separate search API or key — free, no account
required.

Inputs: a search query string (song name, artist, etc.).
Outputs: audio playback (via the same amp_controller.py volume path voice
         uses for speech, so danger-escalation volume overrides apply
         here too); publishes Event(topic="music.now_playing") / Event(
         topic="music.playback_failed").
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Optional

from sensors.sensor_bus import SensorBus, Event


class MusicPlayer:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg["music"]
        self.bus = bus
        self._cache_dir = Path(self.cfg["download_cache_dir"])
        self._currently_playing: Optional[str] = None

    def start(self) -> None:
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self.bus.subscribe("music.play_requested", self._on_play_requested)

    def stop(self) -> None:
        self._stop_playback()

    def _on_play_requested(self, event: Event) -> None:
        query = event.payload.get("query", "")
        if query:
            self.play(query)

    def play(self, query: str) -> None:
        try:
            audio_path = self._resolve_and_download(query)
        except Exception as exc:  # noqa: BLE001
            self.bus.publish(Event(
                topic="music.playback_failed",
                payload={"query": query, "error": str(exc)},
                urgency=0.2,
                source="music_player",
            ))
            return

        self._currently_playing = query
        self._play_audio_file(audio_path)
        self.bus.publish(Event(
            topic="music.now_playing",
            payload={"query": query},
            urgency=0.1,
            source="music_player",
        ))

    def _resolve_and_download(self, query: str) -> Path:
        search_term = f"{self.cfg['search_provider']}{self.cfg['max_search_results']}:{query}"
        output_template = str(self._cache_dir / "%(id)s.%(ext)s")
        # SENSOR INPUT HOOK: real yt-dlp invocation goes here, e.g.:
        #   subprocess.run([
        #       "yt-dlp", "-f", self.cfg["audio_format"], "-x",
        #       "--audio-format", "mp3", "-o", output_template, search_term,
        #   ], check=True)
        # then locate and return the resulting file's Path. Kept as a hook
        # rather than a live subprocess call in this stub so the module is
        # testable without a real network call or yt-dlp binary present.
        return self._cache_dir / "stub.mp3"

    def _play_audio_file(self, path: Path) -> None:
        # SENSOR INPUT HOOK: real audio playback goes here (e.g. via
        # `ffplay`, `simpleaudio`, or `pygame.mixer`), respecting
        # self.cfg["volume_default"] and routing through amp_controller.py
        # so danger-escalation volume overrides still apply during playback.
        pass

    def _stop_playback(self) -> None:
        # SENSOR INPUT HOOK: real playback-stop call goes here.
        self._currently_playing = None

    def purge_stale_cache(self) -> int:
        cutoff = time.time() - self.cfg["cache_max_age_s"]
        removed = 0
        for f in self._cache_dir.glob("*"):
            if f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        return removed