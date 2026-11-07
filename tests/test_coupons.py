import copy
import datetime as dt
import json
import unittest
from automation.build_coupon_page import ROOT, eligible, render_card


class CouponTests(unittest.TestCase):
    def setUp(self):
        records = json.loads((ROOT/'automation/coupons.json').read_text())['coupons']
        self.records = records
        self.row = copy.deepcopy(next(r for r in records if r['code'] == 'MP20'))
        self.now = dt.datetime(2026, 11, 6, 12, tzinfo=dt.timezone.utc)

    def test_requires_real_test_permission_and_discount(self):
        self.assertTrue(eligible(self.row, self.now))
        for key, value in [('status', 'source_only'), ('publication_allowed', False),
                           ('verified_at', '2026-11-07T00:00:00Z'), ('code', '<script>')]:
            row = copy.deepcopy(self.row)
            row[key] = value
            self.assertFalse(eligible(row, self.now), key)
        for key, value in [('after_cents', 600), ('code', 'OTHER'), ('product', ''),
                           ('currency', 'USD')]:
            row = copy.deepcopy(self.row)
            row['cart_test'][key] = value
            self.assertFalse(eligible(row, self.now), key)

    def test_expiry_recheck_and_48_hour_limit_are_closed(self):
        for key, value in [('expires_at', '2026-11-06T12:00:00Z'),
                           ('recheck_after', '2026-11-06T12:00:00Z'),
                           ('starts_at', '2026-11-07T00:00:00Z'), ('expires_at', 'bad')]:
            row = copy.deepcopy(self.row)
            row[key] = value
            self.assertFalse(eligible(row, self.now), key)
        row = copy.deepcopy(self.row)
        row['expires_at'] = row['recheck_after'] = '2026-12-31T00:00:00Z'
        boundary = dt.datetime(2026, 11, 8, 0, tzinfo=dt.timezone.utc)
        self.assertFalse(eligible(row, boundary))
        row['source_url'] = 'https://www.bauzaar.it.evil.example/'
        self.assertFalse(eligible(row, self.now))

    def test_public_card_records_scope_dates_and_escapes(self):
        row = copy.deepcopy(self.row)
        row['title'] = '<script>alert(1)</script>'
        html = render_card(row)
        self.assertNotIn('<script>', html)
        for expected in ['data-valid-until=', 'Provato nel carrello', '6,00 €', '4,80 €',
                         'non ogni possibile carrello', 'rel="noopener noreferrer"']:
            self.assertIn(expected, html)

    def test_only_cart_tested_codes_can_be_published(self):
        for row in self.records:
            if row['status'] != 'cart_tested':
                self.assertFalse(eligible(row, self.now), row['code'])
        partner = copy.deepcopy(next(r for r in self.records if r['code'] == 'CIOTOLA30'))
        partner['publication_allowed'] = True
        self.assertFalse(eligible(partner, self.now))
        for code in ['STY20', 'PP20', 'FD20', 'RELAX', 'BZR20',
                     'SCORTA3', 'SCORTA4', 'SCORTA5', 'RED3', 'RED8', 'WPACO5']:
            candidate = next(r for r in self.records if r['code'] == code)
            self.assertFalse(eligible(candidate, self.now), code)


if __name__ == '__main__':
    unittest.main()
