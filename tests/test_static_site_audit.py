import tempfile
import unittest
from pathlib import Path
from automation.audit_site import inspect


BASE='''<!doctype html><html lang="it"><head><meta name="viewport" content="width=device-width"><meta name="description" content="D"><meta name="robots" content="index,follow"><link rel="canonical" href="https://offerte4zampe.it/{slug}"><title>T</title></head><body><a class="skip" href="#main">Salta</a><main id="main"><h1>H</h1>{body}</main></body></html>'''


class StaticSiteAuditTests(unittest.TestCase):
    def run_site(self,pages):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name,html in pages.items():(root/name).write_text(html)
            return inspect(root)

    def test_nested_blog_pages_and_links_are_audited(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'blog' / 'article').mkdir(parents=True)
            (root / 'index.html').write_text(BASE.format(
                slug='', body='<a href="/blog/">Blog</a><a href="/blog/article/">Articolo</a>'))
            (root / 'blog' / 'index.html').write_text(BASE.format(
                slug='blog/', body='<a href="/blog/article/">Articolo</a>'))
            (root / 'blog' / 'article' / 'index.html').write_text(BASE.format(
                slug='blog/article/', body='<a href="/blog/">Blog</a><a href="/">Home</a>'))
            report = inspect(root)
            self.assertEqual(report['pages_scanned'], 3)
            self.assertEqual(report['issues'], [])
            (root / 'blog' / 'article' / 'index.html').write_text(BASE.format(
                slug='blog/article/', body='<a href="/blog/not-found/">Manca</a>'))
            self.assertIn('valid_internal_link', {row['rule'] for row in inspect(root)['issues']})

    def test_valid_page_and_commercial_link_require_sponsored(self):
        html=BASE.format(slug='one',body='<a href="https://tc.tradetracker.net/x" rel="sponsored noopener noreferrer" target="_blank">Shop</a><img src="x" alt="" width="4" height="5"><script type="application/ld+json">{"@context":"https://schema.org"}</script>')
        self.assertEqual(self.run_site({'one.html':html})['issues'],[])
        broken=html.replace('sponsored ','').replace(' width="4"','').replace('{"@context":"https://schema.org"}','{')
        rules={x['rule'] for x in self.run_site({'one.html':broken})['issues']}
        self.assertEqual(rules,{'commercial_rel_sponsored','image_dimensions','valid_json_ld'})

    def test_duplicate_and_noncanonical_urls_are_rejected_only_for_indexable_pages(self):
        one=BASE.format(slug='same',body='')
        two=BASE.format(slug='same',body='')
        rules={x['rule'] for x in self.run_site({'one.html':one,'two.html':two})['issues']}
        self.assertIn('unique_canonical',rules)
        noindex=two.replace('index,follow','noindex,follow').replace('<link rel="canonical" href="https://offerte4zampe.it/same">','')
        self.assertEqual(self.run_site({'one.html':one,'two.html':noindex})['issues'],[])

    def test_landmarks_metadata_images_and_safe_new_tabs_are_gated(self):
        html=BASE.format(slug='bad?x=1',body='<a target="_blank" href="https://example.com">X</a><img src="x">')
        html=html.replace(' lang="it"','').replace('<h1>H</h1>','').replace('class="skip"','class="other"')
        rules={x['rule'] for x in self.run_site({'bad.html':html})['issues']}
        self.assertTrue({'html_lang_it','one_h1','skip_link','image_alt','image_dimensions','safe_new_tab','clean_internal_canonical'}<=rules)

    def test_internal_pages_and_fragments_must_resolve(self):
        one=BASE.format(slug='one',body='<a href="/two#details">Due</a><a href="#main">Inizio</a>')
        two=BASE.format(slug='two',body='<section id="details">Dettagli</section>')
        self.assertEqual(self.run_site({'one.html':one,'two.html':two})['issues'],[])
        broken_page=one.replace('/two#details','/missing')
        self.assertIn('valid_internal_link',{x['rule'] for x in self.run_site({'one.html':broken_page,'two.html':two})['issues']})
        broken_fragment=one.replace('#details','#missing')
        self.assertIn('valid_internal_fragment',{x['rule'] for x in self.run_site({'one.html':broken_fragment,'two.html':two})['issues']})

    def test_assets_external_and_special_schemes_are_not_page_targets(self):
        body='<a href="/assets/style.css">CSS</a><a href="https://example.com/x">Esterno</a><a href="mailto:ciao@example.com">Email</a>'
        self.assertEqual(self.run_site({'one.html':BASE.format(slug='one',body=body)})['issues'],[])

    def test_search_console_verification_token_is_not_a_content_page(self):
        token='google-site-verification: google123.html'
        result=self.run_site({'google123.html':token,'one.html':BASE.format(slug='one',body='')})
        self.assertEqual(result['pages_scanned'],1)
        self.assertEqual(result['issues'],[])

    def test_report_context_is_application_state_not_a_broken_anchor(self):
        target=BASE.format(slug='segnala-errore',body='')
        one=BASE.format(slug='one',body='<a href="/segnala-errore#id=shop%3A123&amp;title=Test">Segnala</a>')
        self.assertEqual(self.run_site({'one.html':one,'segnala-errore.html':target})['issues'],[])
        for href in ['/segnala-errore#missing','/segnala-errore#id=123&amp;unknown=1','/one#id=123']:
            source=BASE.format(slug='one',body='<a href="'+href+'">Segnala</a>')
            self.assertIn('valid_internal_fragment',{x['rule'] for x in self.run_site({'one.html':source,'segnala-errore.html':target})['issues']})

    def test_outbound_routes_require_real_offer_id_and_commercial_rel(self):
        import gzip,json
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'data').mkdir()
            (root/'data/catalog.json.gz').write_bytes(gzip.compress(json.dumps({'offers':[{'id':'shop:1'}]}).encode()))
            valid='<a href="/go/shop%3A1?from=product" rel="sponsored nofollow noopener noreferrer">Shop</a>'
            page=root/'one.html';page.write_text(BASE.format(slug='one',body=valid))
            self.assertEqual(inspect(root)['issues'],[])
            page.write_text(BASE.format(slug='one',body=valid.replace('shop%3A1','unknown')))
            self.assertIn('valid_internal_link',{x['rule'] for x in inspect(root)['issues']})
            page.write_text(BASE.format(slug='one',body=valid.replace('sponsored ','')))
            self.assertIn('commercial_rel_sponsored',{x['rule'] for x in inspect(root)['issues']})
