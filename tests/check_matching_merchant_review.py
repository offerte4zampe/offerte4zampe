"""Fail closed: technical identity signatures never substitute merchant review."""
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlsplit


def verify(manifest):
    review=manifest['merchant_review']
    assert review['status']=='verified', 'Independent merchant review pending; PR not mergeable'
    assert isinstance(review.get('reviewer'),str) and review['reviewer'].strip(), 'Named reviewer required'
    checked={}
    for row in review.get('evidence',[]):
        pair=tuple(row['join'])
        assert pair not in checked, 'Duplicate evidence pair'
        assert row['result']=='same_exact_product_and_selling_pack'
        hosts=set()
        for source in row['sources']:
            url=urlsplit(source['url']);hosts.add(url.hostname)
            assert url.scheme=='https' and url.hostname and not url.username and not url.password
            stamp=dt.datetime.fromisoformat(source['checked_at'].replace('Z','+00:00'))
            assert stamp.tzinfo and stamp<=dt.datetime.now(dt.timezone.utc)
            for field in ('brand','line','variant','selling_quantity','evidence_excerpt'):
                assert isinstance(source.get(field),str) and source[field].strip(), 'Missing evidence: '+field
        assert len(hosts)>=2, 'Independent merchant sources required'
        checked[pair]=row
    assert set(checked)=={tuple(pair) for pair in manifest['joins']}, 'Every explicit join needs evidence'

if __name__=='__main__':
    verify(json.loads(Path(__file__).with_name('matching-join-manifest.json').read_text()))
    print('All explicit joins have independent merchant review evidence')
