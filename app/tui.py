from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.screen import ModalScreen, Screen
from textual.widgets import Footer, Header, Static

from app.config import RuntimeConfig, build_textual_css
from app.engine import CharState, TypingEngine
from app.loader import BookLoader
from app.reader import Reader
from app.stats import build_session_stats


def build_target_text(target: str, engine: TypingEngine, config: RuntimeConfig) -> Text:
    text = Text()
    for index, character in enumerate(target):
        state = engine.get_state(index)
        if state == CharState.CORRECT:
            style = config.correct_style
        elif state == CharState.INCORRECT:
            style = config.incorrect_style
        else:
            style = config.pending_style
        if index == engine.current_index() and not engine.finished():
            style = f"{style} {config.cursor_style}".strip()
        text.append(character, style=style)
    return text


def build_status_text(
    *,
    title: str,
    engine: TypingEngine,
    idle: bool,
    config: RuntimeConfig,
) -> Text:
    status = Text()
    status.append(title, style="bold")
    status.append("\n")
    status.append(
        f"Progress: {engine.current_index()}/{len(engine.target)}  "
        f"Accuracy: {engine.get_accuracy():.1f}%"
    )
    if idle:
        status.append("\n")
        status.append(config.idle_message, style=config.idle_style)
    if engine.finished():
        status.append("\n")
        status.append("Done", style=config.done_style)
    return status


def build_choice_text(
    title: str,
    items: list[str],
    selected_index: int,
    *,
    config: RuntimeConfig,
    marker: str = ">",
) -> Text:
    text = Text()
    text.append(title, style=config.choice_title_style)
    text.append("\n")
    for index, item in enumerate(items):
        prefix = marker if index == selected_index else " "
        if index == selected_index:
            text.append(f"{prefix} {item}\n", style=config.choice_selected_style)
        else:
            text.append(f"{prefix} {item}\n")
    return text


def build_summary_text(result: dict[str, object], config: RuntimeConfig) -> Text:
    stats = result["stats"]
    progress = result["progress"]
    text = Text()
    text.append(config.summary_title, style=config.summary_title_style)
    text.append("\n\n")
    text.append(f"Book: {progress['book']}\n")
    text.append(f"Chapter: {progress['chapter']}\n")
    text.append(f"Completed: {'yes' if progress['completed'] else 'no'}\n")
    text.append(f"Characters typed: {stats['typed_length']}\n")
    text.append(f"Accuracy: {stats['accuracy']:.1f}%\n")
    text.append(f"WPM: {stats['words_per_minute']:.1f}\n")
    text.append("\n")
    text.append(config.summary_continue_prompt, style=config.summary_prompt_style)
    return text


def _safe_title(template: str, book_name: str, chapter_name: str) -> str:
    try:
        return template.format(book=book_name, chapter=chapter_name)
    except Exception:
        return f"{book_name} / {chapter_name}"


class ChoiceScreen(ModalScreen[str | None]):
    BINDINGS = [("escape", "cancel", "Back"), ("q", "quit", "Quit"), ("ctrl+c", "quit", "Quit")]

    def __init__(
        self,
        *,
        title: str,
        prompt: str,
        items: list[str],
        runtime_config: RuntimeConfig,
        initial_index: int = 0,
    ) -> None:
        super().__init__()
        self.choice_title = title
        self.choice_prompt = prompt
        self.items = items
        self.runtime_config = runtime_config
        self.selected_index = max(0, min(initial_index, max(len(items) - 1, 0)))
        self._content: Static | None = None
        self._status: Static | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="content")
        yield Static(id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.title = self.choice_title
        self._content = self.query_one("#content", Static)
        self._status = self.query_one("#status", Static)
        self._refresh()

    def _refresh(self) -> None:
        if self._content is not None:
            self._content.update(
                build_choice_text(
                    self.choice_title,
                    self.items,
                    self.selected_index,
                    config=self.runtime_config,
                    marker=self.runtime_config.choice_marker,
                )
            )
        if self._status is not None:
            self._status.update(
                Text.assemble(
                    (self.choice_prompt, self.runtime_config.choice_title_style),
                    "\n",
                    (self.runtime_config.choice_help_text, self.runtime_config.choice_help_style),
                )
            )

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_quit(self) -> None:
        self.dismiss("quit")

    def on_key(self, event: events.Key) -> None:
        if not self.items:
            self.dismiss(None)
            return

        if event.key == "up":
            self.selected_index = max(0, self.selected_index - 1)
            self._refresh()
        elif event.key == "down":
            self.selected_index = min(len(self.items) - 1, self.selected_index + 1)
            self._refresh()
        elif event.key == "home":
            self.selected_index = 0
            self._refresh()
        elif event.key == "end":
            self.selected_index = len(self.items) - 1
            self._refresh()
        elif event.key == "enter":
            self.dismiss(self.items[self.selected_index])


class BookSelectScreen(ChoiceScreen):
    def __init__(self, book_names: list[str], runtime_config: RuntimeConfig, initial_index: int = 0) -> None:
        super().__init__(
            title="Books",
            prompt="Choose a book",
            items=book_names,
            runtime_config=runtime_config,
            initial_index=initial_index,
        )


class ChapterSelectScreen(ChoiceScreen):
    def __init__(
        self,
        book_name: str,
        chapter_names: list[str],
        runtime_config: RuntimeConfig,
        initial_index: int = 0,
    ) -> None:
        super().__init__(
            title=f"Chapters - {book_name}",
            prompt="Choose a chapter",
            items=chapter_names,
            runtime_config=runtime_config,
            initial_index=initial_index,
        )


class SummaryScreen(ModalScreen[str | None]):
    BINDINGS = [("escape", "quit", "Quit"), ("q", "quit", "Quit"), ("ctrl+c", "quit", "Quit")]

    def __init__(self, result: dict[str, object], runtime_config: RuntimeConfig) -> None:
        super().__init__()
        self.result = result
        self.runtime_config = runtime_config
        self._content: Static | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="content")
        yield Footer()

    def on_mount(self) -> None:
        self.title = self.runtime_config.summary_title
        self._content = self.query_one("#content", Static)
        self._content.update(build_summary_text(self.result, self.runtime_config))

    def on_key(self, event: events.Key) -> None:
        if event.key in {"escape", "q", "ctrl+c"}:
            self.dismiss("quit")
        else:
            self.dismiss("restart")

    def action_quit(self) -> None:
        self.dismiss("quit")


