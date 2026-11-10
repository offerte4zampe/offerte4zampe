import datetime
import os
from unittest.mock import patch
import unittest
from automation.build_home_data import build


class HomeDataTests(unittest.TestCase):
    def test_small_payload_keeps_current_prices_without_using_reference_discount(self):
        now = datetime.datetime(2026, 10, 19, tzinfo=datetime.timezone.utc)
        base = dict(id='ok', merchant_id='shop', merchant='Shop', brand='Brand', title='Food', price=10, previous_price=20, image='https://example.com/a.jpg', url='https://example.com/product', available=True, checked_at=now.isoformat())
        offers = [base, base | dict(id='stale', checked_at='2026-10-16T00:00:00+00:00'), base | dict(id='suspicious', previous_price=100), base | dict(id='out', available=False)]
        result = build(dict(offers=offers, sources=[dict(id='shop')], generated_at=now.isoformat(), refresh_hours=6), now)
        self.assertEqual(len(result['offers']), 1)
        self.assertIn(result['offers'][0]['id'], ('ok', 'suspicious'))
        self.assertEqual(result['offers'][0]['price'], 10)
        self.assertEqual(result['stats']['offers'], 4)
        self.assertNotIn('affiliate_url', result['offers'][0])
        self.assertNotIn('previous_price', result['offers'][0])
        without_reference = build(dict(offers=[base | dict(previous_price=None)], sources=[dict(id='shop')], generated_at=now.isoformat(), refresh_hours=6), now)
        self.assertEqual(without_reference['offers'][0]['price'], result['offers'][0]['price'])
        self.assertNotIn('verified_discount_pct', result['offers'][0])
        self.assertNotIn('verified_discount_pct', without_reference['offers'][0])
        unrelated = [base | dict(id='tree', title='Albero di Natale', brand='Decorazioni'), base | dict(id='supplement', title='Integratore renale per gatti', brand='Supplements')]
        curated = build(dict(offers=[base]+unrelated, sources=[dict(id='shop')], generated_at=now.isoformat(), refresh_hours=6), now)
        self.assertEqual([o['id'] for o in curated['offers']], ['ok'])

class HomePrerenderTests(unittest.TestCase):
    def test_regions_are_replaced_idempotently_and_offer_text_escaped(self):
        from automation.build_home_data import render_home
        template = '<head><meta name="description" content="Quattro negozi"><meta property="og:description" content="Quattro negozi"></head><main id="main">'+''.join('<div id="'+name+'"><div>Caricamento…</div></div>' for name in ['home-stats','home-spotlight','home-deals-status','home-deals','home-brands','home-shops'])+'</main>'
        offer = dict(url='https://example.com/exact-product', affiliate_url='https://example.com/tracked-product', id='a', title='<script>alert(1)</script>', brand='Brand', merchant='Shop', merchant_id='shop', product_slug='test-canonical', variant='2 kg', price=10, previous_price=20, verified_before_price=15, verified_discount_pct=33.3, weight_kg=2, checked_at='2026-10-19T20:00:00+00:00', image='https://example.com/image.jpg')
        payload = dict(generated_at=offer['checked_at'], refresh_hours=6, stats=dict(offers=100,brands=2), top_brands=['Brand'], sources=[dict(id='shop',name='Shop',offers=100)], offers=[offer])
        with patch.dict(os.environ, {'PRICE_TRACKING_ENABLED':'true'}):
            rendered = render_home(template,payload)
            self.assertEqual(rendered, render_home(rendered,payload))
        self.assertNotIn('Caricamento',rendered)
        self.assertNotIn('<script>',rendered)
        self.assertIn('10,00 €',rendered)
        self.assertIn('data-home-offer',rendered)
        self.assertIn('5,00 €/kg',rendered)
        self.assertIn('class="product-title-link" href="/prodotto/test-canonical"',rendered)
        self.assertIn('<del>15,00 €</del>',rendered)
        self.assertNotIn('<del>20,00 €</del>',rendered)
        self.assertNotIn('catalog-sale',rendered)
        self.assertIn('Shop. Prezzi rilevati, non in tempo reale.', rendered)
        self.assertNotIn('Quattro negozi', rendered)
