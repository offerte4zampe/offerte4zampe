import unittest
from html.parser import HTMLParser
from automation.build_catalog_preview import render_directory


class Links(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.urls = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.urls.append(dict(attrs).get('href'))


class ProductDirectoryTests(unittest.TestCase):
    def test_all_indexable_products_are_linked_without_a_preview_limit(self):
        products = [dict(slug=f'food-{i}', name=f'Food {i}', brand='Pet', indexable=True)
                    for i in range(150)]
        result = render_directory('<main><h1>Prodotti</h1></main>', products)
        self.assertEqual(set(Links(result).urls), {'/prodotto/'+p['slug'] for p in products})
        self.assertEqual(len(Links(result).urls), 150)

    def test_excludes_noindex_and_unsafe_slugs_and_escapes_labels(self):
        products = [dict(slug='food', name='<script>food</script>', brand='A & B', indexable=True),
                    dict(slug='one-shop', name='One shop', indexable=False),
                    dict(slug='missing-flag'), dict(slug='//other.example', indexable=True),
                    dict(slug='food', name='Duplicate', indexable=True)]
        result = render_directory('<main></main>', products)
        self.assertEqual(Links(result).urls, ['/prodotto/food'])
        self.assertNotIn('<script>', result)
        self.assertIn('A &amp; B', result)
        self.assertIn('&lt;script&gt;food&lt;/script&gt;', result)

    def test_refresh_replaces_old_links_and_is_idempotent(self):
        products = [dict(slug='food', name='Food', indexable=True)]
        first = render_directory('<main></main>', products)
        self.assertEqual(first, render_directory(first, products))
        empty = render_directory(first, [])
        self.assertEqual(Links(empty).urls, [])
        self.assertEqual(empty.count('id="product-directory-title"'), 1)


if __name__ == '__main__':
    unittest.main()
