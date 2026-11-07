"""Negative golden-sample evidence tests, no fake reviewer approvals."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from golden_acceptance import check


class GoldenAcceptanceTests(unittest.TestCase):
    def test_unfinished_sample_must_fail(self):
        problems = check(ROOT / "examples" / "focus-notification-v31")
        self.assertTrue(any("still awaiting" in p for p in problems))
        self.assertTrue(any("independent final" in p for p in problems))
        self.assertTrue(any("actual_mp4" in p for p in problems))

    def test_path_escape_and_fake_release_are_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "acceptance.json").write_text(json.dumps({
                "status": "RELEASE_APPROVED", "release_approved": True,
                "actual_mp4": "../not-a-movie.mp4",
                "actual_mp4_sha256": "incorrect",
                "real_voice_review": "voice.json",
                "actual_human_review": "review.json",
            }), encoding="utf-8")
            problems = check(root)
            self.assertTrue(any("MP4 must exist inside" in p for p in problems))
            self.assertTrue(any("missing real voice" in p for p in problems))
            self.assertTrue(any("missing human" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
