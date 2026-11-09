import unittest
from automation.build_category_pages import SEARCH_INTENTS, intent_html, category_items


class CategoryIntentSeoTests(unittest.TestCase):
    def test_each_category_has_relevant_existing_comparator_links(self):
        for slug in ('crocchette-cani', 'crocchette-gatti', 'lettiere-gatti'):
            self.assertEqual(len(SEARCH_INTENTS[slug]), 3)
            html = intent_html(slug)
            self.assertIn('aria-labelledby="ricerche-frequenti"', html)
            self.assertEqual(html.count('href="/confronta-cibo?q='), 3)
            self.assertNotIn('migliori prodotti', html.lower())

    def test_structured_items_only_use_internal_verified_canonical_slugs(self):
        offers = [
            {'title': 'Monge 12 kg', 'variant': '12kg', 'product_slug': 'monge-12-kg', 'affiliate_url': 'https://affiliate.example/?a=1'},
            {'title': 'Unknown product', 'variant': '', 'product_slug': 'https://evil.example/', 'affiliate_url': 'https://affiliate.example/?a=2'}
        ]
        items = category_items(offers)
        self.assertEqual(items, [('Monge 12 kg — 12kg', 'https://offerte4zampe.it/prodotto/monge-12-kg')])
        self.assertNotIn('affiliate.example', str(items))


if __name__ == '__main__':
    unittest.main()
