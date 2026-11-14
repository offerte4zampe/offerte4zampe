"""Explicit PR99 matching contract; allowed joins are never inferred from head output.

Build base, head with base resolver, and head unchanged. Materialize an independent
explicit-mapper oracle to compare generated artifacts. Merchant review is separate.
"""
import argparse
import copy
import datetime as dt
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'tests/matching-join-manifest.json'
GENERATORS=['automation/build_product_pages.py','automation/build_home_data.py','automation/build_sitemaps.py']
DERIVED={'canonical_shop_count','product_matching_method','product_identity_verified','canonical_title','image_local','image_source_offer','product_slug','product_id','offer_matching_method','product_url'}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def explicit_resolver(original,joins):
    def resolve(offers,quantities,identities,normalize,brand,gtin):
        identities,methods,report=original(offers,quantities,identities,normalize,brand,gtin)
        rows={o['id']:o for o in offers}
        assert len({source for source,_ in joins})==len(joins), 'Duplicate manifest source'
        for source,target in joins:
            a,b=rows[source],rows[target]
            assert a['merchant_id']!=b['merchant_id'], 'Manifest same merchant'
            qa,qb=quantities[source],quantities[target]
            assert qa['verified'] and qb['verified'], 'Manifest unverified quantity'
            assert tuple(qa.get(k) for k in ('weight_g','volume_ml','pieces'))==tuple(qb.get(k) for k in ('weight_g','volume_ml','pieces')), 'Manifest quantity conflict'
            assert normalize(brand(a.get('brand','')))==normalize(brand(b.get('brand',''))), 'Manifest brand conflict'
            ac,bc=gtin(a.get('gtin')),gtin(b.get('gtin'))
            if identities[source]==identities[target]:
                assert bc and (not ac or ac==bc), 'Previously satisfied manifest has conflicting/missing GTIN'
                continue
            assert not ac and bc, 'New manifest join requires missing source GTIN and valid target GTIN'
            identities[source]=copy.deepcopy(identities[target]);methods[source]='name_characteristics'
        return identities,methods,report
    return resolve


def verify_merchant_fields(base,actual):
    left,right=({o['id']:o for o in m['offers']} for m in (base,actual))
    assert len(left)==len(base['offers']) and len(right)==len(actual['offers']), 'Duplicate offer ID'
    assert left.keys()==right.keys(), 'Offer IDs changed'
    for oid in left:
        a={k:v for k,v in left[oid].items() if k not in DERIVED}
        b={k:v for k,v in right[oid].items() if k not in DERIVED}
        assert fingerprint(a)==fingerprint(b), 'Merchant fingerprint changed: '+oid
    return left,right


def verify_models(base,actual,expected,joins):
    left,right=verify_merchant_fields(base,actual)
    moved={i for i in left if left[i]['product_id']!=right[i]['product_id']}
    expected_moved={source for source,target in joins if left[source]['product_id']!=left[target]['product_id']}
    assert moved==expected_moved, 'Unexpected identity delta: '+json.dumps({'actual':sorted(moved),'expected':sorted(expected_moved)})
    for field in ('offers','products','registry'):
        assert actual[field]==expected[field], 'Explicit mapper output mismatch: '+field
    for p in actual['products']:
        assert not p['indexable'] or p['verified_shop_count']>=2, 'Indexable without two verified shops'
    return {'offers':len(left),'exact_identity_moves':len(moved),'expected_offers_fingerprint':fingerprint(expected['offers']),'expected_products_fingerprint':fingerprint(expected['products'])}


