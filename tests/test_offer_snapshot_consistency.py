"""Fail publication when home and canonical detail show different offer snapshots."""
import gzip
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "site" / "data"


class OfferSnapshotConsistency(unittest.TestCase):
    def test_offer_dates_match_across_published_snapshots(self):
        catalog = json.loads(gzip.decompress((DATA / "catalog.json.gz").read_bytes()))
        expected = {o["id"]: o.get("checked_at") for o in catalog["offers"]}
        self.assertEqual(len(expected), len(catalog["offers"]), "Duplicate offer IDs in catalog")
        home = json.loads((DATA / "home.json").read_text())
        self.assertEqual(home["generated_at"], catalog["generated_at"])
        for offer in home["offers"]:
            with self.subTest(surface="home", offer=offer["id"]):
                self.assertIn(offer["id"], expected)
                self.assertEqual(offer.get("checked_at"), expected[offer["id"]])
        found = set()
        for shard in sorted((DATA / "canonical-products").glob("*.json")):
            products = json.loads(shard.read_text())
            for product in products.values():
                for offer in product.get("offers", []):
                    with self.subTest(surface="product", offer=offer["id"]):
                        self.assertIn(offer["id"], expected)
                        self.assertEqual(offer.get("checked_at"), expected[offer["id"]])
                        found.add(offer["id"])
        self.assertTrue(found, "No canonical offer snapshots found")
        for offer in home["offers"]:
            self.assertIn(offer["id"], found, "Home offer missing from canonical detail snapshot")


if __name__ == "__main__":
    unittest.main()
