import datetime
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
        self.assertIn('sconto non verificato',html)
        self.assertNotIn('Ribasso verificato',html)
        history={'offers':{a['id']:[dict(day='2026-11-01',last=30),dict(day='2026-11-02',last=30)]}}
        html=render_home(template,build(catalog([a]),NOW,history))
        self.assertIn('Ribasso verificato',html)
        self.assertIn('prezzo precedente osservato',html)

if __name__=='__main__':
    unittest.main()
