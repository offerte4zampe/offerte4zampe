"""Offline real-snapshot equivalence gate (no store access, no write to main).

Both worktrees get exactly the compressed catalog checked into main. Only the
diagnostics are added in memory; offers must remain byte-equivalent in JSON.
Six HTML pages are regenerated in both trees and compared byte-for-byte.
"""
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from automation.update_catalog import attach_gtin_diagnostics
PAGES = [
    'site/index.html',
    'site/monge-maxi-adult-pollo.html',
    'site/royal-canin-medium-adult.html',
    'site/pro-plan-large-athletic-agnello.html',
    'site/guide-risparmio.html',
    'site/codici-sconto.html',
]
GENERATORS = [
    'automation/build_product_pages.py',
    'automation/build_savings_guides.py',
    'automation/build_home_data.py',
]

def run(*cmd, cwd=ROOT):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)

def digest(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True,
                                      separators=(',', ':')).encode()).hexdigest()

def main():
    base = run('git','merge-base','origin/main','HEAD').stdout.strip()
    assert base and len(base) == 40
    # The actual main snapshot is required, not a fixture.
    raw = subprocess.check_output(['git','show',base+':site/data/catalog.json.gz'],cwd=ROOT)
    assert raw[:2] == b'\\x1f\\x8b', 'main compressed catalog missing or invalid'
    original = json.loads(gzip.decompress(raw))
    assert isinstance(original['offers'],list) and original['offers']
    assert isinstance(original['sources'],list) and original['sources']
    updated = copy.deepcopy(original)
    for source in updated['sources']:
        rows = [o for o in updated['offers'] if o.get('merchant_id') == source['id']]
        attach_gtin_diagnostics(source,rows)
        metrics = source.get('gtin_diagnostics')
        assert metrics is not None, source['id']
        assert metrics['raw_present'] == metrics['valid'] + metrics['invalid']
        assert len(rows) == metrics['raw_present'] + metrics['empty']
    assert updated['offers'] == original['offers'], 'Offers modified by diagnostics'
    reconstructed=copy.deepcopy(updated)
    for source in reconstructed['sources']:
        source.pop('gtin_diagnostics',None)
    assert reconstructed == original, 'Non-diagnostic catalog metadata changed'
    print('SNAPSHOT_EQUIVALENCE',json.dumps({
        'base_sha':base,'offer_count':len(original['offers']),
        'offers_sha256':digest(original['offers']),
        'source_diagnostics':{
            s['id']:s['gtin_diagnostics'] for s in updated['sources']
        }
    },sort_keys=True))

    with tempfile.TemporaryDirectory(prefix='gtin-compare-') as tmp:
        trees = [Path(tmp)/'main',Path(tmp)/'candidate']
        revisions = [base,'HEAD']
        created=[]
        try:
            for dest,rev in zip(trees,revisions):
                run('git','worktree','add','--detach',str(dest),rev)
                created.append(dest)
                target=dest/'site/data/catalog.json.gz'
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(raw)
                assert target.read_bytes()==raw
                for generator in GENERATORS:
                    run(sys.executable,generator,cwd=dest)
            comparison={}
            for rel in PAGES:
                left=(trees[0]/rel).read_bytes()
                right=(trees[1]/rel).read_bytes()
                assert left == right, 'Different generated HTML: '+rel
                comparison[rel]={'bytes':len(left),'sha256':hashlib.sha256(left).hexdigest()}
            print('HTML_EQUIVALENCE',json.dumps(comparison,sort_keys=True))
        finally:
            for dest in reversed(created):
                subprocess.run(['git','worktree','remove','--force',str(dest)],
                               cwd=ROOT, capture_output=True, text=True)

if __name__=='__main__':
    main()
