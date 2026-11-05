import datetime as dt
import json
from pathlib import Path
import unittest
from automation.monitor_shipping_rules import report, main

class RenewalMonitorTests(unittest.TestCase):
    def test_warning_starts_fourteen_days_before_thirty_day_expiry(self):
        data=json.loads((Path(__file__).parents[1]/'site/data/shipping-rules.json').read_text())
        ids={'bauzaar','webpet','isola-dei-tesori','paco'}
        end=dt.datetime.fromisoformat(data['merchants']['bauzaar']['verified_until'].replace('Z','+00:00'))
        for offset,expected in [(dt.timedelta(days=14,microseconds=1),'current'),(dt.timedelta(days=14),'expiring'),(dt.timedelta(0),'expired')]:
            states={r['merchant']:r['status'] for r in report(data,end-offset)['merchants']}
            for merchant in ids:self.assertEqual(states[merchant],expected)
        # Both missing/conflicting merchants may warn; default execution never blocks imports.
        self.assertEqual(main(['--now',(end+dt.timedelta(days=1)).isoformat()]),0)
