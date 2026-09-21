from __future__ import annotations

from time import perf_counter


def get_viewport_range(target: str, cursor: int, width: int, height: int) -> tuple[int, int]:
    visible_lines = max(5, height - 4)
    visible_chars = visible_lines * width
    start = max(0, cursor - visible_chars // 2)
    end = min(len(target), start + visible_chars)
    return start, end


class SessionTimer:
    wall_started_at: float
    active_checkpoint: float
    active_seconds: float
    idle: bool
    last_activity_at: float

    def __init__(self, now: float) -> None:
        self.wall_started_at = now
        self.active_checkpoint = now
        self.active_seconds = 0.0
        self.idle = False
        self.last_activity_at = now

    @classmethod
    def start(cls) -> SessionTimer:
        return cls(perf_counter())

    def mark_timeout(self, now: float) -> None:
        if not self.idle:
            self.idle = True
            self.active_checkpoint = now

    def mark_key_event(self, now: float) -> None:
        if not self.idle:
            self.active_seconds += max(0.0, now - self.active_checkpoint)
        self.active_checkpoint = now
        self.last_activity_at = now
        self.idle = False

    def resume(self, now: float) -> None:
        self.last_activity_at = now
        if self.idle:
            self.idle = False
            self.active_checkpoint = now

    def active_elapsed(self, now: float) -> float:
        if self.idle:
            return self.active_seconds
        return self.active_seconds + max(0.0, now - self.active_checkpoint)

    def wall_elapsed(self, now: float) -> float:
        return max(0.0, now - self.wall_started_at)