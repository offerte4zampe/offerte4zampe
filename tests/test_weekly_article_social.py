import datetime as dt
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from automation import build_weekly_article_social as article
from automation.apply_navigation import PARTIALS, apply, disclosure


class WeeklyArticleTests(unittest.TestCase):
    def test_generated_article_has_working_shared_chrome_and_preserves_offers(self):
        day = dt.datetime.now(dt.timezone.utc).date().isoformat()
        offers = [{
            'name': f'Crocchette cane {i} 2kg', 'format': '2 kg',
            'price': '12.00 €', 'shop': 'Negozio', 'category': 'alimenti secchi cane',
            'weight_kg': 2, 'url': f'https://shop.example/item/{i}?a=1&b=2',
            'image': f'https://shop.example/images/{i}.jpg',
        } for i in range(3)]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'automation').mkdir()
            payload = root / 'newsletter-approved.json'
            payload.write_text(json.dumps({'selection_version': 2, 'verified_on': day, 'offers': offers}))
            with patch.object(article, 'ROOT', root), patch.object(article, 'SITE', root / 'site'), patch.object(article, 'PAYLOAD', payload):
                article.build()
            html = (root / 'site' / 'offerte' / f'offerte-settimana-{day}.html').read_text()
            self.assertEqual(re.search(r'<header\b.*?</header>', html, re.S)[0], (PARTIALS / 'header.html').read_text().strip())
            self.assertEqual(re.search(r'<footer\b.*?</footer>', html, re.S)[0], (PARTIALS / 'footer.html').read_text().strip().replace('{{affiliate_disclosure}}', disclosure()))
            self.assertEqual(html.count('<header>'), 1)
            self.assertEqual(html.count('<footer'), 1)
            self.assertEqual(apply(html), html)
            self.assertIn('href="/assets/style.css"', html)
            self.assertIn('src="/assets/base.js" defer', html)
            self.assertIn(f'href="https://offerte4zampe.it/offerte/offerte-settimana-{day}.html"', html)
            self.assertEqual(html.count('12.00 €'), 3)
            for i in range(3):
                self.assertIn(f'href="https://shop.example/item/{i}?a=1&amp;b=2"', html)
                self.assertIn(f'src="https://shop.example/images/{i}.jpg"', html)
            draft = json.loads((root / 'automation' / 'weekly-social-draft.json').read_text())
            self.assertEqual(draft['status'], 'draft_not_published_requires_visual_verification')
