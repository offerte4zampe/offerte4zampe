import assert from 'node:assert/strict';import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),{prepare}=require('../site/assets/catalog-prepare.js');import fs from 'node:fs/promises';
export async function profileCatalog(page,origin,catalog){
 const metadata=require('../site/assets/catalog-metadata.js');
 const reference=catalog.offers.map(metadata.normalize).filter(o=>{try{return o.id&&typeof o.title==='string'&&Number.isFinite(o.price)&&o.price>0&&new URL(o.url).protocol==='https:'}catch{return false}});
 const expectedText=new Map(reference.map(o=>[o.id,[o.title,o.variant,o.brand,o.category,o.sku,o.gtin].join(' ').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('it').trim()]));
 const expectedIdentity=new Map();for(const o of reference)if(o.gtin&&o.weight_kg){const key=JSON.stringify([o.gtin,o.weight_kg,String(o.brand||'').trim().toLowerCase()]);if(!expectedIdentity.has(key))expectedIdentity.set(key,[]);expectedIdentity.get(key).push(o)}
 const prepared=await prepare(catalog.offers);assert.deepEqual(prepared.data,reference);assert.deepEqual(prepared.searchText,expectedText);assert.deepEqual(prepared.identityIndex,expectedIdentity);
 const {each}=require('../site/assets/catalog-cooperate.js'),trade=require('../site/assets/trade.js');
 const rules=JSON.parse(await fs.readFile(new URL('../site/data/shipping-rules.json',import.meta.url))),now=Date.parse(catalog.generated_at);
 const available=reference.filter(o=>o.available),quotes=new Map(),compareItalian=new Intl.Collator('it').compare;
 await each(available,o=>quotes.set(o.id,trade.shipping(o,rules,1,'standard',now)));
 const direct=[...available].sort((a,b)=>(trade.shipping(a,rules,1,'standard',now).total??Infinity)-(trade.shipping(b,rules,1,'standard',now).total??Infinity)||compareItalian(a.title,b.title));
 const cached=[...available].sort((a,b)=>(quotes.get(a.id).total??Infinity)-(quotes.get(b.id).total??Infinity)||compareItalian(a.title,b.title));
 assert.deepEqual(cached.map(o=>o.id),direct.map(o=>o.id),'Warmed quote ordering must equal direct calculation on full catalog');
 const runs=[];
 for(let i=0;i<3;i++){
  // Isolate each sample from prior product/search navigations and terminate its Worker on close.
  const samplePage=await page.browser().newPage();
  let result,downloads=0,indexDownloads=0;const index=JSON.parse(await fs.readFile(new URL('../site/data/catalog-index.json',import.meta.url)));try{
   await samplePage.setViewport(page.viewport());
   await samplePage.setRequestInterception(true);samplePage.on('request',r=>{if(r.url().includes('/data/catalog.json.gz'))downloads++;if(/\/data\/catalog-index\/[a-f0-9]+\.json\.gz$/.test(r.url()))indexDownloads++;return r.url().startsWith(origin)?r.continue():r.abort()});
   await samplePage.evaluateOnNewDocument(now=>{Date.now=()=>now},now);
   await samplePage.goto(origin+'/confronta-cibo.html?profile=1&sort=total',{waitUntil:'domcontentloaded'});
   await samplePage.waitForFunction(()=>Boolean(window.O4ZCatalogProfile),{timeout:60000});
   result=await samplePage.evaluate(()=>window.O4ZCatalogProfile);
  }finally{await samplePage.close()}
 assert.equal(result.loader_thread,'worker','Supported browser must parse in worker; fallback='+result.fallback_reason);assert.equal(downloads,0,'Comparator must not download the full catalog');assert.equal(indexDownloads,index.shards.length,'Each search shard downloads once');assert(result.offers>0);assert(result.cards>0);
  for(const sample of result.samples)assert(Number.isFinite(sample.ms)&&sample.ms>=0);
  runs.push(result);
 }
 const stages=[...new Set(runs.flatMap(r=>r.samples.map(s=>s.stage)))];
 for(const stage of ['decode_decompress','parse','prepare_indexes','prepare_controls','filter_sort','group','render_cards','render_comparison'])assert(stages.includes(stage),'Missing measured stage '+stage);
 const medians=Object.fromEntries(stages.map(stage=>{const values=runs.map(r=>r.samples.filter(s=>s.stage===stage).reduce((n,s)=>n+s.ms,0)).sort((a,b)=>a-b);return [stage,Number(values[1].toFixed(3))]}));
 const maxChunkMs=Math.max(...runs.flatMap(r=>r.samples.filter(s=>s.stage==='prepare_chunk_cpu').map(s=>s.ms)));assert(Number.isFinite(maxChunkMs));
 const quoteMax=Math.max(...runs.flatMap(r=>r.samples.filter(s=>s.stage==='quote_chunk_cpu').map(s=>s.ms)));assert(Number.isFinite(quoteMax));
 const report={quote_max_chunk_ms:Number(quoteMax.toFixed(3)),quote_order_equivalence:true,prepare_max_chunk_ms:Number(maxChunkMs.toFixed(3)),scope:'Decode/parse samples are worker CPU; remaining stages are main thread. Local checkout, Chromium mobile viewport on GitHub runner; no CPU/network throttling, no production/INP measurement',catalog_generated_at:catalog.generated_at,offers:runs[0].offers,iterations:3,units:'milliseconds',medians,runs};
 await fs.writeFile('browser-reports/catalog-profile.json',JSON.stringify(report,null,2));console.log('CATALOG_PROFILE '+JSON.stringify({...report,runs:undefined}));
}
