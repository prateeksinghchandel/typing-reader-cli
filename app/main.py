from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter, sleep
from dataclasses import dataclass
from typing import Protocol

from app.config import RuntimeConfig, load_runtime_config
from app.engine import TypingEngine
from app.loader import BookLoader
from app.reader import Reader
from app.stats import build_session_stats
from app.storage import (
    load_progress,
    load_settings,
    load_stats,
    save_progress,
    save_settings,
    save_stats,
)
from app import ui


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LIBRARY_DIR = PROJECT_ROOT / "books"
DEFAULT_IDLE_TIMEOUT_SECONDS = 10.0
POLL_INTERVAL_SECONDS = 0.05


class KeyReader(Protocol):
    def read(self, timeout: float | None) -> str | None: ...

    def close(self) -> None: ...


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Typing trainer for reading books")
    parser.add_argument(
        "library_path",
        nargs="?",
        help="Path to a book library directory containing book folders",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=None,
        help="Terminal width to use for rendering",
    )
    parser.add_argument(
        "--idle-timeout",
        type=float,
        default=None,
        help="Seconds of inactivity before showing the idle screen",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to a typing-reader .conf file",
    )
    return parser.parse_args(argv)


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def prompt_for_library_path(default: str | None = None) -> str:
    if default:
        prompt = f"Library path [{default}]: "
    else:
        prompt = "Library path: "
    value = input(prompt).strip()
    return value or (default or "")


def choose_index(title: str, items: list[str]) -> int:
    if not items:
        raise ValueError("items cannot be empty")

    while True:
        clear_screen()
        print(ui.render_menu(title, items))
        choice = input("\nChoose a number: ").strip()
        try:
            index = int(choice) - 1
        except ValueError:
            continue
        if 0 <= index < len(items):
            return index


def choose_preferred_index(items: list[str], preferred_name: str | None) -> int | None:
    if not preferred_name:
        return None
    for index, item in enumerate(items):
        if item == preferred_name:
            return index
    return None


def choose_book(loader: BookLoader, previous_progress: dict[str, object]) -> Path:
    books = loader.list_books()
    if not books:
        raise ValueError("No books found")

    preferred_name = (
        str(previous_progress.get("book"))
        if previous_progress.get("book")
        else None
    )
    preferred_index = choose_preferred_index([book.name for book in books], preferred_name)
    if preferred_index is not None:
        return books[preferred_index]
    return books[choose_index("Books", [book.name for book in books])]


def choose_chapter(
    loader: BookLoader,
    book: Path,
    previous_progress: dict[str, object],
) -> Path:
    chapters = loader.list_chapters(book.name)
    if not chapters:
        raise ValueError(f"No .txt chapters found in {book}")

    preferred_name = (
        str(previous_progress.get("chapter"))
        if previous_progress.get("chapter")
        else None
    )
    preferred_index = choose_preferred_index([chapter.name for chapter in chapters], preferred_name)
    if preferred_index is not None:
        return chapters[preferred_index]
    return chapters[choose_index("Chapters", [chapter.name for chapter in chapters])]


def _resolve_library_path(
    *,
    args_library_path: str | None,
    runtime_config: RuntimeConfig,
    config_loaded: bool,
    settings: dict[str, object],
) -> str | None:
    if args_library_path:
        return args_library_path
    if config_loaded and runtime_config.library_path:
        return runtime_config.library_path
    if not config_loaded:
        stored_library_path = settings.get("library_path")
        if stored_library_path:
            return str(stored_library_path)
    return None


def _resolve_render_width(
    *,
    args_width: int | None,
    runtime_config: RuntimeConfig,
    config_loaded: bool,
    settings: dict[str, object],
) -> int:
    if args_width is not None:
        return args_width
    if config_loaded and runtime_config.width is not None:
        return runtime_config.width
    if not config_loaded:
        stored_width = settings.get("width")
        if stored_width is not None:
            return int(stored_width)
    return ui.terminal_width()


