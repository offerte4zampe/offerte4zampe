import datetime as dt
import unittest
from automation.build_product_catalog import build,history_count
class ProductIndexingTests(unittest.TestCase):
    def test_history_threshold_is_observed_dates_not_calendar_span(self):
        now=dt.datetime(2026,10,30,12,tzinfo=dt.timezone.utc)
        offer=dict(id='a:1',merchant_id='a',merchant='A',title='Food 2 kg',brand='Brand',price=12,available=True,weight_kg=2,gtin='4006381333931',checked_at=now.isoformat(),url='https://shop.test/a')
        rows=[dict(day=(now-dt.timedelta(days=i)).date().isoformat(),low=10,high=12,last=11,available=True) for i in range(30)]
        catalog={'generated_at':now.isoformat(),'offers':[offer]}
        self.assertFalse(build(catalog,history={'offers':{'a:1':rows[:29]}},now=now)['products'][0]['indexable'])
        model=build(catalog,history={'offers':{'a:1':rows}},now=now)
        self.assertEqual(history_count(model['products'][0]['history'],now),30)
        self.assertFalse(model['products'][0]['indexable'])
        archived=build({'generated_at':now.isoformat(),'offers':[]},model['registry'],history={'offers':{'a:1':rows}},now=now)
        self.assertFalse(archived['products'][0]['indexable'])
        self.assertEqual(len(archived['products'][0]['history']),30)
