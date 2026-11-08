import copy
import datetime as dt
import math
import unittest
from automation.build_observatory import calculate, fingerprint, render


class ObservatoryTests(unittest.TestCase):
    def setUp(self):
        # Synthetic fixtures only; no invented observations enter the public catalog.
        self.today=dt.date(2026,11,1)
        self.catalog={'offers':[]}
        self.history={'offers':{},'identities':{}}
        for i in range(10):
            offer=dict(id=str(i),merchant_id=('bauzaar' if i%2 else 'webpet'),title='Fixture',variant='2 kg',brand='Fixture',gtin='',weight_kg=2,category='Fixture category')
            self.catalog['offers'].append(offer)
            self.history['identities'][str(i)]=fingerprint(offer)
            self.history['offers'][str(i)]=[]
            for month,price in [('09',10),('10',12 if i%2 else 8)]:
                for day in range(1,8):
                    date=f'2026-{month}-{day:02d}'
                    self.history['offers'][str(i)].append(dict(day=date,low=price,last=price,high=price,available=True,checked_at=date+'T12:00:00+00:00'))

    def october(self,**kwargs):
        return next(r for r in calculate(kwargs.get('catalog',self.catalog),kwargs.get('history',self.history),kwargs.get('today',self.today))['months'] if r['month']=='2026-10')

    def test_closed_month_equal_weight_geometric_relatives_and_auditable_panel(self):
        row=self.october()
        self.assertEqual(row['matched_offers'],10)
        self.assertEqual(row['matched_merchants'],2)
        self.assertAlmostEqual(row['index_previous_month_100'],100*math.sqrt(.96))
        self.assertEqual(len(row['panel']),10)
        self.assertEqual(row['panel'][0]['base_days'],7)

    def test_open_month_never_publishes_even_when_sample_is_sufficient(self):
        row=self.october(today=dt.date(2026,10,20))
        self.assertIsNone(row['index_previous_month_100'])
        self.assertEqual(row['status'],'month_open')
        self.assertEqual(row['panel'],[])

    def test_changed_identity_and_missing_days_do_not_inherit_history(self):
        cat=copy.deepcopy(self.catalog)
        cat['offers'][0]['variant']='New recipe'
        row=self.october(catalog=cat)
        self.assertEqual(row['matched_offers'],9)
        self.assertIsNone(row['index_previous_month_100'])
        hist=copy.deepcopy(self.history)
        hist['offers']['0'].pop()
        self.assertEqual(self.october(history=hist)['matched_offers'],9)

    def test_invalid_unavailable_mismatched_dates_and_duplicates_are_not_days(self):
        for patch in [dict(last=True),dict(low=-1),dict(high=float('inf')),dict(high=1),dict(available=False),dict(checked_at='2026-09-07T12:00:00Z'),dict(checked_at='2026-10-07T12:00:00')]:
            hist=copy.deepcopy(self.history)
            hist['offers']['0'][-1].update(patch)
            self.assertEqual(self.october(history=hist)['matched_offers'],9)
        hist=copy.deepcopy(self.history)
        hist['offers']['0'].append(hist['offers']['0'][-1].copy())
        self.assertEqual(self.october(history=hist)['matched_offers'],9)

    def test_single_merchant_is_not_a_published_category_index(self):
        cat=copy.deepcopy(self.catalog);hist=copy.deepcopy(self.history)
        for offer in cat['offers']:
            offer['merchant_id']='bauzaar'
            hist['identities'][offer['id']]=fingerprint(offer)
        self.assertIsNone(self.october(catalog=cat,history=hist)['index_previous_month_100'])

    def test_no_backfill_empty_fallback_and_visible_limits(self):
        data=calculate({'offers':[]},{},self.today)
        self.assertEqual(data['months'],[])
        html=render('<html><head><title>Template</title></head><body><main></main></body></html>',data)
        self.assertIn('Nessun indice viene ricostruito',html)
        self.assertIn('180 giorni',html)
        self.assertIn('non di inflazione',html)
