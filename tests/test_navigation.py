import unittest
from automation.apply_navigation import apply


class NavigationTests(unittest.TestCase):
    def test_scoped_and_idempotent(self):
        old = '<a href="confronta-cibo.html?sale=1">Offerte</a>'
        cta = '<a class="navcta" href="confronta-cibo.html">Cerca prodotti ↗</a>'
        html = old + '<nav class="navlinks" id="navlinks" aria-label="Principale">' + old + cta + '<a href="/blog/" aria-current="page">Guide</a></nav>' + '<a href="https://tc.tradetracker.net/?c=16143" rel="sponsored">Prodotto</a>'
        result = apply(html)
        self.assertTrue(result.startswith(old))
        self.assertIn('<a href="/prodotti">Prodotti</a>', result)
        self.assertNotIn('Cerca prodotti', result)
        self.assertIn('aria-current="page">Guide', result)
        self.assertIn('https://tc.tradetracker.net/?c=16143', result)
        self.assertEqual(apply(result), result)

    def test_other_navigation_unchanged(self):
        html = '<nav id="categories"><a href="confronta-cibo.html?sale=1">Offerte</a></nav>'
        self.assertEqual(apply(html), html)

    def test_all_published_pages_use_shared_chrome(self):
        import re
        from automation.apply_navigation import ROOT, PARTIALS, disclosure
        header = (PARTIALS / 'header.html').read_text().strip()
        footer = (PARTIALS / 'footer.html').read_text().strip().replace('{{affiliate_disclosure}}', disclosure())
        for href in ('/blog/', '/marche', '/confronti-prodotti', '/correzioni'):
            self.assertIn(f'href="{href}"', footer)
        for path in (ROOT / 'site').rglob('*.html'):
            html = path.read_text()
            if html.startswith('google-site-verification:'):
                continue
            html = apply(html)
            with self.subTest(page=path.name):
                actual = re.search(r'<header\b.*?</header>', html, re.S)[0]
                self.assertEqual(actual.replace(' aria-current="page"', ''), header)
                self.assertEqual(re.search(r'<footer\b.*?</footer>', html, re.S)[0], footer)
                self.assertEqual(apply(html), html)

    def test_disclosure_uses_affiliate_config_and_preserves_commercial_links(self):
        from unittest.mock import patch
        from automation.apply_navigation import disclosure
        html = '<header><nav id="navlinks"></nav></header><main><a href="/go/shop:1" rel="sponsored">Shop ↗</a><a href="https://shop.test/?aff=1">Shop ↗</a><p>Trasparenza: nel catalogo i link verso Bauzaar possono essere affiliati tramite TradeTracker. Le commissioni non determinano l’ordinamento dei risultati.</p></main><footer>Old</footer>'
        with patch('automation.apply_navigation.affiliate_names', return_value='Negozio A e Negozio B'):
            result = apply(html)
            self.assertIn(disclosure(), result)
            self.assertEqual(result.count('Negozio A e Negozio B'), 2)
            self.assertNotIn('Bauzaar', result)
            self.assertIn('href="/go/shop:1" rel="sponsored">Shop</a>', result)
            self.assertIn('href="https://shop.test/?aff=1">Shop ↗</a>', result)
            self.assertEqual(apply(result), result)

    def test_product_breadcrumb_points_to_products(self):
        from automation.apply_navigation import ROOT
        self.assertIn('href="/prodotti">Prodotti</a>', (ROOT / 'worker/canonical-product.mjs').read_text())
