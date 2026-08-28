import tempfile
import unittest
from pathlib import Path

from app.storage import (
    load_progress,
    load_settings,
    load_stats,
    save_progress,
    save_settings,
    save_stats,
)


class StorageTests(unittest.TestCase):
    def test_load_helpers_return_empty_dict_for_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            self.assertEqual(load_settings(root / "settings.json"), {})
            self.assertEqual(load_progress(root / "progress.json"), {})
            self.assertEqual(load_stats(root / "stats.json"), {})

    def test_load_helpers_return_empty_dict_for_empty_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            settings = root / "settings.json"
            progress = root / "progress.json"
            stats = root / "stats.json"
            settings.write_text("", encoding="utf-8")
            progress.write_text("   ", encoding="utf-8")
            stats.write_text("\n", encoding="utf-8")

            self.assertEqual(load_settings(settings), {})
            self.assertEqual(load_progress(progress), {})
            self.assertEqual(load_stats(stats), {})

    def test_save_and_load_round_trip_for_all_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            settings_path = root / "config" / "settings.json"
            progress_path = root / "state" / "progress.json"
            stats_path = root / "stats.json"

            settings_payload = {"library_path": "books", "width": 80}
            progress_payload = {"book": "demo", "chapter": "intro.txt", "cursor": 12}
            stats_payload = {"sessions": 4, "accuracy": 98.2}

            save_settings(settings_payload, settings_path)
            save_progress(progress_payload, progress_path)
            save_stats(stats_payload, stats_path)

            self.assertEqual(load_settings(settings_path), settings_payload)
            self.assertEqual(load_progress(progress_path), progress_payload)
            self.assertEqual(load_stats(stats_path), stats_payload)

    def test_load_helpers_ignore_non_object_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            settings = root / "settings.json"
            settings.write_text('["not", "a", "dict"]', encoding="utf-8")

            self.assertEqual(load_settings(settings), {})


if __name__ == "__main__":
    unittest.main()
