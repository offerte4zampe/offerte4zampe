import pathlib
import tempfile
import unittest
from automation.build_sitemaps import inventory, fingerprint


def html(price='10',date='2026-10-19T20:00:00+00:00',robots='index,follow'):
    return '<head><title>Product</title><link rel="canonical" href="https://offerte4zampe.it/product"><meta name="robots" content="'+robots+'"></head><main><p>'+price+' €</p><time datetime="'+date+'">'+date+'</time><p>Recupero '+date+'</p></main><footer>2026</footer>'


class SitemapsTests(unittest.TestCase):
    def test_refresh_clock_and_copyright_do_not_change_fingerprint(self):
        self.assertEqual(fingerprint(html()),fingerprint(html(date='2026-10-20T10:00:00+00:00').replace('<footer>2026','<footer>2027')))
        self.assertNotEqual(fingerprint(html()),fingerprint(html(price='11')))

    def test_nested_blog_pages_are_included_without_scanning_generated_products(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = pathlib.Path(tmp)
            article = site / 'blog' / 'example' / 'index.html'
            article.parent.mkdir(parents=True)
            article.write_text(html().replace('https://offerte4zampe.it/product',
                                           'https://offerte4zampe.it/blog/example/'))
            generated = site / 'prodotto' / 'example' / 'index.html'
            generated.parent.mkdir(parents=True)
            generated.write_text(html().replace('https://offerte4zampe.it/product',
                                               'https://offerte4zampe.it/prodotto/example'))
            state, partitions = inventory(site, {}, '2026-11-08T00:00:00+00:00')
            self.assertIn('https://offerte4zampe.it/blog/example/', state)
            self.assertNotIn('https://offerte4zampe.it/prodotto/example', state)
            self.assertEqual(len(partitions['guides']), 1)

    def test_lastmod_only_on_observed_change_and_noindex_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            site=pathlib.Path(tmp);path=site/'product.html';path.write_text(html())
            first,_=inventory(site,{},'2026-10-20T01:00:00+00:00')
            self.assertIsNone(first['https://offerte4zampe.it/product']['lastmod'])
            same,_=inventory(site,first,'2026-10-21T01:00:00+00:00')
            self.assertEqual(first,same)
            path.write_text(html(price='11'))
            changed,_=inventory(site,same,'2026-10-22T01:00:00+00:00')
            self.assertEqual(changed['https://offerte4zampe.it/product']['lastmod'],'2026-10-22T01:00:00+00:00')
            path.write_text(html(robots='noindex,follow'))
            self.assertEqual(inventory(site,changed,'2026-10-23T01:00:00+00:00')[0],{})