class TypingSessionScreen(Screen[dict[str, object]]):
    BINDINGS = [("ctrl+c", "finish", "Finish"), ("escape", "finish", "Finish"), ("q", "finish", "Finish")]

    def __init__(
        self,
        *,
        book_name: str,
        chapter_path: Path,
        width: int,
        idle_timeout_seconds: float,
        runtime_config: RuntimeConfig,
    ) -> None:
        super().__init__()
        self.book_name = book_name
        self.chapter_path = chapter_path
        self.render_width = width
        self.idle_timeout_seconds = idle_timeout_seconds
        self.runtime_config = runtime_config
        self.reader = Reader()
        self.target = self.reader.load(chapter_path)
        self.engine = TypingEngine(self.target)
        self.wall_started_at = perf_counter()
        self.active_started_at = self.wall_started_at
        self.active_seconds = 0.0
        self.last_activity_at = self.wall_started_at
        self.idle = False
        self._content: Static | None = None
        self._status: Static | None = None

    def compose(self) -> ComposeResult:
        if self.runtime_config.show_header:
            yield Header()
        yield Static(id="content")
        yield Static(id="status")
        if self.runtime_config.show_footer:
            yield Footer()

    def on_mount(self) -> None:
        self.title = _safe_title(
            self.runtime_config.title_template,
            self.book_name,
            self.chapter_path.name,
        )
        self._content = self.query_one("#content", Static)
        self._status = self.query_one("#status", Static)
        self.set_interval(self.runtime_config.tick_interval_seconds, self._tick)
        if self._content is not None:
            self._content.styles.width = self.render_width
        self._refresh_view(perf_counter())

    def _active_elapsed(self, now: float) -> float:
        if self.idle:
            return self.active_seconds
        return self.active_seconds + max(0.0, now - self.active_started_at)

    def _wall_elapsed(self, now: float) -> float:
        return max(0.0, now - self.wall_started_at)

    def _refresh_view(self, now: float) -> None:
        if self._content is not None:
            self._content.update(build_target_text(self.target, self.engine, self.runtime_config))
        if self._status is not None:
            self._status.update(
                build_status_text(
                    title=_safe_title(
                        self.runtime_config.title_template,
                        self.book_name,
                        self.chapter_path.name,
                    ),
                    engine=self.engine,
                    idle=self.idle,
                    config=self.runtime_config,
                )
            )

    def _set_idle(self, now: float) -> None:
        if not self.idle:
            self.active_seconds += max(0.0, now - self.active_started_at)
            self.active_started_at = now
            self.idle = True

    def _resume(self, now: float) -> None:
        self.last_activity_at = now
        if self.idle:
            self.idle = False
            self.active_started_at = now

    def _finalize_result(self, now: float) -> dict[str, object]:
        if not self.idle:
            self.active_seconds += max(0.0, now - self.active_started_at)
            self.active_started_at = now
        stats = build_session_stats(
            self.target,
            self.engine,
            self.active_seconds,
            wall_seconds=self._wall_elapsed(now),
        )
        progress = {
            "book": self.book_name,
            "chapter": self.chapter_path.name,
            "cursor": self.engine.current_index(),
            "completed": self.engine.finished(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "total_chars": len(self.target),
        }
        return {
            "stats": stats.to_dict(),
            "progress": progress,
        }

    def _tick(self) -> None:
        now = perf_counter()
        if not self.engine.finished() and not self.idle:
            if now - self.last_activity_at >= self.idle_timeout_seconds:
                self._set_idle(now)
        self._refresh_view(now)

    def action_finish(self) -> None:
        self.dismiss(self._finalize_result(perf_counter()))

    def on_key(self, event: events.Key) -> None:
        now = perf_counter()
        if self.idle:
            self._resume(now)

        self.last_activity_at = now

        if event.key == "backspace":
            self.engine.backspace()
        elif event.key == "enter":
            self.engine.process_key("\n")
        elif event.character:
            self.engine.process_key(event.character)
        else:
            return

        self._refresh_view(now)
        if self.engine.finished():
            self.dismiss(self._finalize_result(now))


def make_typing_trainer_app(runtime_config: RuntimeConfig) -> type[App[dict[str, object]]]:
    css = build_textual_css(runtime_config)

    class TypingTrainerApp(App[dict[str, object]]):
        CSS = css
        BINDINGS = [("q", "quit_app", "Quit"), ("ctrl+c", "quit_app", "Quit")]

        def __init__(
            self,
            *,
            loader: BookLoader,
            previous_progress: dict[str, object],
            width: int,
            idle_timeout_seconds: float,
        ) -> None:
            super().__init__()
            self.loader = loader
            self.previous_progress = previous_progress
            self.render_width = width
            self.idle_timeout_seconds = idle_timeout_seconds
            self.runtime_config = runtime_config
            self.book_name: str | None = None
            self.chapter_name: str | None = None
            self._last_result: dict[str, object] | None = None

        def on_mount(self) -> None:
            self._show_book_screen()

        def _book_index(self) -> int:
            books = [book.name for book in self.loader.list_books()]
            preferred = self.previous_progress.get("book")
            if preferred in books:
                return books.index(str(preferred))
            return 0

        def _chapter_index(self, book_name: str) -> int:
            chapters = [chapter.name for chapter in self.loader.list_chapters(book_name)]
            preferred = self.previous_progress.get("chapter")
            if preferred in chapters:
                return chapters.index(str(preferred))
            return 0

        def _show_book_screen(self) -> None:
            book_names = [book.name for book in self.loader.list_books()]
            self.push_screen(
                BookSelectScreen(
                    book_names,
                    runtime_config=self.runtime_config,
                    initial_index=self._book_index(),
                ),
                self._on_book_selected,
            )

        def _on_book_selected(self, book_name: str | None) -> None:
            if book_name is None or book_name == "quit":
                self.exit(self._last_result)
                return
            self.book_name = book_name
            chapter_names = [chapter.name for chapter in self.loader.list_chapters(book_name)]
            self.push_screen(
                ChapterSelectScreen(
                    book_name,
                    chapter_names,
                    runtime_config=self.runtime_config,
                    initial_index=self._chapter_index(book_name),
                ),
                self._on_chapter_selected,
            )

        def _on_chapter_selected(self, chapter_name: str | None) -> None:
            if chapter_name is None:
                self._show_book_screen()
                return
            if chapter_name == "quit":
                self.exit(self._last_result)
                return
            self.chapter_name = chapter_name
            chapter_path = self.loader.chapter_path(self.book_name or "", chapter_name)
            self.push_screen(
                TypingSessionScreen(
                    book_name=self.book_name or "",
                    chapter_path=chapter_path,
                    width=self.render_width,
                    idle_timeout_seconds=self.idle_timeout_seconds,
                    runtime_config=self.runtime_config,
                ),
                self._on_session_finished,
            )

        def _on_session_finished(self, result: dict[str, object] | None) -> None:
            if result is None:
                self._show_book_screen()
                return
            self._last_result = result
            self.push_screen(
                SummaryScreen(result, runtime_config=self.runtime_config),
                self._on_summary_finished,
            )

        def _on_summary_finished(self, result: str | None) -> None:
            if result == "restart":
                self._show_book_screen()
                return
            self.exit(self._last_result)

        def action_quit_app(self) -> None:
            self.exit(self._last_result)

    return TypingTrainerApp


def run_textual_session(
    *,
    library_path: Path,
    book_name: str,
    chapter_path: Path,
    width: int,
    idle_timeout_seconds: float,
    runtime_config: RuntimeConfig,
) -> dict[str, object] | None:
    app_class = make_typing_trainer_app(runtime_config)
    loader = BookLoader(library_path)
    app = app_class(
        loader=loader,
        previous_progress={"book": book_name, "chapter": chapter_path.name},
        width=width,
        idle_timeout_seconds=idle_timeout_seconds,
    )
    result = app.run()
    return result
