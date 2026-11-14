"""Read-only real snapshot simulation. No generated production assets are written."""
import copy
import datetime as dt
import gzip
import json
from pathlib import Path
from automation.audit_store_integrity import suppress_commercial_conflicts
from automation.build_product_catalog import build
from automation.update_history import update
ROOT=Path(__file__).resolve().parents[2]

def run():
    catalog=json.loads(gzip.decompress((ROOT/'site/data/catalog.json.gz').read_bytes()))
    cache=json.loads((ROOT/'automation/store-verification-cache.json').read_text())
    now=dt.datetime.fromisoformat(catalog['generated_at'])
    original=copy.deepcopy(catalog)
    published,report=suppress_commercial_conflicts(catalog,cache,now)
    assert catalog==original
    assert published['offers']==[o for o in catalog['offers'] if o['id'] not in {r['id'] for r in report['withheld']}]
    original_by_id={o['id']:o for o in original['offers']}
    assert all(o==original_by_id[o['id']] for o in published['offers'])
    before=build(catalog,now=now);after=build(published,now=now)
    before_by_id={o['id']:o for o in before['offers']}
    assert all((o.get('affiliate_url') or o['url'])==(before_by_id[o['id']].get('affiliate_url') or before_by_id[o['id']]['url']) for o in after['offers'])
    history=json.loads(gzip.decompress((ROOT/'site/data/price-history.json.gz').read_bytes()))
    next_history=update(history,published,now.date().isoformat())
    result={'snapshot_at':catalog['generated_at'],'input_offers':len(catalog['offers']),'published_offers':len(published['offers']),'withheld':[{'id':r['id'],'reasons':r['reasons']} for r in report['withheld']],'raw_fields_unchanged':True,'retained_offer_targets_unchanged':True,'before_metrics':before['metrics'],'after_metrics':after['metrics'],'history_note':'Existing history is not rewritten by suppression; normal update retention and Amazon exclusion remain in existing update_history code.'}
    return result
if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False,indent=2))
