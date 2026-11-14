"""Fail closed: technical identity signatures never substitute merchant review."""
import datetime as dt
import gzip
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit,parse_qsl

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from automation.audit_store_integrity import canonical_gtin


def observation_fingerprint(offer):
    identity={k:offer.get(k) for k in ('id','merchant_id','title','brand','variant','url')}
    # Valid zero-padded GTIN representations are equivalent; malformed values
    # remain distinct instead of silently collapsing to an empty identifier.
    for key in ('gtin','feed_gtin'):
        raw=str(offer.get(key) or '').strip()
        identity[key]=canonical_gtin(raw) or ('invalid:'+raw if raw else '')
    # SKU casing and internal separators are merchant identifiers, not prose.
    identity['sku']=str(offer.get('sku') or '').strip()
    q=offer.get('quantity',{})
    identity['quantity']={k:q.get(k) for k in ('kind','value','unit','weight_g','volume_ml','pieces','verified')}
    return hashlib.sha256(json.dumps(identity,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def verify_source_url(source,offer):
    """Bind evidence to this merchant product and its exact selected variant."""
    observed=urlsplit(source['url']);selling=urlsplit(offer['url'])
    for url in (observed,selling):
        assert url.scheme=='https' and url.hostname and not url.username and not url.password and not url.fragment, 'Unsafe evidence/product URL'
    assert observed.netloc.lower()==selling.netloc.lower(), 'Evidence merchant host differs'
    merchant=offer.get('merchant_id') or offer['id'].split(':',1)[0]
    selected=offer['id'].split(':',1)[1]
    if merchant in ('bauzaar','animaliapet','webpet'):
        assert selling.path.startswith('/products/'), 'Unexpected Shopify product path'
        assert observed.path in (selling.path,selling.path+'.js'), 'Evidence product path differs'
        def variant_query(url):
            pairs=parse_qsl(url.query,keep_blank_values=True)
            assert all(key=='variant' for key,_ in pairs) and len(pairs)<=1, 'Unexpected or duplicate variant query'
            return [value for _,value in pairs]
        assert variant_query(selling)==[selected], 'Selling URL does not select exact offer variant'
        selected_query=variant_query(observed)
        if observed.path.endswith('.js'):
            assert selected_query in ([],[selected]), 'Evidence query selects another variant'
            assert str(source.get('selected_id') or '').strip()==selected, 'API evidence needs exact reviewed variant ID'
        else:
            assert selected_query==[selected], 'HTML evidence does not select exact offer variant'
    else:
        assert observed.path==selling.path and observed.query==selling.query, 'Evidence product URL differs'
        if merchant=='isola-dei-tesori':
            assert selling.path.endswith('/'+selected+'.html'), 'Evidence does not bind exact Isola SKU'
        if source.get('selected_id') is not None:
            assert str(source['selected_id']).strip()==selected, 'Evidence selected identifier differs'


def verify(manifest,catalog=None,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    offers={o['id']:o for o in catalog['offers']} if catalog is not None else None
    review=manifest['merchant_review']
    assert review['status']=='verified', 'Independent merchant review pending; PR not mergeable'
    assert isinstance(review.get('reviewer'),str) and review['reviewer'].strip(), 'Named reviewer required'
    checked={}
    for row in review.get('evidence',[]):
        pair=tuple(row['join'])
        assert pair not in checked, 'Duplicate evidence pair'
        assert row['result']=='same_exact_product_and_selling_pack'
        hosts=set()
        observed=set()
        for source in row['sources']:
            url=urlsplit(source['url']);hosts.add(url.hostname)
            assert url.scheme=='https' and url.hostname and not url.username and not url.password
            stamp=dt.datetime.fromisoformat(source['checked_at'].replace('Z','+00:00'))
            assert stamp.tzinfo and dt.timedelta(0)<=now-stamp<=dt.timedelta(days=30), 'Evidence expired or future dated'
            oid=source.get('offer_id')
            assert oid in pair and oid not in observed, 'Exact source observation required'
            observed.add(oid)
            digest=source.get('identity_observation_sha256','')
            assert len(digest)==64 and all(c in '0123456789abcdef' for c in digest), 'Identity fingerprint required'
            if offers is not None:
                assert oid in offers and observation_fingerprint(offers[oid])==digest, 'Reviewed observation changed: '+oid
                verify_source_url(source,offers[oid])
            for field in ('brand','line','variant','selling_quantity','evidence_excerpt'):
                assert isinstance(source.get(field),str) and source[field].strip(), 'Missing evidence: '+field
        assert len(hosts)>=2, 'Independent merchant sources required'
        assert observed==set(pair), 'Both exact offer observations required'
        checked[pair]=row
    assert set(checked)=={tuple(pair) for pair in manifest['joins']}, 'Every explicit join needs evidence'

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    catalog=json.loads(gzip.decompress((root/'site/data/catalog.json.gz').read_bytes()))
    verify(json.loads(Path(__file__).with_name('matching-join-manifest.json').read_text()),catalog)
    print('All explicit joins have independent merchant review evidence')
