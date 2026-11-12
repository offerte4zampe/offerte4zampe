import os
import unittest
from unittest.mock import patch

from automation import run_render_newsletter as runner


class RenderNewsletterSafetyTests(unittest.TestCase):
    def test_refuses_non_render_execution_before_any_payload_or_api_work(self):
        with patch.dict(os.environ, {"BREVO_SEND_RUNTIME": "render"}, clear=True), \
             patch.object(runner.build_weekly_newsletter, "build") as build, \
             patch.object(runner.send_brevo_newsletter, "main") as send:
            with self.assertRaises(ValueError):
                runner.main()
            build.assert_not_called()
            send.assert_not_called()

    def test_requires_explicit_runtime_selection(self):
        with patch.dict(os.environ, {"RENDER": "true"}, clear=True), \
             patch.object(runner.send_brevo_newsletter, "main") as send:
            with self.assertRaises(ValueError):
                runner.main()
            send.assert_not_called()

    def test_stale_catalog_failure_never_calls_sender_and_cancels_timer(self):
        with patch.dict(os.environ, {"RENDER": "true", "BREVO_SEND_RUNTIME": "render"}, clear=True), \
             patch.object(runner.build_weekly_newsletter, "build", side_effect=ValueError("Catalog stale")), \
             patch.object(runner.send_brevo_newsletter, "main") as send, \
             patch.object(runner.signal, "alarm") as alarm:
            with self.assertRaises(ValueError):
                runner.main()
            send.assert_not_called()
            self.assertEqual(alarm.call_args_list[-1].args, (0,))

    def test_dry_run_does_not_call_brevo_with_a_valid_current_payload(self):
        import datetime as dt
        import json
        import tempfile
        from pathlib import Path
        payload = {"selection_version": 2, "verified_on": dt.datetime.now(dt.timezone.utc).date().isoformat(),
                   "subject": "Offerte", "offers": [
                       {"name": f"Crocchette cane alimento {i} 2kg", "format": "2 kg",
                        "price": "15.00 €", "shop": "Negozio", "url": f"https://example.org/p/{i}",
                        "image": f"https://example.org/i/{i}.jpg", "category": "alimenti secchi cane",
                        "weight_kg": 2} for i in range(3)]}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "newsletter.json"
            path.write_text(json.dumps(payload))
            env = {"RENDER": "true", "BREVO_SEND_RUNTIME": "render", "BREVO_SEND_ENABLED": "false",
                   "BREVO_LIST_ID": "3", "NEWSLETTER_PAYLOAD": str(path)}
            with patch.dict(os.environ, env, clear=True), \
                 patch.object(runner.build_weekly_newsletter, "build"), \
                 patch.object(runner.send_brevo_newsletter, "request") as api:
                runner.main()
                api.assert_not_called()
