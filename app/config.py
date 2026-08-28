from __future__ import annotations

import configparser
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONF_NAME = "typing-reader.conf"


@dataclass(frozen=True)
class RuntimeConfig:
    library_path: str | None = None
    width: int | None = None
    idle_timeout_seconds: float = 10.0
    tick_interval_seconds: float = 0.1
    show_header: bool = True
    show_footer: bool = True
    screen_align: str = "center top"
    screen_background: str = ""
    content_border: str = "round $accent"
    content_padding: str = "1 2"
    content_background: str = ""
    content_text: str = ""
    status_padding: str = "1 2"
    status_background: str = ""
    status_text: str = ""
    correct_style: str = "bold green"
    incorrect_style: str = "bold red"
    pending_style: str = "grey50"
    cursor_style: str = "reverse bold"
    idle_style: str = "yellow"
    done_style: str = "bold green"
    title_template: str = "{book} / {chapter}"
    choice_marker: str = ">"
    choice_help_text: str = "Use Up/Down and Enter. Esc goes back."
    choice_title_style: str = "bold"
    choice_selected_style: str = "bold cyan"
    choice_help_style: str = "dim"
    idle_message: str = "Idle: WPM is paused. Press any key to continue."
    summary_title: str = "Session Summary"
    summary_continue_prompt: str = "Press any key to continue. Esc or Ctrl+C quits."
    summary_title_style: str = "bold"
    summary_prompt_style: str = "yellow"


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_int(value: str | None, default: int | None) -> int | None:
    if value is None:
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default


def _parse_float(value: str | None, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value.strip())
    except ValueError:
        return default


def _parse_positive_int(value: str | None, default: int | None) -> int | None:
    parsed = _parse_int(value, default)
    if parsed is None or parsed <= 0:
        return default
    return parsed


def _parse_positive_float(value: str | None, default: float) -> float:
    parsed = _parse_float(value, default)
    if parsed <= 0:
        return default
    return parsed


def _candidate_paths(explicit: str | Path | None = None) -> list[Path]:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(Path(explicit))
    candidates.extend(
        [
            Path.cwd() / DEFAULT_CONF_NAME,
            Path(sys.argv[0]).resolve().with_suffix(".conf"),
            Path(sys.executable).resolve().with_suffix(".conf"),
            PROJECT_ROOT / DEFAULT_CONF_NAME,
        ]
    )
    seen: set[Path] = set()
    ordered: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve() if candidate.exists() else candidate
        if resolved in seen:
            continue
        seen.add(resolved)
        ordered.append(candidate)
    return ordered


def resolve_config_path(explicit: str | Path | None = None) -> Path | None:
    for candidate in _candidate_paths(explicit):
        if candidate.is_file():
            return candidate
    return None


def load_runtime_config(path: str | Path | None = None) -> tuple[RuntimeConfig, Path | None]:
    parser = configparser.ConfigParser()
    resolved_path = resolve_config_path(path)
    if resolved_path is not None:
        parser.read(resolved_path, encoding="utf-8")

    app_section = parser["app"] if parser.has_section("app") else {}
    ui_section = parser["ui"] if parser.has_section("ui") else {}
    style_section = parser["styles"] if parser.has_section("styles") else {}

    config = RuntimeConfig(
        library_path=app_section.get("library_path") or None,
        width=_parse_positive_int(app_section.get("width"), None),
        idle_timeout_seconds=_parse_positive_float(app_section.get("idle_timeout_seconds"), 10.0),
        tick_interval_seconds=_parse_positive_float(ui_section.get("tick_interval_seconds"), 0.1),
        show_header=_parse_bool(ui_section.get("show_header"), True),
        show_footer=_parse_bool(ui_section.get("show_footer"), True),
        screen_align=ui_section.get("screen_align", "center top"),
        screen_background=ui_section.get("screen_background", ""),
        content_border=ui_section.get("content_border", "round $accent"),
        content_padding=ui_section.get("content_padding", "1 2"),
        content_background=ui_section.get("content_background", ""),
        content_text=ui_section.get("content_text", ""),
        status_padding=ui_section.get("status_padding", "1 2"),
        status_background=ui_section.get("status_background", ""),
        status_text=ui_section.get("status_text", ""),
        correct_style=style_section.get("correct", "bold green"),
        incorrect_style=style_section.get("incorrect", "bold red"),
        pending_style=style_section.get("pending", "grey50"),
        cursor_style=style_section.get("cursor", "reverse bold"),
        idle_style=style_section.get("idle", "yellow"),
        done_style=style_section.get("done", "bold green"),
        title_template=ui_section.get("title_template", "{book} / {chapter}"),
        choice_marker=ui_section.get("choice_marker", ">"),
        choice_help_text=ui_section.get("choice_help_text", "Use Up/Down and Enter. Esc goes back."),
        choice_title_style=ui_section.get("choice_title_style", "bold"),
        choice_selected_style=ui_section.get("choice_selected_style", "bold cyan"),
        choice_help_style=ui_section.get("choice_help_style", "dim"),
        idle_message=ui_section.get("idle_message", "Idle: WPM is paused. Press any key to continue."),
        summary_title=ui_section.get("summary_title", "Session Summary"),
        summary_continue_prompt=ui_section.get(
            "summary_continue_prompt",
            "Press any key to continue. Esc or Ctrl+C quits.",
        ),
        summary_title_style=ui_section.get("summary_title_style", "bold"),
        summary_prompt_style=ui_section.get("summary_prompt_style", "yellow"),
    )
    return config, resolved_path


def build_textual_css(config: RuntimeConfig) -> str:
    header_rule = "Header { display: none; }" if not config.show_header else ""
    footer_rule = "Footer { display: none; }" if not config.show_footer else ""
    screen_rules = []
    if config.screen_background:
        screen_rules.append(f"background: {config.screen_background};")
    content_rules = []
    if config.content_background:
        content_rules.append(f"background: {config.content_background};")
    if config.content_text:
        content_rules.append(f"color: {config.content_text};")
    status_rules = []
    if config.status_background:
        status_rules.append(f"background: {config.status_background};")
    if config.status_text:
        status_rules.append(f"color: {config.status_text};")
    return f"""
    Screen {{
        align: {config.screen_align};
        {' '.join(screen_rules)}
    }}

    #content {{
        width: 100%;
        height: 1fr;
        padding: {config.content_padding};
        content-align: left top;
        border: {config.content_border};
        {' '.join(content_rules)}
    }}

    #status {{
        width: 100%;
        height: auto;
        padding: {config.status_padding};
        {' '.join(status_rules)}
    }}

    {header_rule}
    {footer_rule}
    """
