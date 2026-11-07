import datetime
import os
from unittest.mock import patch
import unittest

from automation.build_home_data import build, pick, render_home

UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 11, 4, 12, tzinfo=UTC)
STAMP = NOW.isoformat()

def offer(number, brand=None, price=20, checked_at=STAMP):
    return dict(id='merchant:'+str(number), merchant_id='merchant', merchant='Pet Store',
                brand=brand or ('Brand '+str(number)), title='Dog food '+str(number)+' 2 kg',
                category='Dog Food', variant='2 kg', price=price, weight_kg=2,
                image='https://example.com/p.jpg', url='https://example.com/p', available=True,
                checked_at=checked_at)

def catalog(offers):
    return dict(offers=offers, sources=[dict(id='merchant', status='ok', checked_at=STAMP, name='Pet Store')],
                generated_at=STAMP, refresh_hours=6)

class MerchandisingTests(unittest.TestCase):
    def setUp(self):
        # These legacy cases validate behavior only if Amazon explicitly permits history.
        self._flag = patch.dict(os.environ, {'PRICE_TRACKING_ENABLED':'true'})
        self._flag.start()
        self.addCleanup(self._flag.stop)

    def test_observed_drop_is_prioritized_not_seller_previous_price(self):
        a,b,c = offer(1), offer(2), offer(3)
        b['previous_price'] = 1000  # unverified vendor reference cannot create a discount
        history = {'offers': {a['id']:[
            dict(day='2026-11-01', last=30),dict(day='2026-11-02', last=30)]}}
        result=build(catalog([b,c,a]),NOW,history)
        self.assertEqual(result['offers'][0]['id'],a['id'])
        self.assertEqual(result['offers'][0]['verified_before_price'],30)
        self.assertEqual(result['offers'][0]['verified_discount_pct'],33.3)
        self.assertTrue(all('verified_discount_pct' not in o for o in result['offers'][1:]))
        self.assertNotIn('previous_price',result['offers'][1])
        picks,hero=pick(result)
        self.assertEqual(hero['id'],a['id'])
        self.assertEqual(picks[0]['id'],a['id'])

    def test_two_prior_days_and_lowest_prior_price_required(self):
        a,b,c=offer(1,price=20),offer(2,price=20),offer(3,price=20)
        history={'offers':{
            a['id']:[dict(day='2026-11-01',last=30)],
            b['id']:[dict(day='2026-11-01',last=30),dict(day='2026-11-02',last=19)],
            c['id']:[dict(day='2026-11-01',last=30),dict(day='2026-11-02',last=27)]}}
        result=build(catalog([a,b,c]),NOW,history)
        byid={o['id']:o for o in result['offers']}
        self.assertNotIn('verified_discount_pct',byid[a['id']])
        self.assertNotIn('verified_discount_pct',byid[b['id']])
        self.assertEqual(byid[c['id']]['verified_discount_pct'],25.9)

    def test_stale_source_excluded_and_output_stable_for_same_day(self):
        many=[offer(i) for i in range(40)]
        a=build(catalog(many),NOW)
        b=build(catalog(list(reversed(many))),NOW)
        self.assertEqual([o['id'] for o in a['offers']], [o['id'] for o in b['offers']])
        stale=catalog(many)
        stale['sources'][0]['checked_at']='2026-11-01T00:00:00+00:00'
        self.assertEqual(build(stale,NOW)['offers'],[])

    def test_render_does_not_claim_discount_without_history(self):
        a=offer(1)
        payload=build(catalog([a]),NOW)
        template='<main id="main">'+''.join('<div id="'+n+'"></div>' for n in
          ('home-stats','home-spotlight','home-deals-status','home-deals','home-brands','home-shops'))+'</main>'
        html=render_home(template,payload)
        self.assertIn('Oggi non risultano ribassi',html)
        self.assertNotIn('<article class="home-deal"',html)
        self.assertNotIn('Ribasso verificato',html)
        history={'offers':{a['id']:[dict(day='2026-11-01',last=30),dict(day='2026-11-02',last=30)]}}
        html=render_home(template,build(catalog([a]),NOW,history))
        self.assertIn('RIBASSO',html)
        self.assertIn('<del>30,00 €</del>',html)
        self.assertIn('Prezzo precedente osservato',html)


    def test_verified_cross_store_comparison(self):
        cheap = offer(20, 'Acme', 19)
        cheap.update(product_id='group-a', product_identity_verified=True)
        dear = offer(21, 'Acme', 29)
        dear.update(id='other:21', merchant_id='other', merchant='Other Shop',
                    product_id='group-a', product_identity_verified=True)
        c = catalog([cheap, dear])
        c['sources'].append(dict(id='other', status='ok', checked_at=STAMP, name='Other Shop'))
        payload = build(c, NOW)
        self.assertEqual(len(payload['offers']), 1)
        row = payload['offers'][0]
        self.assertEqual(row['price'], 19)
        self.assertEqual(row['comparison_other_price'], 29)
        self.assertEqual(row['comparison_savings_pct'], 34.5)
        self.assertNotIn('verified_discount_pct', row)
        template='<main id="main">'+''.join('<div id="'+n+'"></div>' for n in
          ('home-stats','home-spotlight','home-deals-status','home-deals','home-brands','home-shops'))+'</main>'
        html = render_home(template, payload)
        self.assertIn('TRA NEGOZI', html)
        self.assertIn('Altrove 29,00 €', html)
        self.assertIn('Qui</span><strong>19,00 €', html)
        self.assertIn('non è uno sconto del negozio', html)
        self.assertNotIn('<del>', html)

    def test_unverified_identity_never_gains_comparison(self):
        a,b=offer(31,'Acme',19),offer(32,'Acme',29)
        a.update(product_id='same', product_identity_verified=False)
        b.update(product_id='same', product_identity_verified=False, merchant_id='other', merchant='Other Shop')
        c=catalog([a,b])
        c['sources'].append(dict(id='other',status='ok',checked_at=STAMP,name='Other Shop'))
        self.assertFalse(any('comparison_savings_pct' in x for x in build(c,NOW)['offers']))
        a['product_identity_verified']=b['product_identity_verified']=True
        b['merchant_id']='merchant'
        self.assertFalse(any('comparison_savings_pct' in x for x in build(catalog([a,b]),NOW)['offers']))

    def test_second_cheapest_reference_not_highest(self):
        rows=[offer(i,'Acme',p) for i,p in [(40,20),(41,25),(42,90)]]
        for i,row in enumerate(rows):
            row.update(product_id='same-verified',product_identity_verified=True,
                       merchant_id=f'shop{i}',merchant=f'Shop {i}')
        c=catalog(rows)
        c['sources']=[dict(id=f'shop{i}',name=f'Shop {i}',status='ok',checked_at=STAMP) for i in range(3)]
        data=build(c,NOW)
        self.assertEqual(data['offers'][0]['id'],rows[0]['id'])
        self.assertEqual(data['offers'][0]['comparison_other_price'],25)
        self.assertEqual(data['offers'][0]['comparison_savings_pct'],20)


    def test_large_spotlight_is_offer_of_the_day_only_when_verified(self):
        template = '<main id="main"><span id="daily-pick-label">Dal catalogo reale</span>'+''.join(
            '<div id="'+name+'"></div>' for name in
            ('home-stats','home-spotlight','home-deals-status','home-deals','home-brands','home-shops'))+'</main>'
        a = offer(99)
        absent = render_home(template, build(catalog([a]), NOW))
        self.assertIn('NESSUNA OFFERTA VERIFICATA OGGI', absent)
        self.assertNotIn('OFFERTA DEL GIORNO</span>', absent)
        history = {'offers': {a['id']: [
            dict(day='2026-11-01', last=30), dict(day='2026-11-02', last=30)]}}
        present = render_home(template, build(catalog([a]), NOW, history))
        self.assertIn('OFFERTA DEL GIORNO</span>', present)
        self.assertIn('−33,3% RIBASSO', present)
        self.assertIn('Prima <del>30,00 €</del>', present)


    def test_daily_hero_rotates_only_among_verified_deals(self):
        a,b,c = offer(51),offer(52),offer(53)
        history={'offers': {row['id']:[
            dict(day='2026-11-01',last=30),dict(day='2026-11-02',last=30)
        ] for row in (a,b,c)}}
        first=build(catalog([a,b,c]), NOW, history)
        self.assertIn(first['daily_pick_id'],[o['id'] for o in first['offers']])
        self.assertEqual(pick(first)[1]['id'], first['daily_pick_id'])
        tomorrow = NOW + datetime.timedelta(days=1)
        next_catalog = catalog([{**o,'checked_at':tomorrow.isoformat()} for o in (a,b,c)])
        next_catalog['sources'][0]['checked_at']=tomorrow.isoformat()
        second=build(next_catalog, tomorrow, history)
        self.assertIn(second['daily_pick_id'],[o['id'] for o in second['offers']])
        self.assertNotEqual(first['daily_pick_id'],second['daily_pick_id'])
        self.assertIsNone(build(catalog([a]), NOW)['daily_pick_id'])

if __name__=='__main__':
    unittest.main()
