import datetime as dt
import unittest
from automation.build_product_catalog import build,clean_title,quantity

class CanonicalProductTests(unittest.TestCase):
    def setUp(self):
        self.now=dt.datetime(2026,10,28,12,tzinfo=dt.timezone.utc)
        self.a=dict(id='a:1',merchant_id='a',merchant='A',title='Acana - Acana Adult 2 kg',variant='2 kg',brand='Acana',price=20,available=True,gtin='4006381333931',weight_kg=2,checked_at=self.now.isoformat(),url='https://shop.test/a')
    def model(self,rows,old=None):return build({'offers':rows,'generated_at':self.now.isoformat()},old,now=self.now)
    def test_gtin_and_selling_quantity_define_product_not_price_or_shop(self):
        b=dict(self.a,id='b:1',merchant_id='b',merchant='B',price=18,gtin='04006381333931')
        m=self.model([self.a,b]);self.assertEqual(len(m['products']),1);self.assertEqual(m['metrics']['multi_shop_products'],1)
        p=m['products'][0];self.assertEqual(p['active_shop_count'],2);self.assertEqual(p['name'],'Acana Adult 2 kg')
        self.assertEqual({o['product_id'] for o in m['offers']},{p['id']})
        b['price']=17;b['title']='Acana Adult Cane 2 kg'
        second=self.model([self.a,b],m['registry']);self.assertEqual(second['products'][0]['slug'],p['slug'])
    def test_single_store_multiple_offers_is_not_a_multishop_comparison(self):
        m=self.model([self.a,dict(self.a,id='a:2')]);self.assertEqual(m['metrics']['multi_shop_products'],0)
        self.assertEqual(m['products'][0]['verified_shop_count'],1)
    def test_missing_gtin_and_different_formats_are_never_fuzzy_merged(self):
        rows=[self.a,dict(self.a,id='b:1',merchant_id='b',gtin=''),dict(self.a,id='c:1',merchant_id='c',weight_kg=4)]
        self.assertEqual(len(self.model(rows)['products']),3)
    def test_unknown_merchant_quantity_never_acquires_unit_price(self):
        row=dict(self.a,quantity_verified=False);m=self.model([row]);self.assertIsNone(m['offers'][0]['unit_price'])
        self.assertEqual(m['products'][0]['matching_method'],'unattached')
    def test_titles_and_explicit_volume_pieces(self):
        self.assertEqual(clean_title('Mousse 85 g 85 gr - Cibo umido per gatti'),'Mousse 85 g')
        self.assertEqual(quantity(dict(title='Lettiera 6 x 5 l'))['volume_ml'],30000)
        self.assertEqual(quantity(dict(title='Snack 12 pezzi'))['pieces'],12)
        self.assertIsNone(quantity(dict(title='Lettiera 5 l / 10 l'))['volume_ml'])
    def test_stale_and_sold_out_do_not_inflate_metric(self):
        b=dict(self.a,id='b:1',merchant_id='b',available=False)
        self.assertEqual(self.model([self.a,b])['products'][0]['active_shop_count'],1)

    def test_capacity_is_not_misrepresented_as_consumable_volume(self):
        self.assertIsNone(quantity(dict(title='Ciotola in acciaio 500 ml'))['volume_ml'])
        self.assertIsNone(quantity(dict(title='Acquario 100 l'))['volume_ml'])
        self.assertEqual(quantity(dict(title='Shampoo per cani 250 ml'))['volume_ml'],250)
        self.assertEqual(quantity(dict(title='Lettiera 36 L (6 confezioni da 6 litri)'))['volume_ml'],36000)

    def test_observed_history_and_retired_products_keep_identity(self):
        catalog={'offers':[self.a],'generated_at':self.now.isoformat()}
        history={'offers':{'a:1':[{'day':'2026-10-27','low':19,'high':21,'last':20,'available':True}]}}
        first=build(catalog,history=history,now=self.now)
        self.assertEqual(first['products'][0]['history'][0]['sum'],20)
        retired=build({'offers':[],'generated_at':self.now.isoformat()},first['registry'],now=self.now)
        self.assertEqual(retired['products'][0]['id'],first['products'][0]['id'])
        self.assertEqual(retired['products'][0]['active_offer_count'],0)

    def test_explicit_brand_line_aliases_need_same_gtin_and_quantity(self):
        a=dict(self.a,brand='Royal Canin Veterinary Diet')
        b=dict(self.a,id='b:1',merchant_id='b',brand='Royal Canin')
        self.assertEqual(self.model([a,b])['metrics']['multi_shop_products'],1)
        for extra in [{'brand':'Unrelated Royal Canin imitation'},{'weight_kg':4},{'gtin':''}]:
            self.assertEqual(self.model([a,dict(b,**extra)])['metrics']['multi_shop_products'],0)
        # Corporate ownership alone is not an alias.
        self.assertEqual(self.model([dict(a,brand='Askoll'),dict(b,brand='Ciano')])['metrics']['multi_shop_products'],0)

    def test_brand_merge_preserves_existing_urls_with_unambiguous_redirect(self):
        from unittest.mock import patch
        a=dict(self.a,brand='Royal Canin Veterinary Diet')
        b=dict(self.a,id='b:1',merchant_id='b',brand='Royal Canin')
        with patch('automation.build_product_catalog.BRAND_ALIASES',{}):old=self.model([a,b])
        new=self.model([a,b],old['registry'])
        current=next(p for p in new['products'] if p['active_offer_count'])
        retired=next(p for p in new['products'] if not p['active_offer_count'])
        self.assertEqual(retired['redirect_slug'],current['slug'])
        self.assertEqual(current['slug'],next(p['slug'] for p in old['products'] if p['brand']=='Royal Canin'))
        missing=self.model([b],old['registry'])
        self.assertNotIn('redirect_slug',next(p for p in missing['products'] if not p['active_offer_count']))
        self.assertEqual(new['metrics']['store_coverage']['b']['offers_in_multishop_products'],1)

    def test_full_catalog_name_matching_has_provenance_and_no_fake_gtin(self):
        a=dict(self.a,title='Acana Heritage Prairie Poultry Adult 2 kg',variant='',gtin='')
        b=dict(a,id='b:1',merchant_id='b',price=18)
        m=self.model([a,b]);p=m['products'][0]
        self.assertEqual(len(m['products']),1)
        self.assertEqual(p['matching_method'],'name_characteristics')
        self.assertEqual(p['gtin'],'');self.assertIsNone(p['matching_confidence']);self.assertTrue(p['indexable'])
        self.assertEqual(m['metrics']['name_matching']['evaluated_offers'],2)
        self.assertEqual(m['metrics']['characteristic_multi_shop_products'],1)
        self.assertTrue(all(o['offer_matching_method']=='name_characteristics' and not o['gtin'] for o in m['offers']))

    def test_name_fallback_rejects_recipe_age_format_and_unknown_quantity(self):
        a=dict(self.a,title='Acana Heritage Prairie Poultry Adult 2 kg',variant='',gtin='')
        for extra in [dict(title='Acana Heritage Prairie Poultry Puppy 2 kg'),dict(title='Acana Heritage Wild Salmon Adult 2 kg'),dict(weight_kg=4),dict(quantity_verified=False),dict(brand='Other')]:
            m=self.model([a,dict(a,id='b:1',merchant_id='b',**extra)])
            self.assertEqual(m['metrics']['multi_shop_products'],0)
        generic=dict(a,title='Acana Adult Pollo 2 kg')
        self.assertEqual(self.model([generic,dict(generic,id='b:1',merchant_id='b')])['metrics']['multi_shop_products'],0)

    def test_translated_tokens_keep_recipe_and_life_stage_distinct(self):
        a=dict(self.a,title='Acana Heritage Prairie Chicken Adult Dog 2 kg',variant='',gtin='')
        b=dict(a,id='b:1',merchant_id='b',title='Acana Heritage Prairie Pollo Adulto Cane 2 kg')
        self.assertEqual(self.model([a,b])['metrics']['multi_shop_products'],1)
        for title in ['Acana Heritage Prairie Agnello Adulto Cane 2 kg',
                      'Acana Heritage Prairie Pollo Puppy Cane 2 kg',
                      'Acana Heritage Prairie Pollo Adulto Gatto 2 kg']:
            self.assertEqual(self.model([a,dict(b,title=title)])['metrics']['multi_shop_products'],0)

    def test_specific_short_line_matches_without_relaxing_generic_names(self):
        a=dict(self.a,title='Vitakraft Strisce Prosciutto 80 g',brand='Vitakraft',variant='',gtin='',weight_kg=.08)
        b=dict(a,id='b:1',merchant_id='b',title='Vitakraft Strisce 80 g Prosciutto')
        self.assertEqual(self.model([a,b])['metrics']['multi_shop_products'],1)
        self.assertEqual(self.model([a,dict(b,title='Vitakraft Strisce Coniglio 80 g')])['metrics']['multi_shop_products'],0)

    def test_missing_gtin_does_not_bridge_conflicting_valid_gtins(self):
        a=dict(self.a,title='Acana Heritage Prairie Poultry Adult 2 kg',variant='')
        b=dict(a,id='b:1',merchant_id='b',gtin='5901234123457')
        c=dict(a,id='c:1',merchant_id='c',gtin='')
        m=self.model([a,b,c]);self.assertEqual(m['metrics']['multi_shop_products'],0)
        self.assertEqual(m['metrics']['name_matching']['conflicting_gtin_groups'],1)

    def test_missing_gtin_attaches_to_unique_known_identity_without_inheriting_code(self):
        a=dict(self.a,title='Acana Heritage Prairie Poultry Adult 2 kg',variant='')
        b=dict(a,id='b:1',merchant_id='b',gtin='')
        before=self.model([a]);m=self.model([a,b],before['registry'])
        self.assertEqual(m['products'][0]['slug'],before['products'][0]['slug'])
        self.assertEqual(m['products'][0]['matching_method'],'gtin_with_name')
        self.assertEqual(next(o for o in m['offers'] if o['id']=='b:1')['gtin'],'')

    def test_licensed_image_is_shared_only_inside_the_same_product_identity(self):
        from unittest.mock import patch
        from automation.image_policy import feed_image
        image='https://images.test/exact-2kg.png';local='/img/p/'+'a'*24+'-400.webp'
        a=self.a|dict(image=image,image_local=local,source_type='official_feed',affiliate_url='https://tc.tradetracker.net/?c=16143&a=518044',image_source=feed_image(image,16143,600171))
        b=self.a|dict(id='b:1',merchant_id='b',image='https://other.test/food.png')
        rule={'allow_cache':True,'permission_status':'verified','scope':'approved_feed_assets','campaign_id':16143,'feed_id':600171,'evidence':'https://license.test'}
        with patch('automation.build_product_catalog.IMAGE_RULES',{'a':rule}):
            model=self.model([a,b]);self.assertEqual(len(model['products']),1)
            self.assertEqual(model['products'][0]['image_local'],local)
            self.assertEqual({o['image_local'] for o in model['offers']},{local})
            split=self.model([a,b|{'weight_kg':4}]);self.assertNotIn('image_local',next(o for o in split['offers'] if o['id']=='b:1'))
            changed=self.model([a|{'image':'https://images.test/replaced.png'},b]);self.assertTrue(all('image_local' not in o for o in changed['offers']))

    def test_liter_prices_require_explicit_consistent_per_offer_sources(self):
        cat=dict(self.a,title="Cat's Best Original lettiera 7lt / 3Kg",brand="Cat's Best",variant='3kg',weight_kg=3,price=8.12)
        m=self.model([cat]);o=m['offers'][0]
        self.assertEqual(o['quantity']['volume_source'],'title')
        self.assertEqual(o['unit_prices']['l'],1.16)
        self.assertEqual(m['products'][0]['format'],'3 kg')
        for changed in [dict(title="Cat's Best Original lettiera 3kg"),dict(variant='10 l'),dict(title="Cat's Best Original lettiera 7l / 10l"),dict(quantity_verified=False),dict(weight_conflict=True)]:
            row=self.model([dict(cat,**changed)])['offers'][0]
            self.assertNotIn('l',row['unit_prices'])
            self.assertIsNone(row['quantity']['volume_source'])
        agreed=self.model([dict(cat,variant='7 l')])['offers'][0]
        self.assertEqual(agreed['quantity']['volume_source'],'title_and_variant')
        self.assertEqual(agreed['unit_prices']['l'],1.16)

    def test_volume_provenance_preserves_product_identity_registry_slug_and_history(self):
        from automation.build_product_catalog import identity,format_label
        import hashlib,json
        cat=dict(self.a,title="Cat's Best Original lettiera 7lt / 3Kg",brand="Cat's Best",variant='3kg',weight_kg=3)
        q=quantity(cat);old_q={k:v for k,v in q.items() if k!='volume_source'}
        self.assertEqual(identity(cat,q),identity(cat,old_q))
        self.assertEqual(format_label(q),format_label(old_q))
        first=self.model([cat]);p=first['products'][0]
        expected='p-'+hashlib.sha256(json.dumps(identity(cat,old_q),ensure_ascii=False,separators=(',',':')).encode()).hexdigest()[:20]
        self.assertEqual(p['id'],expected)
        old=first['registry'];old[p['id']]['slug']='historical-stable-catbest-slug'
        history={'offers':{'a:1':[{'day':'2026-10-27','low':19,'high':21,'last':20,'available':True}]}}
        result=build({'offers':[cat],'generated_at':self.now.isoformat()},old,history,now=self.now)
        self.assertEqual(result['products'][0]['id'],p['id'])
        self.assertEqual(result['products'][0]['slug'],'historical-stable-catbest-slug')
        self.assertEqual(result['products'][0]['history'][0]['sum'],20)
