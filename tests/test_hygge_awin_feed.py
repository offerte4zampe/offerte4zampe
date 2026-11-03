import csv
import gzip
import tempfile
import unittest
from pathlib import Path
from automation.hygge_awin_feed import import_file

FIELDS = ["advertiser_id", "id", "title", "price", "link", "aw_deep_link", "currency", "availability", "gtin"]
class HyggeAwinTests(unittest.TestCase):
    def fixture(self, rows, zipped=True):
        tmp = tempfile.TemporaryDirectory()
        path = Path(tmp.name) / ("feed.csv.gz" if zipped else "feed.csv")
        opener = gzip.open if zipped else open
        with opener(path, "wt", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        self.addCleanup(tmp.cleanup)
        return path

    def good(self):
        return dict(advertiser_id="121988", id="abc123", title="Crocchette 2kg",
                    price="39.90 EUR", link="https://hyggepetfood.com/products/item",
                    aw_deep_link="https://www.awin1.com/cread.php?awinmid=121988&awinaffid=3126265",
                    currency="", availability="in_stock", gtin="1234567890123")

    def test_valid_gzip(self):
        result = import_file(self.fixture([self.good()]), checked_at="2026-11-03T12:00:00+00:00")
        self.assertEqual(result["offers"][0]["price"], 39.9)
        self.assertEqual(result["offers"][0]["gtin"], "1234567890123")
        self.assertFalse(result["coupon"]["verified"])
        self.assertEqual(result["offers"][0]["weight_kg"], 2.0)

    def test_unknown_stock_rejected(self):
        row = self.good()
        row["availability"] = ""
        with self.assertRaisesRegex(ValueError, "No valid offers"):
            import_file(self.fixture([row]))

    def test_bad_url_rejected(self):
        row = self.good()
        row["link"] = "javascript:alert(1)"
        with self.assertRaisesRegex(ValueError, "No valid offers"):
            import_file(self.fixture([row]))

    def test_duplicate_id_fails_closed(self):
        row = self.good()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            import_file(self.fixture([row, row]))

    def test_wrong_publisher_rejected(self):
        row = self.good()
        row["aw_deep_link"] = row["aw_deep_link"].replace("3126265", "3126256")
        with self.assertRaisesRegex(ValueError, "No valid offers"):
            import_file(self.fixture([row]))

    def test_wrong_currency_rejected(self):
        row = self.good()
        row["currency"] = "GBP"
        with self.assertRaisesRegex(ValueError, "No valid offers"):
            import_file(self.fixture([row]))

if __name__ == "__main__":
    unittest.main()
