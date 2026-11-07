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
            if row['status'] not in ('cart_tested', 'owner_confirmed'):
                self.assertFalse(eligible(row, self.now), row['code'])
        partner = copy.deepcopy(next(r for r in self.records if r['code'] == 'CIOTOLA30'))
        partner['status'] = 'partner_provided'
        partner['publication_allowed'] = True
        self.assertFalse(eligible(partner, self.now))
        for code in ['STY20', 'PP20', 'FD20', 'RELAX', 'BZR20',
                     'SCORTA3', 'SCORTA4', 'SCORTA5', 'RED3', 'RED8', 'WPACO5']:
            candidate = next(r for r in self.records if r['code'] == code)
            self.assertFalse(eligible(candidate, self.now), code)

    def test_owner_confirmed_restoration_is_scoped_and_honest(self):
        row = copy.deepcopy(next(r for r in self.records if r['code'] == 'CIOTOLA30'))
        now = dt.datetime(2026, 11, 7, 12, tzinfo=dt.timezone.utc)
        self.assertTrue(eligible(row, now))
        self.assertNotIn('cart_test', row)
        html = render_card(row)
        self.assertIn('CIOTOLA30', html)
        self.assertIn('Codice concordato con il partner · confermato dal titolare', html)
        self.assertNotIn('Provato nel carrello', html)
        for key, value in [('code', 'OTHER'), ('publication_allowed', False),
                           ('destination_url', 'https://evil.example/'),
                           ('expires_at', '2026-11-07T00:00:00Z')]:
            changed = copy.deepcopy(row)
            changed[key] = value
            self.assertFalse(eligible(changed, now))
        del row['owner_confirmation']
        self.assertFalse(eligible(row, now))


    def test_owner_confirmation_three_states(self):
        row = copy.deepcopy(next(r for r in self.records if r['code'] == 'CIOTOLA30'))
        confirmed = dt.datetime(2026, 11, 20, 23, 59, tzinfo=dt.timezone.utc)
        recheck = dt.datetime(2026, 11, 21, 0, 0, tzinfo=dt.timezone.utc)
        expired = dt.datetime(2028, 1, 1, 0, 0, tzinfo=dt.timezone.utc)

        # 1: published with partner/owner label before the 14-day boundary.
        self.assertTrue(eligible(row, confirmed))
        before = render_card(row, confirmed)
        self.assertIn('Codice concordato con il partner · confermato dal titolare', before)
        self.assertIn('data-recheck-after="2026-11-21T00:00:00Z"', before)
        self.assertNotIn('Provato nel carrello', before)

        # 2: still visible but explicitly awaiting re-confirmation after 14 days.
        self.assertTrue(eligible(row, recheck))
        due = render_card(row, recheck)
        self.assertIn('>Da riconfermare</span>', due)
        self.assertNotIn('confermato dal titolare</span>', due)
        self.assertNotIn('Provato nel carrello', due)

        # 3: excluded at expires_at, not merely marked as needing recheck.
        self.assertFalse(eligible(row, expired))
        self.assertFalse(eligible(row, expired + dt.timedelta(days=1)))

        # A missing/inconsistent recheck date must not publish a confirmation.
        for bad in ('2026-11-22T00:00:00Z', 'invalid'):
            changed = copy.deepcopy(row)
            changed['recheck_after'] = bad
            self.assertFalse(eligible(changed, confirmed))

if __name__ == '__main__':
    unittest.main()
