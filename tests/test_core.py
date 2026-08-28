import tempfile
import unittest
from pathlib import Path

from app.engine import CharState, TypingEngine
from app.layout import TextLayout
from app.loader import BookLoader
from app.reader import Reader


class TypingEngineTests(unittest.TestCase):
    def test_process_key_tracks_correct_and_incorrect_input(self) -> None:
        engine = TypingEngine("abc")

        engine.process_key("a")
        engine.process_key("x")
        engine.process_key("c")

        self.assertEqual(engine.current_index(), 3)
        self.assertTrue(engine.finished())
        self.assertEqual(engine.correct, 2)
        self.assertEqual(engine.incorrect, 1)
        self.assertAlmostEqual(engine.get_accuracy(), 66.66666666666666)
        self.assertEqual(engine.get_state(0), CharState.CORRECT)
        self.assertEqual(engine.get_state(1), CharState.INCORRECT)
        self.assertEqual(engine.get_state(2), CharState.CORRECT)

    def test_backspace_rewinds_state_and_counters(self) -> None:
        engine = TypingEngine("ab")
        engine.process_key("a")
        engine.process_key("x")

        engine.backspace()

        self.assertEqual(engine.current_index(), 1)
        self.assertEqual(engine.correct, 1)
        self.assertEqual(engine.incorrect, 0)
        self.assertEqual(engine.get_state(1), None)
        self.assertEqual(engine.current_character(), "b")

    def test_backspace_at_start_is_safe(self) -> None:
        engine = TypingEngine("a")

        engine.backspace()

        self.assertEqual(engine.current_index(), 0)
        self.assertEqual(engine.correct, 0)
        self.assertEqual(engine.incorrect, 0)

    def test_process_key_ignores_input_after_finish(self) -> None:
        engine = TypingEngine("a")
        engine.process_key("a")

        engine.process_key("z")

        self.assertEqual(engine.current_index(), 1)
        self.assertEqual(engine.correct, 1)
        self.assertEqual(engine.incorrect, 0)


class BookLoaderTests(unittest.TestCase):
    def test_list_books_and_chapters_and_resolve_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "book-b").mkdir()
            (root / "book-a").mkdir()
            (root / "book-a" / "chapter-2.txt").write_text("second", encoding="utf-8")
            (root / "book-a" / "chapter-1.txt").write_text("first", encoding="utf-8")
            (root / "book-a" / "notes.md").write_text("ignore", encoding="utf-8")

            loader = BookLoader(root)

            books = loader.list_books()
            self.assertEqual([p.name for p in books], ["book-a", "book-b"])

            chapters = loader.list_chapters("book-a")
            self.assertEqual([p.name for p in chapters], ["chapter-1.txt", "chapter-2.txt"])

            chapter_path = loader.chapter_path("book-a", "chapter-1.txt")
            self.assertEqual(chapter_path, root / "book-a" / "chapter-1.txt")

    def test_init_rejects_missing_library_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing = Path(tmpdir) / "missing"

            with self.assertRaises(FileNotFoundError):
                BookLoader(missing)


class ReaderTests(unittest.TestCase):
    def test_load_reads_utf8_text_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            chapter = Path(tmpdir) / "chapter.txt"
            chapter.write_text("Hello, world!", encoding="utf-8")

            reader = Reader()

            self.assertEqual(reader.load(chapter), "Hello, world!")


class TextLayoutTests(unittest.TestCase):
    def test_wrap_splits_text_by_width(self) -> None:
        layout = TextLayout()

        lines = layout.wrap("one two three four", width=8)

        self.assertEqual(lines, ["one two", "three", "four"])


if __name__ == "__main__":
    unittest.main()
