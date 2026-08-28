import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config import RuntimeConfig, build_textual_css, load_runtime_config, resolve_config_path


class RuntimeConfigTests(unittest.TestCase):
    def test_load_runtime_config_reads_ini_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            conf = Path(tmpdir) / "typing-reader.conf"
            conf.write_text(
                """
[app]
library_path = /books
width = 120
idle_timeout_seconds = 7

[ui]
show_header = false
show_footer = true
screen_align = left top
screen_background = black
content_border = square red
content_padding = 0 1
content_background = navy
content_text = white
status_padding = 2 3
status_background = black
status_text = cyan
tick_interval_seconds = 0.25
title_template = {book} :: {chapter}
choice_marker = *
choice_help_text = Use arrows
choice_title_style = italic
choice_selected_style = reverse bold
choice_help_style = dim
idle_message = Waiting for input
summary_title = Summary
summary_continue_prompt = Continue
summary_title_style = underline
summary_prompt_style = yellow

[styles]
correct = green
incorrect = red
pending = dim
idle = yellow
done = bold white
""".strip(),
                encoding="utf-8",
            )

            config, resolved = load_runtime_config(conf)

            self.assertEqual(resolved, conf)
            self.assertEqual(config.library_path, "/books")
            self.assertEqual(config.width, 120)
            self.assertEqual(config.idle_timeout_seconds, 7.0)
            self.assertFalse(config.show_header)
            self.assertTrue(config.show_footer)
            self.assertEqual(config.screen_align, "left top")
            self.assertEqual(config.screen_background, "black")
            self.assertEqual(config.content_border, "square red")
            self.assertEqual(config.content_padding, "0 1")
            self.assertEqual(config.content_background, "navy")
            self.assertEqual(config.content_text, "white")
            self.assertEqual(config.status_padding, "2 3")
            self.assertEqual(config.status_background, "black")
            self.assertEqual(config.status_text, "cyan")
            self.assertEqual(config.tick_interval_seconds, 0.25)
            self.assertEqual(config.title_template, "{book} :: {chapter}")
            self.assertEqual(config.choice_marker, "*")
            self.assertEqual(config.choice_help_text, "Use arrows")
            self.assertEqual(config.choice_title_style, "italic")
            self.assertEqual(config.choice_selected_style, "reverse bold")
            self.assertEqual(config.choice_help_style, "dim")
            self.assertEqual(config.idle_message, "Waiting for input")
            self.assertEqual(config.summary_title, "Summary")
            self.assertEqual(config.summary_continue_prompt, "Continue")
            self.assertEqual(config.summary_title_style, "underline")
            self.assertEqual(config.summary_prompt_style, "yellow")
            self.assertEqual(config.correct_style, "green")
            self.assertEqual(config.incorrect_style, "red")
            self.assertEqual(config.pending_style, "dim")
            self.assertEqual(config.cursor_style, "reverse bold")
            self.assertEqual(config.idle_style, "yellow")
            self.assertEqual(config.done_style, "bold white")

    def test_load_runtime_config_returns_defaults_when_missing(self) -> None:
        with patch("app.config.resolve_config_path", return_value=None):
            config, resolved = load_runtime_config(Path("does-not-exist.conf"))

        self.assertIsNone(resolved)
        self.assertEqual(config, RuntimeConfig())

    def test_build_textual_css_reflects_layout_settings(self) -> None:
        config = RuntimeConfig(
            show_header=False,
            show_footer=False,
            screen_align="left top",
            screen_background="black",
            content_border="square green",
            content_padding="1 0",
            content_background="navy",
            content_text="white",
            status_padding="0 1",
            status_background="black",
            status_text="cyan",
        )

        css = build_textual_css(config)

        self.assertIn("align: left top;", css)
        self.assertIn("background: black;", css)
        self.assertIn("border: square green;", css)
        self.assertIn("padding: 1 0;", css)
        self.assertIn("background: navy;", css)
        self.assertIn("color: white;", css)
        self.assertIn("padding: 0 1;", css)
        self.assertIn("color: cyan;", css)
        self.assertIn("Header { display: none; }", css)
        self.assertIn("Footer { display: none; }", css)

    def test_resolve_config_path_prefers_explicit_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            conf = Path(tmpdir) / "typing-reader.conf"
            conf.write_text("[app]\nwidth = 90\n", encoding="utf-8")

            resolved = resolve_config_path(conf)

            self.assertEqual(resolved, conf)

    def test_invalid_numeric_values_fall_back_to_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            conf = Path(tmpdir) / "typing-reader.conf"
            conf.write_text(
                """
[app]
width = -10
idle_timeout_seconds = 0

[ui]
tick_interval_seconds = -1
""".strip(),
                encoding="utf-8",
            )

            config, _ = load_runtime_config(conf)

            self.assertEqual(config.width, None)
            self.assertEqual(config.idle_timeout_seconds, 10.0)
            self.assertEqual(config.tick_interval_seconds, 0.1)
            self.assertEqual(config.cursor_style, "reverse bold")


if __name__ == "__main__":
    unittest.main()
