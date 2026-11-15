import copy
import datetime as dt
import io
import json
import unittest
from types import SimpleNamespace

from automation.audit_store_integrity import observe_offer, page_url, fingerprint, suppress_commercial_conflicts, report
from automation.variant_integrity import missing_candidate, verify_missing_variant, valid_missing_proof


class MissingVariantTests(unittest.TestCase):
    def setUp(self):
        self.now = dt.datetime(2026, 11, 15, 12, tzinfo=dt.timezone.utc)
        self.offer = dict(id='bauzaar:1', merchant_id='bauzaar', merchant='Bauzaar',
                          title='Leash Black 2 m', brand='Brand', variant='1ct', price=14.18,
                          available=True, gtin='4006381333931', weight_kg=None,
                          checked_at=self.now.isoformat(),
                          url='https://www.bauzaar.it/products/leash?variant=1',
                          affiliate_url='https://tc.tradetracker.net/?example=unchanged')
        self.variant = dict(id=2, title='Purple 2 m', sku='V2', barcode='9780201379624',
                            price=1799, available=False)
        self.api = dict(id=10, handle='leash', variants=[self.variant])

    def document(self, *, product=10, section='main', path='/products/leash', selected=None,
                 canonical='https://www.bauzaar.it/products/leash', duplicate=False):
        selected = [self.variant] if selected is None else selected
        picker = lambda v: ('<variant-selects data-section="' + section + '" data-url="' + path
                            + '"><script type="application/json" data-selected-variant>'
                            + json.dumps(v) + '</script></variant-selects>')
        main = ('<product-info id="MainProduct-main" data-product-id="' + str(product)
                + '" data-section="main" data-url="/products/leash">'
                + ''.join(picker(v) for v in selected) + '</product-info>')
        return ('<link rel="canonical" href="' + canonical + '">' + main + (main if duplicate else '')
                # A quick-view's selected JSON must not contaminate the main product.
                + '<product-info id="QuickView"><variant-selects data-section="other">'
                + '<script type="application/json" data-selected-variant>{"id":999}</script>'
                + '</variant-selects></product-info>')

    def verify(self, api=None, document=None, **statuses):
        return verify_missing_variant(self.offer, json.dumps(self.api if api is None else api),
                                      self.document() if document is None else document,
                                      api_status=statuses.get('api_status', 200),
                                      document_status=statuses.get('document_status', 200))

    def entry(self):
        return dict(self.verify(), source=page_url(self.offer), checked_at=self.now.isoformat(),
                    fingerprint=fingerprint(self.offer))

    def test_exact_product_api_and_main_selection_corroborate_missing_variant(self):
        result = self.verify(document=self.document(selected=[self.variant, self.variant]))
        self.assertEqual(result['status'], 'verified_missing_variant')
        self.assertEqual(result['evidence']['exact_variant'], '1')
        self.assertTrue(valid_missing_proof(self.offer, result['evidence']))
        self.assertNotIn('price', result['evidence'])
        self.assertNotIn('available', result['evidence'])

    def test_absence_alone_or_truncated_malformed_api_never_confirms(self):
        cap = [dict(self.variant, id=i) for i in range(2, 252)]
        cases = [dict(self.api, variants=[]), dict(self.api, variants=cap),
                 dict(self.api, variants=[self.variant, self.variant]),
                 dict(self.api, variants=[dict(self.variant, id=1)]),
                 dict(self.api, handle='other'), dict(self.api, id=True),
                 dict(self.api, variants=[{}])]
        for api in cases:
            with self.subTest(api=api):
                self.assertIsNone(missing_candidate(self.offer, json.dumps(api)))
                self.assertIsNone(self.verify(api=api))
        self.assertIsNone(self.verify(document='<html>Challenge or generic product page</html>'))

    def test_main_product_identity_selected_fields_and_all_pickers_must_agree(self):
        other = dict(self.variant, id=3)
        api = dict(self.api, variants=[self.variant, other])
        cases = [self.document(product=11), self.document(section='recommendations'),
                 self.document(path='/products/other'), self.document(selected=[]),
                 self.document(selected=[dict(self.variant, id=1)]),
                 self.document(selected=[dict(self.variant, sku='different')]),
                 self.document(selected=[self.variant, other]), self.document(duplicate=True),
                 self.document(canonical='https://evil.test/products/leash')]
        mixed = self.document().replace('</product-info>',
            '<variant-selects data-section="unknown"><script type="application/json" data-selected-variant>'
            + json.dumps(other) + '</script></variant-selects></product-info>', 1)
        cases.extend([mixed, self.document().replace('</variant-selects>', '', 1)])
        for document in cases:
            with self.subTest(document=document):
                self.assertIsNone(self.verify(api=api, document=document))
        # A selected ID appearing only in recommendations cannot supply the missing main proof.
        self.assertIsNone(self.verify(document=self.document(selected=[])))
        for status in [301, 302, 403, 404, 500]:
            self.assertIsNone(self.verify(api_status=status))
            self.assertIsNone(self.verify(document_status=status))

    def test_suppression_preserves_original_fields_and_does_not_select_replacement(self):
        original = copy.deepcopy(self.offer)
        peer = dict(self.offer, id='webpet:5', merchant_id='webpet',
                    url='https://www.webpet.it/products/leash?variant=5')
        catalog = dict(generated_at=self.now.isoformat(), offers=[self.offer, peer])
        published, audit = suppress_commercial_conflicts(catalog, {self.offer['id']: self.entry()}, self.now)
        self.assertEqual(published['offers'], [peer])
        self.assertEqual(audit['withheld'][0]['offer'], original)
        self.assertEqual(audit['withheld'][0]['reasons'], ['variant_missing'])
        self.assertEqual(self.offer, original)
        self.assertEqual(audit['withheld'][0]['offer']['affiliate_url'], original['affiliate_url'])

    def test_inactive_main_product_and_nested_pickers_cannot_supply_live_selection(self):
        original = self.document()
        for opening, closing in [('<template>', '</template>'), ('<noscript>', '</noscript>'),
                                 ('<div hidden>', '</div>'), ('<div inert>', '</div>'),
                                 ('<div aria-hidden="true">', '</div>'),
                                 ('<div style="display : none !important">', '</div>')]:
            with self.subTest(wrapper=opening):
                self.assertIsNone(self.verify(document=opening + original + closing))
        for attribute in ['hidden', 'inert', 'style="visibility: hidden"', 'aria-hidden="true"']:
            self.assertIsNone(self.verify(document=original.replace('<product-info ', '<product-info ' + attribute + ' ', 1)))
        nested = original.replace('<script type="application/json" data-selected-variant>',
            '<variant-selects data-section="unrelated" data-url="/products/other">'
            '<script type="application/json" data-selected-variant>', 1).replace('</script>', '</script></variant-selects>', 1)
        self.assertIsNone(self.verify(document=nested))

    def test_expired_future_unbound_or_inconclusive_cache_cannot_suppress(self):
        base = self.entry()
        cases = [{}, dict(base, status='inconclusive'), dict(base, status='verified'),
                 dict(base, source='https://www.bauzaar.it/products/other.js'),
                 dict(base, fingerprint='changed'),
                 dict(base, checked_at=(self.now + dt.timedelta(seconds=1)).isoformat()),
                 dict(base, checked_at=(self.now - dt.timedelta(hours=24, seconds=1)).isoformat())]
        for field, value in [('exact_variant', '3'), ('api_url', 'https://evil.test/x.js'),
                             ('document_url', 'https://www.bauzaar.it/products/leash?variant=3'),
                             ('remaining_variant_ids', ['1', '2']), ('document_sha256', ''),
                             ('html_selected_variant_ids', ['1']), ('api_http_status', 403)]:
            e = copy.deepcopy(base); e['evidence'][field] = value; cases.append(e)
        for e in cases:
            with self.subTest(entry=e):
                published, _ = suppress_commercial_conflicts({'offers': [self.offer]}, {self.offer['id']: e}, self.now)
                self.assertEqual(published['offers'], [self.offer])
        changed = dict(self.offer, price=15)
        self.assertEqual(suppress_commercial_conflicts({'offers': [changed]}, {changed['id']: base}, self.now)[0]['offers'], [changed])
        wrong_url = dict(self.offer, url='https://www.bauzaar.it/products/leash?variant=3')
        self.assertFalse(valid_missing_proof(wrong_url, base['evidence']))
        self.assertIsNone(missing_candidate(wrong_url, json.dumps(self.api)))

    def checker(self, *, blocked=(), failure=None, document_status=200, api=None):
        calls = []
        class Response(io.BytesIO):
            def __init__(self, body, status):
                super().__init__(body.encode()); self.code = status
            def getcode(self): return self.code
        def open_request(request, timeout):
            calls.append(request.full_url)
            if request.full_url == self.offer['url']:
                if failure: raise failure
                return Response(self.document(), document_status)
            return Response(json.dumps(self.api if api is None else api), 200)
        return SimpleNamespace(allowed=lambda url: url not in blocked,
                               opener=SimpleNamespace(open=open_request)), calls

    def test_collector_uses_one_additional_robots_allowed_document_only_when_needed(self):
        checker, calls = self.checker()
        result = observe_offer(self.offer, checker, self.now)
        self.assertEqual(result['status'], 'verified_missing_variant')
        self.assertEqual(calls, [page_url(self.offer), self.offer['url']])
        for kwargs, expected_count in [({'blocked': [page_url(self.offer)]}, 0),
                                       ({'blocked': [self.offer['url']]}, 1),
                                       ({'api': dict(self.api, variants=[dict(self.variant, id=1)])}, 1),
                                       ({'api': dict(self.api, variants=[dict(self.variant, id=i) for i in range(2, 252)])}, 1)]:
            checker, calls = self.checker(**kwargs); result = observe_offer(self.offer, checker, self.now)
            self.assertNotEqual(result['status'], 'verified_missing_variant')
            self.assertEqual(len(calls), expected_count)

    def test_cached_variant_ids_require_one_canonical_string_representation(self):
        base = self.entry()
        for ids, selected in [([1], [1]), ([2], [2]), (['2', 3], ['2']),
                              ([True], [True]), (['02'], ['02']),
                              (['2', '02'], ['2']), (['2', '2'], ['2']),
                              (['2'], [2]), (['1', '2'], ['1'])]:
            e = copy.deepcopy(base)
            e['evidence'].update(remaining_variant_ids=ids, html_selected_variant_ids=selected)
            with self.subTest(ids=ids, selected=selected):
                self.assertFalse(valid_missing_proof(self.offer, e['evidence']))
                published, _ = suppress_commercial_conflicts({'offers': [self.offer]}, {self.offer['id']: e}, self.now)
                self.assertEqual(published['offers'], [self.offer])
        for value in ('02', True, 2.0):
            api = dict(self.api, variants=[dict(self.variant, id=value)])
            self.assertIsNone(missing_candidate(self.offer, json.dumps(api)))

    def test_document_network_error_or_redirect_status_remains_inconclusive(self):
        for kwargs in [dict(failure=TimeoutError()), dict(document_status=302), dict(document_status=403)]:
            checker, _ = self.checker(**kwargs)
            result = observe_offer(self.offer, checker, self.now)
            self.assertEqual(result['status'], 'inconclusive')
            self.assertEqual(result['discrepancies'], [])

    def test_report_counts_confirmed_absence_as_verified_discrepancy(self):
        result = report({'offers': [self.offer], 'generated_at': self.now.isoformat()},
                        {self.offer['id']: self.entry()}, self.now)
        store = next(x for x in result['stores'] if x['id'] == 'bauzaar')
        self.assertEqual((store['sample_verified'], store['sample_inconclusive'], store['sample_discrepancies']), (1, 0, 1))


if __name__ == '__main__':
    unittest.main()
