import test from 'node:test';import assert from 'node:assert/strict';import {createRequire} from 'node:module';const require=createRequire(import.meta.url),{prepare,identity}=require('../site/assets/catalog-prepare.js');
const offer={id:'a',title:'Crocchette Èlite',price:12,url:'https://shop.test/a',brand:' Brand ',variant:'2 kg',weight_kg:2,gtin:'4006381333931',category:'Cibo',sku:'123'};
test('chunked preparation preserves eligibility, identity groups, text, order without mutating source rows',async()=>{
 const b={...offer,id:'b',price:10},rows=[offer,{...offer,id:'bad',price:0},b,{...offer,id:'http',url:'http://shop.test'}],before=JSON.stringify(rows);let yields=0,chunks=0;
 const result=await prepare(rows,{chunkSize:2,yieldTask:async()=>{yields++},onChunk:ms=>{assert(ms>=0);chunks++}});
 assert.deepEqual(result.data,[{...offer,brand:'Brand'},{...b,brand:'Brand'}]);assert.notEqual(result.data[0],offer);assert.deepEqual(result.identityIndex.get(identity(offer)),result.data);assert.equal(result.searchText.get('a'),require('../site/assets/search-suggest.js').normalizeSearch([offer.title,offer.variant,'Brand',offer.category,offer.sku,offer.gtin].join(' ')));
 assert.equal(yields,1);assert.equal(chunks,2);assert.equal(JSON.stringify(rows),before);
});
test('empty catalog and invalid batch size',async()=>{const r=await prepare([]);assert.equal(r.data.length,0);await assert.rejects(()=>prepare([offer],{chunkSize:0}));});
test('default yield permits a queued timer between preparation chunks',async()=>{let timer=false;const pending=setTimeout(()=>{timer=true},0);await prepare([offer,{...offer,id:'b'}],{chunkSize:1});assert(timer);clearTimeout(pending)});
test('manual comparison review holds remain searchable but cannot enter identity shortcuts',async()=>{
 const held={...offer,id:'held',comparison_review:{review_state:'unverified'}};
 const peer={...offer,id:'peer'};
 const result=await prepare([held,peer]);
 assert.deepEqual(result.data.map(o=>o.id),['held','peer']);
 assert(result.searchText.has('held'));
 assert.equal(result.data[0].comparison_review.review_state,'unverified');
 assert.deepEqual(result.identityIndex.get(identity(peer)).map(o=>o.id),['peer']);
});

test('accent variants share query normalization in suggestions, main-thread and worker filtering',async()=>{
 const suggest=require('../site/assets/search-suggest.js'),worker=require('../site/assets/catalog-filter.worker.js');
 const rows=['Patè','Paté','Pate\u0300','PATE'].map((title,i)=>({...offer,id:'accent'+i,title:'Gourmet '+title,available:true,checked_at:new Date().toISOString()}));
 const result=await prepare(rows),words=suggest.normalizeSearch('GOURMET paté').split(/\s+/);
 for(const o of result.data){const search=result.searchText.get(o.id);assert(words.every(w=>search.includes(w)));assert(worker.matches({...o,search,facets:{}},{words}));}
 assert.equal(suggest.candidates(rows,'gourmet pate').length,1);
});
test('canonical unknown packs remain searchable but cannot enter identity shortcuts',async()=>{
 const held={...offer,id:'unknown',quantity:{verified:false}},r=await prepare([held,offer]);
 assert(r.searchText.has(held.id));assert.deepEqual(r.identityIndex.get(identity(offer)).map(o=>o.id),[offer.id]);
});