def _resolve_idle_timeout_seconds(
    *,
    args_idle_timeout: float | None,
    runtime_config: RuntimeConfig,
    config_loaded: bool,
    settings: dict[str, object],
) -> float:
    if args_idle_timeout is not None:
        return args_idle_timeout
    if config_loaded:
        return runtime_config.idle_timeout_seconds
    stored_timeout = settings.get("idle_timeout_seconds")
    if stored_timeout is not None:
        return float(stored_timeout)
    return DEFAULT_IDLE_TIMEOUT_SECONDS


@dataclass
class SessionTimer:
    wall_started_at: float
    active_checkpoint: float
    active_seconds: float = 0.0
    idle: bool = False

    @classmethod
    def start(cls, now: float) -> "SessionTimer":
        return cls(wall_started_at=now, active_checkpoint=now)

    def mark_timeout(self, now: float) -> None:
        if not self.idle:
            self.idle = True
            self.active_checkpoint = now

    def mark_key_event(self, now: float) -> None:
        if not self.idle:
            self.active_seconds += max(0.0, now - self.active_checkpoint)
        self.active_checkpoint = now
        self.idle = False

    def active_elapsed(self, now: float) -> float:
        if self.idle:
            return self.active_seconds
        return self.active_seconds + max(0.0, now - self.active_checkpoint)

    def wall_elapsed(self, now: float) -> float:
        return max(0.0, now - self.wall_started_at)


class WindowsPollingKeyReader:
    def __init__(self) -> None:
        import msvcrt

        self._msvcrt = msvcrt

    def read(self, timeout: float | None) -> str | None:
        deadline = None if timeout is None else perf_counter() + timeout
        while True:
            if self._msvcrt.kbhit():
                key = self._msvcrt.getwch()
                if key in ("\x00", "\xe0"):
                    self._msvcrt.getwch()
                    continue
                if key == "\r":
                    return "\n"
                return key
            if deadline is not None and perf_counter() >= deadline:
                return None
            sleep(POLL_INTERVAL_SECONDS)

    def close(self) -> None:
        return None


class ThreadedKeyReader:
    def __init__(self) -> None:
        import queue
        import threading

        self._queue: queue.Queue[str] = queue.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def _read_key(self) -> str:
        import readchar

        key = readchar.readkey()
        if key == readchar.key.ENTER:
            return "\n"
        return key

    def _worker(self) -> None:
        while not self._stop.is_set():
            key = self._read_key()
            self._queue.put(key)
            if key == "\x03":
                return

    def read(self, timeout: float | None) -> str | None:
        import queue

        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self) -> None:
        self._stop.set()


def create_key_reader() -> KeyReader:
    if os.name == "nt":
        return WindowsPollingKeyReader()
    return ThreadedKeyReader()


def run_textual_typing_session(
    *,
    library_path: Path,
    book_name: str,
    chapter_path: Path,
    width: int,
    idle_timeout_seconds: float = DEFAULT_IDLE_TIMEOUT_SECONDS,
    runtime_config: RuntimeConfig | None = None,
) -> dict[str, object] | None:
    try:
        from app.tui import run_textual_session
    except ImportError:
        return run_typing_session(
            book_name=book_name,
            chapter_path=chapter_path,
            width=width,
            idle_timeout_seconds=idle_timeout_seconds,
        )

    return run_textual_session(
        library_path=library_path,
        book_name=book_name,
        chapter_path=chapter_path,
        width=width,
        idle_timeout_seconds=idle_timeout_seconds,
        runtime_config=runtime_config or RuntimeConfig(),
    )


