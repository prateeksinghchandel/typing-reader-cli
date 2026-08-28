import unittest

from app.engine import TypingEngine
from app.stats import SessionStats, build_session_stats, calculate_wpm


class StatsTests(unittest.TestCase):
    def test_calculate_wpm_uses_standard_five_characters_per_word_formula(self) -> None:
        self.assertEqual(calculate_wpm(0, 12), 0.0)
        self.assertEqual(calculate_wpm(10, 0), 0.0)
        self.assertAlmostEqual(calculate_wpm(250, 60), 50.0)

    def test_build_session_stats_reflects_engine_state(self) -> None:
        engine = TypingEngine("abc")
        engine.process_key("a")
        engine.process_key("x")
        engine.process_key("c")

        stats = build_session_stats("abc", engine, active_seconds=30, wall_seconds=42)

        self.assertIsInstance(stats, SessionStats)
        self.assertEqual(stats.target_length, 3)
        self.assertEqual(stats.typed_length, 3)
        self.assertEqual(stats.correct, 2)
        self.assertEqual(stats.incorrect, 1)
        self.assertTrue(stats.completed)
        self.assertAlmostEqual(stats.accuracy, 66.66666666666666)
        self.assertAlmostEqual(stats.words_per_minute, 1.2)
        self.assertEqual(stats.duration_seconds, 30)
        self.assertEqual(stats.wall_seconds, 42)
        self.assertEqual(stats.idle_seconds, 12)

    def test_session_stats_can_be_serialized_to_dict(self) -> None:
        engine = TypingEngine("ab")
        engine.process_key("a")

        stats = build_session_stats("ab", engine, active_seconds=15, wall_seconds=20)
        payload = stats.to_dict()

        self.assertEqual(payload["target_length"], 2)
        self.assertEqual(payload["typed_length"], 1)
        self.assertEqual(payload["correct"], 1)
        self.assertEqual(payload["incorrect"], 0)
        self.assertFalse(payload["completed"])
        self.assertEqual(payload["duration_seconds"], 15)
        self.assertEqual(payload["wall_seconds"], 20)
        self.assertEqual(payload["idle_seconds"], 5)


if __name__ == "__main__":
    unittest.main()
