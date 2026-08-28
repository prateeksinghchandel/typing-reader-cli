from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SETTINGS_FILE = DATA_DIR / "settings.json"
PROGRESS_FILE = DATA_DIR / "progress.json"
STATS_FILE = DATA_DIR / "stats.json"

JsonDict = dict[str, Any]


def _read_json(path: str | Path, default: JsonDict | None = None) -> JsonDict:
    file_path = Path(path)
    fallback: JsonDict = {} if default is None else dict(default)

    if not file_path.is_file():
        return fallback

    try:
        raw = file_path.read_text(encoding="utf-8").strip()
        if not raw:
            return fallback
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return fallback

    if not isinstance(data, dict):
        return fallback

    return data


def _write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(dict(payload), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def load_settings(path: str | Path = SETTINGS_FILE) -> JsonDict:
    return _read_json(path)


def save_settings(settings: Mapping[str, Any], path: str | Path = SETTINGS_FILE) -> None:
    _write_json(path, settings)


def load_progress(path: str | Path = PROGRESS_FILE) -> JsonDict:
    return _read_json(path)


def save_progress(progress: Mapping[str, Any], path: str | Path = PROGRESS_FILE) -> None:
    _write_json(path, progress)


def load_stats(path: str | Path = STATS_FILE) -> JsonDict:
    return _read_json(path)


def save_stats(stats: Mapping[str, Any], path: str | Path = STATS_FILE) -> None:
    _write_json(path, stats)
