import unittest

from app.engine import TypingEngine
from app.ui import render_idle_session, render_menu, render_message, render_session


class UiTests(unittest.TestCase):
    def test_render_menu_lists_items(self) -> None:
        output = render_menu("Books", ["alpha", "beta"])

        self.assertIn("Books", output)
        self.assertIn("1. alpha", output)
        self.assertIn("2. beta", output)

    def test_render_session_includes_progress_and_colored_state(self) -> None:
        engine = TypingEngine("ab")
        engine.process_key("a")
        engine.process_key("x")

        output = render_session(
            title="Demo",
            target="ab",
            engine=engine,
            elapsed_seconds=12.5,
            width=40,
        )

        self.assertIn("Demo", output)
        self.assertIn("Progress", output)
        self.assertIn("Accuracy", output)
        self.assertIn("Elapsed", output)
        self.assertIn("\033[32ma\033[0m", output)
        self.assertIn("\033[31mb\033[0m", output)

    def test_render_idle_session_includes_pause_message(self) -> None:
        engine = TypingEngine("ab")
        engine.process_key("a")

        output = render_idle_session(
            title="Demo",
            target="ab",
            engine=engine,
            active_seconds=9.5,
            wall_seconds=14.5,
            idle_timeout_seconds=5,
            width=40,
        )

        self.assertIn("Idle", output)
        self.assertIn("WPM is paused", output)
        self.assertIn("Wall time", output)

    def test_render_message_returns_plain_text(self) -> None:
        self.assertEqual(render_message("hello"), "hello")


if __name__ == "__main__":
    unittest.main()
