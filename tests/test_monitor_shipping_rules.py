import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest

from automation import monitor_shipping_rules as monitor


class ShippingMonitorTests(unittest.TestCase):
    def setUp(self):
        self.now = monitor.parse('2026-11-04T16:52:00Z')
        self.rules = {'merchants': {
            'current': {'checked_at': '2026-11-04', 'verified_until': '2026-12-01T00:00Z'},
            'soon': {'checked_at': '2026-11-04', 'verified_until': '2026-11-15T00:00Z'},
            'expired': {'checked_at': '2026-10-28', 'verified_until': '2026-11-04T00:00Z'},
            'bad': {'checked_at': 'broken', 'verified_until': 'broken'},
            'animaliapet': {'checked_at': '2026-11-04', 'verified_until': '2026-12-01T00:00Z', 'conflict': True}}}

    def test_fourteen_day_window_and_distinct_health_states_without_mutation(self):
        original = copy.deepcopy(self.rules)
        report = monitor.report(self.rules, self.now, ['hygge'])
        self.assertEqual(self.rules, original)
        self.assertEqual(report['warning_hours'], 336)
        states = {r['merchant']: r['status'] for r in report['merchants']}
        self.assertEqual(states, {'current': 'current', 'soon': 'expiring', 'expired': 'expired',
                                  'bad': 'invalid', 'animaliapet': 'current', 'hygge': 'missing'})
        quotes = {r['merchant']: r['quote_status'] for r in report['merchants']}
        self.assertEqual(quotes['animaliapet'], 'conflict')
        self.assertEqual(quotes['hygge'], 'unknown')
        self.assertEqual(quotes['expired'], 'unknown')

    def test_default_covers_all_six_merchants(self):
        result = monitor.report({'merchants': {}}, self.now)
        self.assertEqual({r['merchant'] for r in result['merchants']}, set(monitor.EXPECTED_MERCHANTS))
        self.assertEqual(len(result['merchants']), 6)

    def test_expiry_boundary_and_future_verification(self):
        for rule in [{'checked_at': '2026-11-04', 'verified_until': self.now.isoformat()},
                     {'checked_at': '2026-11-05', 'verified_until': '2026-11-20'}]:
            result = monitor.report({'merchants': {'x': rule}}, self.now, ())
            self.assertIn(result['merchants'][0]['status'], ('expired', 'invalid'))

    def test_default_warns_and_opt_in_fails_without_modifying_rules(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'rules.json'
            output = Path(temp) / 'report.json'
            path.write_text(json.dumps(self.rules))
            before = path.read_bytes()
            args = [str(path), '--now', self.now.isoformat(), '--annotations', '--output', str(output)]
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.assertEqual(monitor.main(args), 0)
                self.assertEqual(monitor.main(args + ['--fail-on-expired']), 1)
            self.assertEqual(path.read_bytes(), before)
            self.assertTrue(output.exists())
            self.assertIn('::warning title=Shipping evidence::', stderr.getvalue())
            self.assertEqual(json.loads(output.read_text())['warning_hours'], 336)

    def test_report_cannot_overwrite_input(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'rules.json'
            path.write_text(json.dumps(self.rules))
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                monitor.main([str(path), '--output', str(path)])
            self.assertEqual(json.loads(path.read_text()), self.rules)

    def test_annotation_escapes_newlines_and_workflow_commands(self):
        self.assertEqual(monitor.annotation_message('a%\r\n::error::x'), 'a%25%0D%0A::error::x')

    def test_repository_data_reports_conflict_and_missing_rule(self):
        path = monitor.ROOT / 'site/data/shipping-rules.json'
        before = path.read_bytes()
        rows = {r['merchant']: r for r in monitor.report(json.loads(before), self.now)['merchants']}
        self.assertEqual(rows['hygge']['status'], 'missing')
        self.assertEqual(rows['animaliapet']['quote_status'], 'conflict')
        self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
