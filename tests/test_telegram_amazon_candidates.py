import datetime as dt
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "telegram_amazon_candidates", ROOT / "automation/build_telegram_amazon_candidates.py"
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class TelegramAmazonCandidateTests(unittest.TestCase):
    def test_deduplicates_and_never_auto_approves(self):
        row = {"asin":"B0002AR15U", "title":"Kong Classic Small - gioco per cani",
               "checked_at":"2026-11-07"}
        out = mod.candidates({"links":[row,row]}, dt.date(2026,11,8))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["source_match_count"], 2)
        self.assertIsNone(out[0]["reviewed_at"])
        self.assertIsNone(out[0]["note"])
        self.assertIsNone(out[0]["image"])
        self.assertFalse(out[0]["rights_confirmed"])
        self.assertFalse(out[0]["editorial_reviewed"])
        self.assertFalse(out[0]["publication_ready"])

    def test_filters_stale_invalid_and_sensitive(self):
        entries = [
            {"asin":"B0002AR15U","title":"Kong Classic Small - gioco per cani","checked_at":"2026-10-01"},
            {"asin":"BAD","title":"Kong Classic Small - gioco per cani","checked_at":"2026-11-07"},
            {"asin":"B0722X975H","title":"Collare calmante per gatti","checked_at":"2026-11-07"},
            {"asin":"B0002AR0I8","title":"Kong Classic Large per cani","checked_at":"2026-11-07"},
        ]
        out = mod.candidates({"links":entries},dt.date(2026,11,8))
        self.assertEqual([r["asin"] for r in out], ["B0002AR0I8"])


if __name__ == "__main__":
    unittest.main()
