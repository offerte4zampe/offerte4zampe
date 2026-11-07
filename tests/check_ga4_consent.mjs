// Regression test: GA4 is opt-in and existing first-party events remain intact.
// Run: node tests/check_ga4_consent.mjs
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source=readFileSync(new URL('../site/assets/metrics.js',import.meta.url),'utf8');
assert.match(source,/const ga4MeasurementId='';/,'GA4 must remain unconfigured until the real ID is supplied');

function run({consent=false,gpc=false,dnt='0',configured=true}={}){
  const scripts=[],requests=[],stored=new Map([['o4z-statistics-consent-v1',consent?'yes':'no']]);
  const footer={append(p){this.button=p.button}};
  const listeners={};
  const document={
    cookie:'',
    head:{appendChild(node){scripts.push(node.src)}},
    querySelector(selector){return selector==='footer .wrap'?footer:null},
    createElement(tag){return tag==='p'?{append(b){this.button=b}}:{setAttribute(){}}},
    addEventListener(event,fn){listeners[event]=fn}
  };
  const window={};
  const context={
    document,window,
    localStorage:{getItem(k){return stored.get(k)},setItem(k,v){stored.set(k,v)}},
    location:{pathname:'/',href:'https://offerte4zampe.it/'},
    navigator:{globalPrivacyControl:gpc,doNotTrack:dnt},
    fetch(url,opts){requests.push({url,opts});return Promise.resolve()},
    URL,Date,clearTimeout,setTimeout
  };
  const testSource=configured?source.replace("const ga4MeasurementId='';","const ga4MeasurementId='G-TEST1234';"):source;
  vm.runInNewContext(testSource,context);
  return {scripts,requests,footer,listeners,window,stored,document};
}

let t=run({consent:false});
assert.equal(t.scripts.length,0,'No Google script before consent');
assert.equal(t.requests.length,0,'No first-party metrics before consent');
t.footer.button.onclick();
assert.equal(t.scripts.length,1,'Google loads only on opt-in');
assert.equal(t.requests.length,1,'First-party page view preserved');
assert.equal(t.requests[0].url,'/api/metrics');
assert.equal(JSON.parse(t.requests[0].opts.body).event,'page_view');
assert.equal(t.window.dataLayer.filter(x=>x[0]==='event').length,1,'Exactly one GA page view');
t.footer.button.onclick();
assert.equal(t.window.dataLayer.at(-1)[0],'consent');
assert.equal(t.window.dataLayer.at(-1)[2].analytics_storage,'denied','Withdrawal revokes analytics storage');
assert.equal(t.requests.length,1,'Opt-out sends no new events');

t=run({consent:true});
assert.equal(t.scripts.length,1);
assert.equal(t.window.dataLayer.filter(x=>x[0]==='event').length,1,'No duplicate page view');

for(const config of [{consent:true,gpc:true},{consent:true,dnt:'1'}]){
  t=run(config);
  assert.equal(t.scripts.length,0,'Privacy signals block GA');
  assert.equal(t.requests.length,0,'Privacy signals block first-party metrics');
}

t=run({consent:true,configured:false});
assert.equal(t.scripts.length,0,'Absent GA ID must fail closed');
assert.equal(t.requests.length,1,'Existing analytics still works without GA ID');
console.log('GA4 opt-in, opt-out, privacy signals and first-party fallback: OK');
