"""Regression tests for the ELYSY ASS converter (standard library only)."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from elysy_to_karaoke_ass import (  # noqa: E402
    PROFILES, Word, ass_time, group_srt, karaoke_words,
    make_ass, parse_json, parse_srt,
)


class ConverterTests(unittest.TestCase):
    def test_fixture_srt(self):
        path = ROOT / "tests" / "fixtures" / "sample_enhanced.srt"
        words = parse_srt(path)
        self.assertEqual([w.text for w in words],
                         ["Six", "young", "friends,", "one", "summer", "ride."])
        self.assertAlmostEqual(words[0].start, 1.0)
        self.assertAlmostEqual(words[-1].end, 3.4)
        groups = group_srt(words, 7, 4.0, .65, 40)
        self.assertEqual(len(groups), 1)
        self.assertIn(r"{\kf43}Six", karaoke_words(groups[0]))
        self.assertIn("ride.", karaoke_words(groups[0]))

    def test_json_lines(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "aligned.json"
            path.write_text(json.dumps([
                {"line": "Look ahead", "words": [
                    {"word": "Look", "start": 2.0, "end": 2.2},
                    {"word": "ahead", "start": 2.25, "end": 2.8},
                ]},
                {"line": "Come home", "words": [
                    {"word": "Come", "start": 3.0, "end": 3.3},
                    {"word": "home", "start": 3.4, "end": 3.8},
                ]},
            ]), encoding="utf-8")
            groups = parse_json(path)
            self.assertEqual(len(groups), 2)
            self.assertEqual(groups[-1][-1].text, "home")

    def test_all_profiles(self):
        groups = [[Word("Maybe", 1.0, 1.5), Word("home", 1.6, 2.0)]]
        for profile, (width, height, margin, _) in PROFILES.items():
            with self.subTest(profile=profile):
                position = "right" if profile == "wide" else "center"
                content = make_ass(groups, profile, "Arial", 0, margin, .25, position)
                self.assertIn(f"PlayResX: {width}", content)
                self.assertIn(f"PlayResY: {height}", content)
                self.assertIn(r"{\kf50}Maybe", content)
                self.assertIn("Dialogue:", content)

    def test_offset(self):
        content = make_ass(
            [[Word("Now", 1.0, 1.5)]], "wide", "Arial", 4.8, 90, .25, "right")
        self.assertIn("Dialogue: 0,0:00:05.80,", content)

    def test_timestamp(self):
        self.assertEqual(ass_time(61.23), "0:01:01.23")

    def test_cli(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "reels.ass"
            result = subprocess.run(
                [sys.executable, str(ROOT / "elysy_to_karaoke_ass.py"),
                 str(ROOT / "tests" / "fixtures" / "sample_enhanced.srt"),
                 "--profile", "instagram-reels", "--output", str(output)],
                capture_output=True, text=True, check=True)
            self.assertIn("instagram-reels", result.stdout)
            self.assertIn("PlayResX: 1080", output.read_text(encoding="utf-8-sig"))
            self.assertIn("Dialogue:", output.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    unittest.main()
