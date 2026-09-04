"""
brain/time_awareness.py

The companion's shared sense of "when is it." Every other module that
needs to reason about time — quiet hours, how long ago something
happened, whether today is a meaningful anniversary of a past incident —
should go through this module instead of calling datetime.now() directly
scattered across the codebase. That keeps time handling testable (you can
swap in a fake clock for tests) and keeps timezone/quiet-hours logic in
exactly one place.

Uses Python's real datetime module throughout — this is not a mock. All
persisted timestamps elsewhere in the system (episodic memory, people's
last_seen, etc.) are stored as raw epoch floats for sortability, but this
module is where those floats get turned into "this happened yesterday
evening" style human framing, and where "is it late at night right now"
gets decided.

Inputs: none required for basic queries (reads the system clock); accepts
        an epoch timestamp for historical framing.
Outputs: structured "TimeContext" snapshots consumed by prompt_builder.py
         (so the LLM knows what day/time it "is"), and by any module
         deciding whether now is an appropriate moment to be loud/quiet.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time as dtime, timedelta
from typing import Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python <3.9 fallback path
    ZoneInfo = None  # type: ignore[assignment,misc]


@dataclass
class TimeContext:
    """A snapshot of 'now', framed the way a prompt or a rule needs it."""

    now: datetime
    is_quiet_hours: bool
    day_of_week: str          # "Monday", ..., useful for prompt_builder phrasing
    human_time_of_day: str    # "early morning" / "afternoon" / "late night" etc.


class TimeAwareness:
    def __init__(self, cfg: dict):
        self.cfg = cfg["time_awareness"]
        self._tz = self._resolve_timezone(self.cfg["timezone"])
        self._quiet_start = self._parse_hhmm(self.cfg["quiet_hours_start"])
        self._quiet_end = self._parse_hhmm(self.cfg["quiet_hours_end"])
        self._last_observed_now: Optional[datetime] = None

    def _resolve_timezone(self, tz_name: str):
        if ZoneInfo is None:
            return None  # naive local time fallback
        try:
            return ZoneInfo(tz_name)
        except Exception:  # noqa: BLE001 — bad tz string shouldn't crash boot
            return None

    def _parse_hhmm(self, hhmm: str) -> dtime:
        hour, minute = (int(part) for part in hhmm.split(":"))
        return dtime(hour=hour, minute=minute)

    def now(self) -> datetime:
        """The single source of truth for 'what time is it right now.'"""
        current = datetime.now(self._tz) if self._tz else datetime.now()
        self._last_observed_now = current
        return current

    def today_str(self) -> str:
        """ISO date string for 'today,' used when tagging new memories."""
        return self.now().date().isoformat()

    def context(self) -> TimeContext:
        current = self.now()
        return TimeContext(
            now=current,
            is_quiet_hours=self._is_quiet_hours(current),
            day_of_week=current.strftime("%A"),
            human_time_of_day=self._human_time_of_day(current),
        )

    def _is_quiet_hours(self, current: datetime) -> bool:
        current_time = current.time()
        if self._quiet_start <= self._quiet_end:
            return self._quiet_start <= current_time <= self._quiet_end
        # quiet window wraps past midnight (e.g. 22:30 -> 07:00)
        return current_time >= self._quiet_start or current_time <= self._quiet_end

    def _human_time_of_day(self, current: datetime) -> str:
        hour = current.hour
        if hour < 5:
            return "the dead of night"
        if hour < 8:
            return "early morning"
        if hour < 12:
            return "morning"
        if hour < 17:
            return "afternoon"
        if hour < 21:
            return "evening"
        return "late night"

    def humanize_past_timestamp(self, epoch_seconds: float) -> str:
        """
        Turns a raw stored timestamp into the kind of phrase a creature
        with a sense of time would actually say ("earlier today", "a
        couple days ago", "last month") — used when memory context is
        assembled for prompt_builder.py so recollection sounds natural
        rather than robotic ("event occurred at timestamp 1739...").
        """
        then = datetime.fromtimestamp(epoch_seconds, tz=self._tz) if self._tz else datetime.fromtimestamp(epoch_seconds)
        delta = self.now() - then
        if delta < timedelta(hours=1):
            return "just a little while ago"
        if delta < timedelta(hours=12) and then.date() == self.now().date():
            return "earlier today"
        if delta < timedelta(days=2):
            return "yesterday"
        if delta < timedelta(days=7):
            return f"{delta.days} days ago"
        if delta < timedelta(days=31):
            return f"about {delta.days // 7} week(s) ago"
        if delta < timedelta(days=365):
            return f"about {delta.days // 30} month(s) ago"
        return f"about {delta.days // 365} year(s) ago"

    def is_anniversary_of(self, epoch_seconds: float, tolerance_days: int = 1) -> bool:
        """
        True if today's month/day is within tolerance_days of the given
        past timestamp's month/day, ignoring year — powers the "seasonal
        callback" idea (TOP_20_IDEAS #20): resurfacing an old notable
        incident around its actual anniversary.
        """
        then = datetime.fromtimestamp(epoch_seconds, tz=self._tz) if self._tz else datetime.fromtimestamp(epoch_seconds)
        today = self.now().date()
        this_year_anniversary = then.date().replace(year=today.year)
        return abs((today - this_year_anniversary).days) <= tolerance_days

    def clock_looks_stale(self) -> bool:
        """
        Sanity check: if we've never observed the clock moving forward, or
        it appears frozen, something's wrong at the OS/hardware level
        (common on a Pi with no RTC battery and no network to sync via
        NTP). Used by network/connection_watchdog.py-style logic to decide
        whether "the date looks wrong" is itself worth calling for help
        about.
        """
        if self._last_observed_now is None:
            return False
        elapsed = (datetime.now(self._tz) if self._tz else datetime.now()) - self._last_observed_now
        return elapsed.total_seconds() > self.cfg["stale_clock_warn_after_s"]