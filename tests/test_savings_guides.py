import datetime as dt
import json
import re
import unittest
from automation.build_savings_guides import food_examples, food_content, litter_examples, document, pack_content, shipping_content, observed_examples, history_content, identity_examples, identity_content


class SavingsGuidesTests(unittest.TestCase):
    def setUp(self):
        self.now=dt.datetime.now(dt.timezone.utc)
        # Synthetic fixtures used only in tests, never written as public offers.
        self.o=dict(id='a',merchant_id='a',merchant='Shop A',brand='Brand',title='Food cane',category='Crocchette cani',price=12,weight_kg=2,available=True,url='https://example.com/product',checked_at=self.now.isoformat(),gtin='4006381333931')

    def test_manual_ration_is_explicit_and_price_math_uses_actual_net_weight(self):
        html=food_content([self.o],self.now)
        self.assertIn('6,00 €/kg',html);self.assertIn('1,50 €',html);self.assertIn('45,00 €',html)
        self.assertIn('Non è una razione consigliata',html);self.assertIn('spedizione esclusa',html)
        self.assertIn(self.o['url'],html)

    def test_stale_missing_weight_medical_and_unavailable_examples_are_not_used(self):
        for patch in [dict(checked_at='2020-01-01T00:00:00Z'),dict(weight_kg=None),dict(weight_kg=float('nan')),dict(title='Dieta veterinaria cane'),dict(available=False),dict(price=-3)]:
            self.assertEqual(food_examples([self.o|patch],self.now),[])
        html=food_content([],self.now);self.assertNotIn('<tr>',html)

    def test_litter_comparison_requires_exact_code_brand_and_net_quantity(self):
        a=self.o|dict(title='Lettiera 2 kg',category='Lettiera');b=a|dict(id='b',merchant_id='b',merchant='Shop B')
        self.assertEqual(len(litter_examples([a,b],self.now)),1)
        for patch in [dict(weight_kg=3),dict(gtin=''),dict(brand='Other'),dict(weight_kg=None)]:
            self.assertEqual(litter_examples([a,b|patch],self.now),[])

    def test_article_metadata_and_visible_breadcrumb_correspond(self):
        html=document('<html><head><title>Method</title></head><body><main></main></body></html>','sample','Title','Description','<h2>Content</h2>',self.now)
        data=json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',html)[1])
        article=data['@graph'][0];self.assertEqual(article['headline'],'Title')
        self.assertNotIn('datePublished',article);self.assertEqual(article['author']['@type'],'Organization')
        self.assertIn('guide-risparmio.html',html)

    def test_pack_comparison_keeps_tracking_and_does_not_fill_unknown_weight(self):
        offer=self.o|dict(affiliate_url='https://example.com/tracked')
        html=pack_content([offer],self.now)
        self.assertIn('6,00 €/kg',html)
        self.assertIn('https://example.com/tracked',html)
        self.assertIn('sponsored',html)
        self.assertIn('ricette differenti',html)
        self.assertNotIn('<table',pack_content([offer|dict(weight_kg=None)],self.now))

    def shipping_fixture(self, **patch):
        rule={'name':'A','fee':5.9,'note':'Soglia esatta ambigua: totale ignoto; Bauzaar massimo 35 kg con peso noto.',
              'source':'https://example.com/shipping',
              'checked_at':(self.now-dt.timedelta(days=20)).isoformat(),
              'verified_until':(self.now+dt.timedelta(seconds=1)).isoformat(),**patch}
        return {'merchants':{'a':rule},'scope':'Esclusi isole, CAP disagiati, Punto Poste e Fermopoint BRT.'}

    def test_shipping_date_and_timestamp_forms_use_aware_instants(self):
        for checked in ['2026-11-01','2026-11-01T00:00:00Z','2026-11-01T01:00:00+01:00']:
            rules=self.shipping_fixture(checked_at=checked,verified_until='2026-12-05T11:31:55+01:00')
            html=shipping_content([],dt.datetime(2026,11,7,tzinfo=dt.timezone.utc),rules)
            self.assertIn('<caption>',html)
            self.assertIn('https://example.com/shipping',html)

    def test_shipping_expiry_is_per_merchant_and_precise_to_the_second(self):
        for delta,shown in [(-1,False),(0,False),(1,True)]:
            rules=self.shipping_fixture(verified_until=(self.now+dt.timedelta(seconds=delta)).isoformat())
            html=shipping_content([],self.now,rules)
            self.assertEqual('<caption>' in html,shown)
        rules=self.shipping_fixture()
        rules['checked_at']='not-a-date'
        self.assertIn('<caption>',shipping_content([],self.now,rules),'A current per-shop verification overrides global metadata')

    def test_invalid_missing_expired_and_conflicting_shipping_stays_unknown(self):
        for patch in [{'checked_at':'bad'},{'verified_until':'bad'},{'verified_until':None},
                      {'checked_at':(self.now+dt.timedelta(days=1)).isoformat()},
                      {'conflict':True},{'status':'unknown'},{'fee':None}]:
            with self.subTest(patch=patch):
                self.assertNotIn('<table',shipping_content([],self.now,self.shipping_fixture(**patch)))
        self.assertNotIn('<table',shipping_content([],self.now,{'merchants':{}}))

    def test_shipping_table_excludes_invalid_shops_and_preserves_conditions(self):
        rules=self.shipping_fixture()
        rules['merchants']['animaliapet']={**rules['merchants']['a'],'name':'Animaliapet','conflict':True}
        html=shipping_content([],self.now,rules)
        self.assertIn('<caption>',html)
        self.assertIn('data-shipping-merchant="a"',html)
        self.assertNotIn('data-shipping-merchant="animaliapet"',html)
        self.assertNotIn('data-shipping-merchant="hygge"',html)
        for text in ['Soglia esatta ambigua','35 kg','peso noto','Punto Poste','Fermopoint BRT','totale resta ignoto']:
            self.assertIn(text,html)
        self.assertNotIn('sette giorni',html)

    def test_history_counts_real_days_and_rejects_changed_identity_and_bad_rows(self):
        import hashlib
        fingerprint=hashlib.sha256(json.dumps([self.o.get(k) for k in ('merchant_id','title','variant','brand','gtin','weight_kg')],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        day=self.now.date().isoformat()
        record={'day':day,'low':10,'last':12,'high':14}
        history={'identities':{'a':fingerprint},'offers':{'a':[record,record|{'low':9},{'day':'2099-01-01','low':1,'last':1,'high':1},record|{'low':-4},record|{'high':8}]}}
        example=observed_examples([self.o],self.now,history)[0][1]
        self.assertEqual(example['days'],1)
        self.assertEqual(example['low'],9)
        self.assertEqual(example['high'],14)
        self.assertEqual(observed_examples([self.o|{'variant':'New recipe'}],self.now,history),[])
        self.assertNotIn('<table',history_content([self.o],self.now,{}))
        html=history_content([self.o],self.now,history)
        self.assertIn('9,00 €',html)
        self.assertIn(day,html)

    def test_identity_guide_requires_exact_format_and_keeps_product_clicks_internal(self):
        other=self.o|dict(id='b',merchant_id='b',merchant='Shop B',affiliate_url='https://example.com/tracked')
        self.assertEqual(len(identity_examples([self.o,other],self.now)),1)
        html=identity_content([self.o,other],self.now)
        self.assertIn('4006381333931',html)
        self.assertNotIn('https://example.com/tracked',html)
        self.assertNotIn('href="https://example.com/product"',html)
        self.assertIn('spedizione esclusa',html)
        # The guide keeps both product-title clicks inside the exact-format comparison.
        # The comparison page itself retains any authorized merchant affiliate URLs.
        from automation.build_matched_pages import slug_for
        key=identity_examples([self.o,other],self.now)[0][0]
        self.assertIn(slug_for(key)+'.html',html)
        self.assertEqual(html.count('href="'+slug_for(key)+'.html"'),3)
        self.assertIn('Apri il confronto aggiornato fra negozi',html)
        self.assertIn('2,00 €',identity_content([self.o,other|{'price':14}],self.now))
        self.assertIn('non è un risparmio garantito al checkout',html)
        for patch in [dict(gtin='4006381333932'),dict(weight_kg=3),dict(brand='Other'),dict(available=False),dict(checked_at='2020-01-01T00:00:00Z')]:
            self.assertEqual(identity_examples([self.o,other|patch],self.now),[])
            self.assertNotIn('<table',identity_content([self.o,other|patch],self.now))
