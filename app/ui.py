from __future__ import annotations

from shutil import get_terminal_size

from app.engine import CharState, TypingEngine


RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
CYAN = "\033[36m"
YELLOW = "\033[33m"


def terminal_width(default: int = 80) -> int:
    return get_terminal_size((default, 24)).columns


def colorize(text: str, state: CharState | None) -> str:
    if state == CharState.CORRECT:
        return f"{GREEN}{text}{RESET}"
    if state == CharState.INCORRECT:
        return f"{RED}{text}{RESET}"
    return text


def render_target(target: str, engine: TypingEngine) -> str:
    rendered: list[str] = []
    for index, character in enumerate(target):
        rendered.append(colorize(character, engine.get_state(index)))
    if engine.finished() and not target:
        return ""
    return "".join(rendered)


def render_session(
    *,
    title: str,
    target: str,
    engine: TypingEngine,
    elapsed_seconds: float,
    width: int | None = None,
) -> str:
    total_width = width or terminal_width()
    header = f"{BOLD}{title}{RESET}"
    status = (
        f"{CYAN}Progress{RESET}: {engine.current_index()}/{len(target)}  "
        f"{CYAN}Accuracy{RESET}: {engine.get_accuracy():.1f}%  "
        f"{CYAN}Elapsed{RESET}: {elapsed_seconds:.1f}s"
    )
    if engine.finished():
        status += f"  {YELLOW}Done{RESET}"
    body = render_target(target, engine)
    separator = "-" * min(total_width, max(len(title), 10))
    return "\n".join([header, separator, body, "", status])


def render_idle_session(
    *,
    title: str,
    target: str,
    engine: TypingEngine,
    active_seconds: float,
    wall_seconds: float,
    idle_timeout_seconds: float,
    width: int | None = None,
) -> str:
    total_width = width or terminal_width()
    session_view = render_session(
        title=title,
        target=target,
        engine=engine,
        elapsed_seconds=active_seconds,
        width=total_width,
    )
    idle_note = (
        f"{YELLOW}Idle{RESET}: WPM is paused after "
        f"{idle_timeout_seconds:.0f}s of inactivity. "
        "Press any key to continue."
    )
    wall_note = f"{CYAN}Wall time{RESET}: {wall_seconds:.1f}s"
    separator = "-" * min(total_width, max(len(title), 10))
    return "\n".join([session_view, separator, wall_note, idle_note])


def render_menu(title: str, items: list[str]) -> str:
    lines = [f"{BOLD}{title}{RESET}"]
    for index, item in enumerate(items, start=1):
        lines.append(f"  {index}. {item}")
    return "\n".join(lines)


def render_message(message: str) -> str:
    return message
