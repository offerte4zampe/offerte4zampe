import copy
import datetime as dt
import json
import unittest
from automation.build_coupon_page import ROOT, eligible, render_card, visit_link


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
        self.assertIn('Verifica confermata dal titolare', html)
        self.assertNotIn('Provato nel carrello', html)
        for key, value in [('code', 'OTHER'), ('publication_allowed', False),
                           ('destination_url', 'https://evil.example/'),
                           ('expires_at', '2026-11-07T00:00:00Z')]:
            changed = copy.deepcopy(row)
            changed[key] = value
            self.assertFalse(eligible(changed, now))
        del row['owner_confirmation']
        self.assertFalse(eligible(row, now))

    def test_official_affiliate_link_is_preserved_and_disclosed(self):
        row = copy.deepcopy(next(r for r in self.records if r['code'] == 'CIOTOLA30'))
        url, rel = visit_link(row)
        self.assertEqual(url, row['affiliate_url'])
        self.assertEqual(rel, 'sponsored nofollow noopener noreferrer')
        html = render_card(row)
        self.assertIn('awinaffid=3126265', html)
        self.assertIn('rel="sponsored nofollow noopener noreferrer"', html)
        self.assertIn('CIOTOLA30', html)
        self.assertEqual(visit_link(self.row), (self.row['destination_url'], 'noopener noreferrer'))

    def test_affiliate_link_rejects_wrong_publisher_merchant_destination(self):
        row = copy.deepcopy(next(r for r in self.records if r['code'] == 'CIOTOLA30'))
        good = row['affiliate_url']
        for bad in [good.replace('3126265', '3126256'), good.replace('121988', '999'),
                    good.replace('www.awin1.com', 'www.awin1.com.evil.test'),
                    good + '&awinaffid=3126256', good.replace('hyggepetfood.com', 'evil.test'),
                    good.replace('https://', 'http://', 1), good + '#fragment', good + '\n']:
            row['affiliate_url'] = bad
            with self.assertRaises(ValueError, msg=bad):
                render_card(row)


if __name__ == '__main__':
    unittest.main()
