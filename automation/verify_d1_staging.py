"""Exercise the staging Worker on local workerd, or on remote D1 when authorized.

Remote mode requires existing Cloudflare credentials in the environment. Never
falls back to local when --remote was requested, never binds production resources.
"""
import argparse,datetime as dt,json,os,pathlib,re,secrets,shutil,subprocess,time,urllib.request,urllib.error
try:
    from .build_shipping_seed import convert
    from .d1_fingerprint import input_hash,commit_sha,SCOPE
except ImportError:
    from build_shipping_seed import convert
    from d1_fingerprint import input_hash,commit_sha,SCOPE
ROOT=pathlib.Path(__file__).resolve().parents[1]
NAME='zampachiara-shipping-staging'
WORKER='zampachiara-d1-staging'

def validate_staging_config(config):
    if config.get('name')!=WORKER or config.get('routes') or len(config.get('d1_databases',[]))!=1:raise RuntimeError('Staging Worker isolation configuration changed')
    binding=config['d1_databases'][0]
    if binding.get('database_name')!=NAME or binding.get('binding')!='SHIPPING_DB_STAGING':raise RuntimeError('Staging database isolation configuration changed')

def validate_resolved_database(info,expected_uuid):
    if info.get('name')!=NAME or info.get('uuid')!=expected_uuid or expected_uuid=='00000000-0000-0000-0000-000000000000':raise RuntimeError('Resolved database is not the exact staging database')

def validate_worker_url(url):
    if not re.fullmatch(r'https://zampachiara-d1-staging\.[a-z0-9-]+\.workers\.dev',url):raise RuntimeError('Deployment URL is not the staging Worker')

def assert_remote_target(cli,runtime):
    config=json.loads(runtime.read_text());validate_staging_config(config)
    info=json.loads(run(cli,['d1','info',NAME,'--json','--config',str(runtime)]))
    validate_resolved_database(info,config['d1_databases'][0]['database_id'])

def run(cli,args,stdin=None):
    p=subprocess.run([cli,*args],cwd=ROOT,text=True,input=stdin,capture_output=True,env={**os.environ,'CI':'true','WRANGLER_SEND_METRICS':'false'})
    if p.returncode:raise RuntimeError('Wrangler operation failed: '+' '.join(args[:3])+'\n'+p.stderr[-2000:])
    return p.stdout

def call(url,token,path,data=None):
    body=json.dumps(data or {}).encode();req=urllib.request.Request(url+path,data=body,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)
    except urllib.error.HTTPError as error:
        if error.code>=500:raise RuntimeError('Staging '+path+' failed: '+error.read(4096).decode(errors='replace')) from None
        raise

