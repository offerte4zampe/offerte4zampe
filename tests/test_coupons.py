import copy
import datetime as dt
import json
import unittest
from automation.build_coupon_page import ROOT, eligible, render_card, partner_eligible, render_partner_card


class CouponTests(unittest.TestCase):
    def setUp(self):
        self.row = json.loads((ROOT/'automation/coupons.json').read_text())['coupons'][0]
        self.now = dt.datetime(2026, 10, 29, 20, tzinfo=dt.timezone.utc)

    def test_requires_real_test_permission_and_discount(self):
        self.assertTrue(eligible(self.row, self.now))
        for key, value in [('status','source_only'), ('publication_allowed',False), ('verified_at','2026-10-30T00:00:00Z'), ('code','<script>')]:
            row = copy.deepcopy(self.row); row[key] = value
            self.assertFalse(eligible(row, self.now), key)
        for key,value in [('after_cents',150),('code','OTHER'),('product',''),('currency','USD')]:
            row = copy.deepcopy(self.row); row['cart_test'][key] = value
            self.assertFalse(eligible(row, self.now), key)

    def test_expiry_recheck_and_future_start_are_closed(self):
        for key,value in [('expires_at','2026-10-29T20:00:00Z'),('recheck_after','2026-10-29T20:00:00Z'),('starts_at','2026-10-30T00:00:00Z'),('expires_at','bad')]:
            row = copy.deepcopy(self.row);row[key] = value
            self.assertFalse(eligible(row, self.now),key)
        row = copy.deepcopy(self.row)
        row['expires_at'] = row['recheck_after'] = '2026-12-31T00:00:00Z'
        self.assertFalse(eligible(row, dt.datetime(2026,10,31,tzinfo=dt.timezone.utc)))
        row['source_url']='https://www.bauzaar.it.evil.example/'
        self.assertFalse(eligible(row,self.now))

    def test_public_card_records_scope_dates_and_escapes(self):
        row = copy.deepcopy(self.row);row['title']='<script>alert(1)</script>'
        html = render_card(row)
        self.assertNotIn('<script>',html)
        for expected in ['data-valid-until=', 'Provato nel carrello', '1,50 €', '1,20 €', 'non ogni possibile carrello', 'rel="noopener noreferrer"']:
            self.assertIn(expected,html)


    def test_partner_coupon_is_not_misrepresented_as_cart_tested(self):
        partner = json.loads((ROOT/'automation/coupons.json').read_text())['coupons'][-1]
        now = dt.datetime(2026, 11, 3, 12, tzinfo=dt.timezone.utc)
        self.assertFalse(eligible(partner, now))
        self.assertTrue(partner_eligible(partner, now))
        html = render_partner_card(partner)
        self.assertIn('CIOTOLA30', html)
        self.assertIn('non ancora provato nel carrello', html)
        self.assertNotIn('Provato nel carrello ·', html)
        self.assertFalse(partner_eligible(partner, dt.datetime(2028, 1, 1, tzinfo=dt.timezone.utc)))
        spoofed = copy.deepcopy(partner)
        spoofed['destination_url'] = 'https://hyggepetfood.com.evil.example/'
        self.assertFalse(partner_eligible(spoofed, now))


if __name__ == '__main__':
    unittest.main()