def run_typing_session(
    *,
    book_name: str,
    chapter_path: Path,
    width: int,
    idle_timeout_seconds: float = DEFAULT_IDLE_TIMEOUT_SECONDS,
    key_reader: KeyReader | None = None,
    clock=perf_counter,
) -> dict[str, object]:
    reader = Reader()
    target = reader.load(chapter_path)
    engine = TypingEngine(target)
    input_reader = key_reader or create_key_reader()
    timer = SessionTimer.start(clock())
    last_event_now = timer.wall_started_at

    try:
        while not engine.finished():
            display_now = clock()
            clear_screen()
            if timer.idle:
                print(
                    ui.render_idle_session(
                        title=f"{book_name} / {chapter_path.name}",
                        target=target,
                        engine=engine,
                        active_seconds=timer.active_elapsed(display_now),
                        wall_seconds=timer.wall_elapsed(display_now),
                        idle_timeout_seconds=idle_timeout_seconds,
                        width=width,
                    )
                )
            else:
                print(
                    ui.render_session(
                        title=f"{book_name} / {chapter_path.name}",
                        target=target,
                        engine=engine,
                        elapsed_seconds=timer.active_elapsed(display_now),
                        width=width,
                    )
                )

            key = input_reader.read(timeout=idle_timeout_seconds)
            event_now = clock()
            if key in ("\x08", "\x7f"):
                timer.mark_key_event(event_now)
                last_event_now = event_now
                engine.backspace()
            elif key == "\x03":
                raise KeyboardInterrupt
            elif key is None:
                timer.mark_timeout(event_now)
                last_event_now = event_now
            else:
                timer.mark_key_event(event_now)
                last_event_now = event_now
                engine.process_key(key)
    except KeyboardInterrupt:
        pass
    finally:
        close = getattr(input_reader, "close", None)
        if callable(close):
            close()

    stats = build_session_stats(
        target,
        engine,
        timer.active_seconds,
        wall_seconds=max(0.0, last_event_now - timer.wall_started_at),
    )
    progress = {
        "book": book_name,
        "chapter": chapter_path.name,
        "cursor": engine.current_index(),
        "completed": engine.finished(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_chars": len(target),
    }
    return {
        "stats": stats.to_dict(),
        "progress": progress,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    runtime_config, config_path = load_runtime_config(args.config)
    config_loaded = config_path is not None
    settings = load_settings()
    previous_progress = load_progress()
    previous_stats = load_stats()

    library_path = _resolve_library_path(
        args_library_path=args.library_path,
        runtime_config=runtime_config,
        config_loaded=config_loaded,
        settings=settings,
    )
    if not library_path:
        default_library = str(DEFAULT_LIBRARY_DIR) if DEFAULT_LIBRARY_DIR.is_dir() else None
        library_path = prompt_for_library_path(default_library)
    if not library_path:
        print("No library path provided.")
        return 1

    library = Path(library_path)
    try:
        loader = BookLoader(library)
    except FileNotFoundError as exc:
        print(exc)
        return 1

    books = loader.list_books()
    if not books:
        print(f"No books found in {library}.")
        return 1

    try:
        book = choose_book(loader, previous_progress)
        chapter = choose_chapter(loader, book, previous_progress)
    except ValueError as exc:
        print(exc)
        return 1

    render_width = _resolve_render_width(
        args_width=args.width,
        runtime_config=runtime_config,
        config_loaded=config_loaded,
        settings=settings,
    )
    idle_timeout_seconds = _resolve_idle_timeout_seconds(
        args_idle_timeout=args.idle_timeout,
        runtime_config=runtime_config,
        config_loaded=config_loaded,
        settings=settings,
    )
    session_result = run_textual_typing_session(
        library_path=library,
        book_name=book.name,
        chapter_path=chapter,
        width=render_width,
        idle_timeout_seconds=idle_timeout_seconds,
        runtime_config=runtime_config,
    )

    if session_result is None:
        return 0

    updated_settings = dict(settings)
    updated_settings["library_path"] = str(library)
    updated_settings["width"] = render_width
    updated_settings["idle_timeout_seconds"] = idle_timeout_seconds
    updated_settings["last_book"] = book.name
    updated_settings["last_chapter"] = chapter.name
    if config_path is not None:
        updated_settings["config_path"] = str(config_path)

    updated_progress = dict(previous_progress)
    updated_progress.update(session_result["progress"])

    updated_stats = dict(previous_stats)
    updated_stats["last_session"] = session_result["stats"]

    save_settings(updated_settings)
    save_progress(updated_progress)
    save_stats(updated_stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