def main():
    p=argparse.ArgumentParser();p.add_argument('--remote',action='store_true');p.add_argument('--wrangler',default=os.environ.get('WRANGLER_BIN') or shutil.which('wrangler'));p.add_argument('--port',type=int,default=8789);a=p.parse_args()
    subprocess.run([os.sys.executable,str(ROOT/'automation/check_d1_activation.py'),'--prepare-build'],cwd=ROOT,check=True)
    if not a.wrangler:raise SystemExit('Install pinned Wrangler 4.154.0 or set WRANGLER_BIN.')
    if a.remote and not all(os.environ.get(k) for k in ('CLOUDFLARE_API_TOKEN','CLOUDFLARE_ACCOUNT_ID')):raise SystemExit('Remote staging NOT executed: Cloudflare account/token are not configured. No database or Worker was created.')
    config=json.loads((ROOT/'wrangler.staging.jsonc').read_text());token=secrets.token_urlsafe(32)
    validate_staging_config(config)
    if a.remote:
        records=json.loads(run(a.wrangler,['d1','list','--json','--config',str(ROOT/'wrangler.staging.jsonc')]))
        found=[r for r in records if r['name']==NAME]
        if not found:
            run(a.wrangler,['d1','create',NAME,'--config',str(ROOT/'wrangler.staging.jsonc'),'--update-config=false']);found=[r for r in json.loads(run(a.wrangler,['d1','list','--json','--config',str(ROOT/'wrangler.staging.jsonc')])) if r['name']==NAME]
        if len(found)!=1 or not re.fullmatch(r'[0-9a-f-]{36}',found[0]['uuid']):raise RuntimeError('Ambiguous staging database')
        config['d1_databases'][0]['database_id']=found[0]['uuid'];config['vars']['STAGING_LOCATION']='remote'
    else:config['vars']['STAGING_TOKEN']=token
    runtime=ROOT/'wrangler.staging.runtime.json';runtime.write_text(json.dumps(config,indent=2)+'\n')
    scope='--remote' if a.remote else '--local'
    if a.remote:assert_remote_target(a.wrangler,runtime)
    migration=run(a.wrangler,['d1','migrations','apply',NAME,scope,'--config',str(runtime)])
    reports=ROOT/'staging-reports';reports.mkdir(exist_ok=True)
    (reports/(('remote' if a.remote else 'local')+'-migrations.log')).write_text(migration)
    process=None;logfile=None
    try:
        if a.remote:
            assert_remote_target(a.wrangler,runtime)
            output=run(a.wrangler,['deploy','--config',str(runtime)])
            urls=re.findall(r'https://zampachiara-d1-staging\.[a-z0-9-]+\.workers\.dev',output)
            if not urls:raise RuntimeError('Deployment did not return a staging URL')
            url=urls[-1];validate_worker_url(url);run(a.wrangler,['secret','put','STAGING_TOKEN','--config',str(runtime)],stdin=token+'\n')
        else:
            url='http://127.0.0.1:'+str(a.port);logfile=(reports/'local-wrangler.log').open('w')
            process=subprocess.Popen([a.wrangler,'dev','--config',str(runtime),'--ip','127.0.0.1','--port',str(a.port),'--show-interactive-dev-session=false'],cwd=ROOT,stdout=logfile,stderr=logfile,env={**os.environ,'CI':'true','WRANGLER_SEND_METRICS':'false'})
        # Wait for startup/secret propagation; never bypass errors after this bounded window.
        if a.remote:assert_remote_target(a.wrangler,runtime)
        seed=convert(json.loads((ROOT/'site/data/shipping-rules.json').read_text()));seed_result=None
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            try:seed_result=call(url,token,'/seed',seed);break
            except (urllib.error.URLError,ConnectionError) as error:
                if isinstance(error,urllib.error.HTTPError) and error.code not in (404,503):raise
                if process and process.poll() is not None:raise RuntimeError('Local Worker exited; see staging-reports/local-wrangler.log')
                time.sleep(.5)
        if seed_result is None:raise RuntimeError('Staging Worker did not become ready')
        result=call(url,token,'/verify')
        report={'execution':'remote-d1' if a.remote else 'local-workerd','wrangler':'4.154.0','database':NAME,'seed':seed_result,'verification':result}
        path=reports/(('remote' if a.remote else 'local')+'-shipping-report.json');path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        if seed_result['counts']!={'shops':6,'rules':6}:raise RuntimeError('Seed row counts differ from SQLite fixture')
        if result['matrix']['cases']!=732 or result['matrix']['differences']:raise RuntimeError('Shipping parity failed')
        if not all(result['capabilities'][k] for k in ['check_constraints','triggers','generated_columns_and_index']):raise RuntimeError('Required SQL capabilities failed')
        details=[row.get('detail','') for row in result['plans']]
        if not any(re.search(r'SEARCH r USING (?:COVERING )?INDEX',d) for d in details) or any(re.search(r'SCAN r(?:$| )',d) for d in details):raise RuntimeError('Shipping query scans rules instead of using an index')
        if a.remote and os.environ.get('GITHUB_RUN_ID'):
            sha=commit_sha()
            if os.environ.get('GITHUB_SHA')!=sha:raise RuntimeError('Workflow SHA differs from checked-out commit')
            subprocess.run(['git','diff','--exit-code','HEAD','--'],cwd=ROOT,check=True,capture_output=True)
            attestation={'scope':SCOPE,'execution':'remote-d1','run_id':os.environ['GITHUB_RUN_ID'],'commit_sha':sha,'input_hash':input_hash(),'verified_at':dt.datetime.now(dt.timezone.utc).isoformat(),'database_uuid':config['d1_databases'][0]['database_id'],'database_name':NAME,'worker_name':WORKER}
            (reports/'remote-d1-attestation.json').write_text(json.dumps(attestation,indent=2)+'\n')
        print(json.dumps({'execution':report['execution'],'cases':610,'differences':0,'seed_meta':seed_result['meta'],'product_request_meta':result['product_request']['meta'],'fts5_trigram':result['capabilities']['fts5_trigram'],'report':str(path)},ensure_ascii=False))
    finally:
        if process:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        if logfile:logfile.close()
        # No generated token is retained in the checkout configuration.
        runtime.unlink(missing_ok=True)
if __name__=='__main__':main()
