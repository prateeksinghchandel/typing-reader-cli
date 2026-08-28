from __future__ import annotations

from dataclasses import dataclass, asdict

from app.engine import TypingEngine


@dataclass(frozen=True)
class SessionStats:
    target_length: int
    typed_length: int
    correct: int
    incorrect: int
    accuracy: float
    duration_seconds: float
    wall_seconds: float
    idle_seconds: float
    words_per_minute: float
    completed: bool

    def to_dict(self) -> dict[str, float | int | bool]:
        return asdict(self)


def calculate_wpm(characters_typed: int, elapsed_seconds: float) -> float:
    if elapsed_seconds <= 0:
        return 0.0
    return (characters_typed / 5.0) / (elapsed_seconds / 60.0)


def build_session_stats(
    target_text: str,
    engine: TypingEngine,
    active_seconds: float,
    wall_seconds: float | None = None,
) -> SessionStats:
    total_wall_seconds = active_seconds if wall_seconds is None else wall_seconds
    typed_length = engine.current_index()
    return SessionStats(
        target_length=len(target_text),
        typed_length=typed_length,
        correct=engine.correct,
        incorrect=engine.incorrect,
        accuracy=engine.get_accuracy(),
        duration_seconds=active_seconds,
        wall_seconds=total_wall_seconds,
        idle_seconds=max(0.0, total_wall_seconds - active_seconds),
        words_per_minute=calculate_wpm(typed_length, active_seconds),
        completed=engine.finished(),
    )