def files(root):
    site=root/'site';paths=list(site.rglob('*.html'))+list(site.glob('sitemap*.xml'))
    for folder in ('canonical-products','canonical-routes'):paths+=list((site/'data'/folder).glob('*.json'))
    paths += [site/'data/canonical-sitemap.json',site/'data/canonical-route-list.json',site/'_redirects']
    return {str(p.relative_to(site)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def worker_build(root,base_resolver,joins):
    sys.path.insert(0,str(root))
    from automation import build_product_catalog as module
    from automation import name_matching
    if base_resolver:
        spec=importlib.util.spec_from_file_location('automation._contract_base_name_matching',base_resolver)
        old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        name_matching.resolve=explicit_resolver(old.resolve,joins)
    catalog=json.loads(gzip.decompress((root/'site/data/catalog.json.gz').read_bytes()))
    registry=json.loads((root/'automation/product-registry.json').read_text())
    model=module.build(catalog,registry,now=dt.datetime.fromisoformat(catalog['generated_at']))
    module.write(model,root/'site')
    (root/'automation/product-registry.json').write_text(json.dumps(model['registry'],ensure_ascii=False,separators=(',',':'))+'\n')
    catalog['offers']=model['offers']
    (root/'site/data/catalog.json.gz').write_bytes(gzip.compress(json.dumps(catalog,ensure_ascii=False,separators=(',',':')).encode(),mtime=0))
    (root/'contract-model.json.gz').write_bytes(gzip.compress(json.dumps(model).encode(),mtime=0))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--base-ref',default='origin/main');parser.add_argument('--output',default='matching-contract-result.json')
    parser.add_argument('--worker');parser.add_argument('--base-resolver');parser.add_argument('--manifest',default=str(MANIFEST))
    args=parser.parse_args();manifest=json.loads(Path(args.manifest).read_text());joins=manifest['joins']
    if args.worker:worker_build(Path(args.worker),args.base_resolver,joins);return
    def git(*cmd):return subprocess.check_output(['git',*cmd],cwd=ROOT,text=True).strip()
    base=git('rev-parse',args.base_ref);head=git('rev-parse','HEAD');trees=[]
    output=Path(args.output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    output.unlink(missing_ok=True)
    initial={'base_sha':base,'head_sha':head,'merchant_review':manifest['merchant_review']['status'],'merge_ready':False}
    with tempfile.TemporaryDirectory(prefix='matching-contract-') as temp:
        tmp=Path(temp)
        try:
            for name,rev in [('base',base),('common',head),('actual',head),('expected',head)]:
                dest=tmp/name;git('worktree','add','--quiet','--detach',str(dest),rev);trees.append(dest)
            base_tree,common,actual,expected=trees
            shutil.copyfile(base_tree/'automation/name_matching.py',common/'automation/name_matching.py')
            inputs=['site/data/catalog.json.gz','site/data/price-history.json.gz','automation/product-registry.json']
            for p in inputs:assert len({(tree/p).read_bytes() for tree in trees})==1, 'Input snapshot differs: '+p
            assert files(base_tree)==files(actual), 'Static input HTML/sitemap/shards differ'
            catalog=json.loads(gzip.decompress((base_tree/inputs[0]).read_bytes()))
            input_rows={o['id']:o for o in catalog['offers']}
            initial['manifest_offer_status']=[{'source':source,'target':target,'source_gtin':input_rows[source].get('gtin'),'target_gtin':input_rows[target].get('gtin'),'source_product_id':input_rows[source].get('product_id'),'target_product_id':input_rows[target].get('product_id')} for source,target in joins]
            clock=tmp/'clock';clock.mkdir()
            (clock/'sitecustomize.py').write_text('import datetime as d,os\nr=d.datetime\nclass F(r):\n @classmethod\n def now(cls,tz=None):\n  x=r.fromisoformat(os.environ["MATCHING_FIXED_NOW"]);return x.astimezone(tz) if tz else x.replace(tzinfo=None)\n @classmethod\n def utcnow(cls):return cls.now(d.timezone.utc).replace(tzinfo=None)\nd.datetime=F\n')
            env={**os.environ,'PRICE_TRACKING_ENABLED':'false','MATCHING_FIXED_NOW':catalog['generated_at'],'PYTHONPATH':str(clock)}
            for tree in trees:
                command=[sys.executable,str(Path(__file__).resolve()),'--worker',str(tree),'--manifest',str(Path(args.manifest).resolve())]
                if tree==expected:command+=['--base-resolver',str(base_tree/'automation/name_matching.py')]
                subprocess.run(command,cwd=tree,env=env,check=True,stdout=subprocess.DEVNULL)
                for gen in GENERATORS:subprocess.run([sys.executable,gen],cwd=tree,env=env,check=True,stdout=subprocess.DEVNULL)
            b,c,a,e=[json.loads(gzip.decompress((tree/'contract-model.json.gz').read_bytes())) for tree in trees]
            for field in ('offers','products','registry'):assert b[field]==c[field], 'Legacy isolation model differs: '+field
            assert files(base_tree)==files(common), 'Legacy isolation HTML/sitemap/shards differ'
            issues=[];result={'base_sha':base,'head_sha':head,'snapshot':catalog['generated_at'],'offers':len(a['offers']),'legacy_isolation':'passed','merchant_review':manifest['merchant_review']['status'],'merge_ready':False}
            base_ids={o['id']:o['product_id'] for o in b['offers']}
            diagnostic={**initial,'actual_moved':sorted(o['id'] for o in a['offers'] if base_ids[o['id']]!=o['product_id']),'manifest_sources':sorted(pair[0] for pair in joins)}
            output.with_suffix('.diagnostic.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
            try:verify_merchant_fields(b,a);result['merchant_fingerprints']='passed'
            except AssertionError as error:result['merchant_fingerprints']='failed';issues.append(str(error))
            try:result.update(verify_models(b,a,e,joins))
            except AssertionError as error:issues.append(str(error))
            expected_files,actual_files=files(expected),files(actual)
            differences=sorted(p for p in expected_files.keys()|actual_files.keys() if expected_files.get(p)!=actual_files.get(p))
            result['unexpected_artifact_differences']=differences
            if differences:issues.append('Explicit mapping HTML/sitemap/shard output mismatch')
            for p in ['site/data/price-history.json.gz','site/_redirects']:
                if (base_tree/p).read_bytes()!=(actual/p).read_bytes():issues.append('Protected artifact changed: '+p)
            for tree in (base_tree,actual):subprocess.run([sys.executable,'automation/check_d1_activation.py','--prepare-build'],cwd=tree,check=True,stdout=subprocess.DEVNULL)
            redirect=subprocess.run(['node',str(ROOT/'tests/check_matching_contract.mjs'),str(base_tree),str(actual)])
            result['affiliate_redirect_responses']='passed' if redirect.returncode==0 else 'failed'
            if redirect.returncode:issues.append('Affiliate redirect response mismatch')
            result.update(protected_artifact_count=len(actual_files),issues=issues,status='passed' if not issues else 'blocked')
            output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
            assert not issues, 'Matching contract blocked; inspect saved diagnostic artifacts'
        except Exception as error:
            if not output.exists():output.write_text(json.dumps({**initial,'status':'blocked','error_type':type(error).__name__,'error':str(error)},indent=2)+'\n')
            raise
        finally:
            for tree in reversed(trees):subprocess.run(['git','worktree','remove','--force',str(tree)],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

if __name__=='__main__':main()
