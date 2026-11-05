import datetime as dt
import unittest
from automation.merchant_promotions import annotate,with_reference,info,render
class MerchantPromotionTests(unittest.TestCase):
    def setUp(self):
        self.now=dt.datetime(2026,11,5,12,tzinfo=dt.timezone.utc)
        self.row=dict(id='webpet:123',merchant_id='webpet',price=8,previous_price=10,available=True,url='https://webpet.it/products/food?variant=123',checked_at=self.now.isoformat())
    def test_exact_variant_reference_and_money_are_distinct_from_history(self):
        o=annotate(self.row);p=info(o,self.now)
        self.assertEqual(p,dict(reference_cents=1000,saved_cents=200,percent=20))
        self.assertIn('Rif. negozio <s>10,00 €</s>',render(o,self.now))
        self.assertNotIn('Prima',render(o,self.now));self.assertNotIn('merchant_promotion',self.row)
    def test_changed_price_offer_source_date_and_stale_or_unknown_pack_reject(self):
        o=annotate(self.row)
        for change in [dict(price=7),dict(id='other'),dict(url='https://webpet.it/products/other'),dict(checked_at='2026-11-04T12:00:00Z'),dict(quantity_verified=False),dict(available=False),dict(weight_conflict=True)]:
            self.assertIsNone(info(dict(o,**change),self.now))
        self.assertIsNone(info(o,self.now+dt.timedelta(hours=13)))
    def test_no_reference_guessed_from_other_shops_or_ambiguous_variant(self):
        for change in [dict(previous_price=None),dict(previous_price=7),dict(url='https://webpet.it/products/food?variant=456'),dict(source_type='official_feed'),dict(merchant_id='unknown')]:
            self.assertNotIn('merchant_promotion',annotate(dict(self.row,**change)))
    def test_feed_promotion_expires_without_changing_current_price(self):
        o=with_reference(self.row,10,'feed_regular_price',(self.now+dt.timedelta(hours=1)).isoformat())
        self.assertIsNotNone(info(o,self.now));self.assertIsNone(info(o,self.now+dt.timedelta(hours=2)))
        self.assertEqual(o['price'],8)
    def test_percentage_is_not_rounded_up(self):
        o=with_reference(dict(self.row,price=9),11,'shopify_compare_at')
        self.assertEqual(info(o,self.now)['percent'],18.1)
