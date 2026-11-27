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


def _verify_active(manifest,catalog=None,now=None):
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


def identity_snapshot_fingerprint(catalog):
    rows={o['id']:observation_fingerprint(o) for o in catalog['offers']}
    assert len(rows)==len(catalog['offers']), 'Duplicate catalog offer ID'
    return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def review_plan(manifest,catalog=None,now=None):
    """An explicit archive is not permission to ignore a changed observation.

    Present pairs keep the exact existing gate. Historical evidence is checked
    at the archive date; a returning complete pair must pass it at today's date.
    This is a test/review policy, never a production identity resolver or hold.
    """
    import copy
    import re
    now=now or dt.datetime.now(dt.timezone.utc)
    dormant=manifest.get('dormant_joins',[])
    assert isinstance(dormant,list), 'Invalid dormant archive'
    effective=copy.deepcopy(manifest);effective.pop('dormant_joins',None)
    if not dormant:return {'manifest':effective,'dormant_states':[]}
    assert manifest.get('schema_version')==3, 'Dormant archive requires schema3'
    assert catalog is not None, 'Dormant archive requires a real input catalog'
    rows={o['id']:o for o in catalog['offers']}
    assert len(rows)==len(catalog['offers']), 'Duplicate catalog offer ID'
    seen_pairs=set();seen_sources=set()
    for pair in manifest['joins']:
        assert isinstance(pair,list) and len(pair)==2 and len(set(pair))==2, 'Invalid active join'
        assert frozenset(pair) not in seen_pairs and pair[0] not in seen_sources, 'Duplicate active pair/source'
        seen_pairs.add(frozenset(pair));seen_sources.add(pair[0])
    states=[];identity_digest=None
    for entry in dormant:
        assert isinstance(entry,dict), 'Invalid dormant record'
        pair=entry.get('join')
        assert isinstance(pair,list) and len(pair)==2 and all(isinstance(x,str) and x for x in pair) and len(set(pair))==2, 'Invalid dormant join'
        assert frozenset(pair) not in seen_pairs and pair[0] not in seen_sources, 'Duplicate/overlapping dormant pair/source'
        seen_pairs.add(frozenset(pair));seen_sources.add(pair[0])
        assert isinstance(entry.get('reason'),str) and 15<=len(entry['reason'])<=2000, 'Explicit dormant reason required'
        archived=dt.datetime.fromisoformat(entry['archived_at'].replace('Z','+00:00'))
        assert archived.tzinfo and archived<=now, 'Future/naive archive date'
        snapshot=entry['input_snapshot'];generated=dt.datetime.fromisoformat(snapshot['generated_at'].replace('Z','+00:00'))
        assert generated.tzinfo and generated<=archived, 'Invalid archived snapshot date'
        assert re.fullmatch(r'[0-9a-f]{40}',snapshot.get('commit','')), 'Archived input commit required'
        assert re.fullmatch(r'[0-9a-f]{64}',snapshot.get('identity_snapshot_sha256','')), 'Archived identity snapshot digest required'
        missing=entry['missing_offer_ids']
        assert isinstance(missing,list) and missing and len(set(missing))==len(missing) and set(missing)<=set(pair), 'Explicit archived absences required'
        historical=entry['archived_review']
        assert historical.get('join')==pair, 'Archived review pair differs'
        assert all(re.fullmatch(r'[0-9a-f]{64}',source.get('source_sha256','')) for source in historical.get('sources',[])), 'Archived source body digest required'
        reviewer=entry.get('archived_reviewer')
        assert isinstance(reviewer,str) and reviewer.strip(), 'Archived reviewer required'
        single={'joins':[pair],'merchant_review':{'status':'verified','reviewer':reviewer,'evidence':[historical]}}
        _verify_active(single,None,archived)
        if catalog.get('generated_at')==snapshot['generated_at']:
            if identity_digest is None:identity_digest=identity_snapshot_fingerprint(catalog)
            assert identity_digest==snapshot['identity_snapshot_sha256'], 'Archived input identity digest differs'
        current_missing=[oid for oid in pair if oid not in rows]
        if current_missing:
            assert set(current_missing)==set(missing), 'Dormant absence set changed; explicit review/update required'
            for source in historical['sources']:
                oid=source['offer_id']
                if oid in rows:
                    assert observation_fingerprint(rows[oid])==source['identity_observation_sha256'], 'Dormant present observation changed: '+oid
                    verify_source_url(source,rows[oid])
            states.append({'join':pair,'state':'dormant_absent','missing_offer_ids':current_missing,'archived_at':entry['archived_at']})
        else:
            # Presence is never a wildcard: both fingerprints, URLs, sources and
            # the original30-day review validity are checked before reactivation.
            _verify_active(single,catalog,now)
            effective['joins'].append(copy.deepcopy(pair))
            effective['merchant_review']['evidence'].append(copy.deepcopy(historical))
            states.append({'join':pair,'state':'returned_unchanged_review_valid','missing_offer_ids':[],'archived_at':entry['archived_at']})
    return {'manifest':effective,'dormant_states':states}


def verify(manifest,catalog=None,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    plan=review_plan(manifest,catalog,now)
    _verify_active(plan['manifest'],catalog,now)
    return plan

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    catalog=json.loads(gzip.decompress((root/'site/data/catalog.json.gz').read_bytes()))
    verify(json.loads(Path(__file__).with_name('matching-join-manifest.json').read_text()),catalog)
    print('All explicit joins have independent merchant review evidence')
