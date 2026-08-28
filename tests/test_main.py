import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import main as app_main
from app.config import RuntimeConfig


class MainTests(unittest.TestCase):
    class FakeKeyReader:
        def __init__(self, keys: list[str | None]) -> None:
            self._keys = list(keys)
            self.read_calls: list[float | None] = []
            self.closed = False

        def read(self, timeout: float | None) -> str | None:
            self.read_calls.append(timeout)
            if self._keys:
                return self._keys.pop(0)
            return None

        def close(self) -> None:
            self.closed = True

    class FakeClock:
        def __init__(self, values: list[float]) -> None:
            self._values = list(values)

        def __call__(self) -> float:
            if not self._values:
                raise AssertionError("fake clock exhausted")
            return self._values.pop(0)

    def test_parse_args_accepts_library_path_and_width(self) -> None:
        args = app_main.parse_args(["C:/books", "--width", "100"])

        self.assertEqual(args.library_path, "C:/books")
        self.assertEqual(args.width, 100)

    def test_choose_preferred_index_finds_matching_item(self) -> None:
        self.assertEqual(app_main.choose_preferred_index(["a", "b", "c"], "b"), 1)
        self.assertIsNone(app_main.choose_preferred_index(["a", "b", "c"], "z"))
        self.assertIsNone(app_main.choose_preferred_index(["a", "b", "c"], None))

    def test_choose_book_and_chapter_use_previous_progress_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "alpha").mkdir()
            (root / "beta").mkdir()
            (root / "alpha" / "one.txt").write_text("a", encoding="utf-8")
            (root / "alpha" / "two.txt").write_text("b", encoding="utf-8")
            (root / "beta" / "only.txt").write_text("c", encoding="utf-8")

            loader = app_main.BookLoader(root)
            previous_progress = {"book": "alpha", "chapter": "two.txt"}

            book = app_main.choose_book(loader, previous_progress)
            chapter = app_main.choose_chapter(loader, book, previous_progress)

            self.assertEqual(book.name, "alpha")
            self.assertEqual(chapter.name, "two.txt")

    def test_config_values_override_saved_settings_when_config_is_loaded(self) -> None:
        runtime_config = RuntimeConfig(
            library_path="config-books",
            width=120,
            idle_timeout_seconds=3.5,
        )
        settings = {
            "library_path": "saved-books",
            "width": 80,
            "idle_timeout_seconds": 9.0,
        }

        self.assertEqual(
            app_main._resolve_library_path(
                args_library_path=None,
                runtime_config=runtime_config,
                config_loaded=True,
                settings=settings,
            ),
            "config-books",
        )
        self.assertEqual(
            app_main._resolve_render_width(
                args_width=None,
                runtime_config=runtime_config,
                config_loaded=True,
                settings=settings,
            ),
            120,
        )
        self.assertEqual(
            app_main._resolve_idle_timeout_seconds(
                args_idle_timeout=None,
                runtime_config=runtime_config,
                config_loaded=True,
                settings=settings,
            ),
            3.5,
        )

    def test_saved_settings_fill_gaps_when_no_config_is_loaded(self) -> None:
        runtime_config = RuntimeConfig()
        settings = {
            "library_path": "saved-books",
            "width": 80,
            "idle_timeout_seconds": 9.0,
        }

        self.assertEqual(
            app_main._resolve_library_path(
                args_library_path=None,
                runtime_config=runtime_config,
                config_loaded=False,
                settings=settings,
            ),
            "saved-books",
        )
        self.assertEqual(
            app_main._resolve_render_width(
                args_width=None,
                runtime_config=runtime_config,
                config_loaded=False,
                settings=settings,
            ),
            80,
        )
        self.assertEqual(
            app_main._resolve_idle_timeout_seconds(
                args_idle_timeout=None,
                runtime_config=runtime_config,
                config_loaded=False,
                settings=settings,
            ),
            9.0,
        )

    def test_run_typing_session_returns_stats_and_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            chapter = Path(tmpdir) / "chapter.txt"
            chapter.write_text("abc", encoding="utf-8")
            key_reader = self.FakeKeyReader(["a", "x", "c"])
            clock = self.FakeClock([0, 1, 2, 3, 4, 5, 6])

            with patch("app.main.clear_screen"), patch("app.main.print"):
                result = app_main.run_typing_session(
                    book_name="demo-book",
                    chapter_path=chapter,
                    width=80,
                    idle_timeout_seconds=10,
                    key_reader=key_reader,
                    clock=clock,
                )

        self.assertEqual(result["progress"]["book"], "demo-book")
        self.assertEqual(result["progress"]["chapter"], "chapter.txt")
        self.assertEqual(result["progress"]["cursor"], 3)
        self.assertTrue(result["progress"]["completed"])
        self.assertEqual(result["stats"]["correct"], 2)
        self.assertEqual(result["stats"]["incorrect"], 1)
        self.assertTrue(result["stats"]["completed"])
        self.assertEqual(result["stats"]["duration_seconds"], 6)
        self.assertEqual(result["stats"]["wall_seconds"], 6)
        self.assertEqual(result["stats"]["idle_seconds"], 0)

    def test_run_typing_session_pauses_wpm_during_idle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            chapter = Path(tmpdir) / "chapter.txt"
            chapter.write_text("abc", encoding="utf-8")
            key_reader = self.FakeKeyReader(["a", None, "x", "c"])
            clock = self.FakeClock([0, 1, 2, 3, 4, 5, 6, 7, 8])

            with patch("app.main.clear_screen"), patch("app.main.print"):
                result = app_main.run_typing_session(
                    book_name="demo-book",
                    chapter_path=chapter,
                    width=80,
                    idle_timeout_seconds=5,
                    key_reader=key_reader,
                    clock=clock,
                )

        self.assertEqual(result["stats"]["duration_seconds"], 4)
        self.assertEqual(result["stats"]["wall_seconds"], 8)
        self.assertEqual(result["stats"]["idle_seconds"], 4)
        self.assertLess(result["stats"]["duration_seconds"], result["stats"]["wall_seconds"])


if __name__ == "__main__":
    unittest.main()
