import datetime as dt
import unittest
from automation.build_commercial_lines import LINES, MIN_OFFERS, select, render, eligible

NOW = dt.datetime(2026, 11, 8, 12, 0, tzinfo=dt.timezone.utc)
LINE = LINES[0]

def offer(i, merchant=None, **overrides):
    row = dict(id='row:'+str(i), merchant_id=merchant or ('a' if i % 2 else 'b'),
               merchant=merchant or ('Shop A' if i % 2 else 'Shop B'),
               title='Monge Supreme Tonno confezione '+str(i % 4), brand='Monge',
               price=10.0+i, available=True, checked_at=NOW.isoformat(),
               url='https://shop.example/product', product_slug='monge-supreme-'+str(i % 4),
               weight_kg=1.0, variant='1kg')
    row.update(overrides)
    return row

class CommercialLineSEOTest(unittest.TestCase):
    def test_curated_allowlist_has_only_fifteen_non_medicine_lines(self):
        self.assertEqual(len(LINES), 15)
        slugs=[line[0] for line in LINES]
        self.assertEqual(len(set(slugs)), len(slugs))
        self.assertFalse(any('seresto' in x or 'frontline' in x or 'advantix' in x for x in slugs))

    def test_publish_only_with_evidence_across_merchants_and_canonicals(self):
        rows=[offer(i) for i in range(12)]
        selected,picked=select(rows, LINE, NOW)
        self.assertEqual(len(selected),12)
        self.assertEqual(len(picked),4)
        self.assertEqual(select(rows[:11], LINE, NOW)[1],[])
        self.assertEqual(select([offer(i, merchant='a') for i in range(12)], LINE, NOW)[1],[])
        self.assertEqual(select([offer(i, product_slug='single-slug') for i in range(12)], LINE, NOW)[1],[])

    def test_avoid_false_brand_and_keyword_hits(self):
        self.assertFalse(eligible(offer(1, brand='Other', title='Monge Supreme'), LINE[2], LINE[3], NOW))
        self.assertFalse(eligible(offer(1, title='Monge Supremeness'), LINE[2], LINE[3], NOW))
        self.assertFalse(eligible(offer(1, checked_at='2020-01-01T00:00:00Z'), LINE[2], LINE[3], NOW))
        self.assertFalse(eligible(offer(1, product_slug='https://evil.test/'), LINE[2], LINE[3], NOW))

    def test_html_uses_only_internal_product_links_and_escapes_titles(self):
        rows,picked=select([offer(i,title='Monge Supreme <script> '+str(i)) for i in range(12)],LINE,NOW)
        template='<html><head><title>Old</title><meta name="description" content="Old"><link rel="canonical" href="https://offerte4zampe.it/chi-siamo"></head><body><main>Old</main></body></html>'
        html=render(template, LINE, rows, picked)
        self.assertIn('https://offerte4zampe.it/linea-monge-supreme',html)
        self.assertIn('/prodotto/monge-supreme-',html)
        self.assertNotIn('<script>',html)
        self.assertNotIn('https://shop.example/product',html)
        self.assertNotIn('minimo storico',html)
        self.assertIn('spedizione esclusa',html)

if __name__=='__main__':
    unittest.main()
