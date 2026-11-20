import test from 'node:test';import assert from 'node:assert/strict';import {createRequire} from 'node:module';import fs from 'node:fs';
const require=createRequire(import.meta.url),{productLink}=require('../site/assets/amazon-links.js');
const config=JSON.parse(fs.readFileSync(new URL('../site/data/amazon-links.json',import.meta.url),'utf8')),row=config.links[0],offer={id:row.offer_id,...row};
const now=Date.parse('2026-10-21T12:00:00Z');
test('verified exact product uses direct tagged Amazon link without prices or stock',()=>{const value=productLink(offer,config,now);assert.deepEqual(value,{url:'https://www.amazon.it/dp/'+row.asin+'?tag='+config.tracking_id,checked_at:row.checked_at});});
test('no fuzzy mapping, changed format, title, GTIN or brand',()=>{assert.equal(productLink({...offer,id:'other'},config,now),null);for(const key of ['title','brand','variant','gtin'])assert.equal(productLink({...offer,[key]:'changed'},config,now),null);});
test('current feed identity drift rejects the editorial link, including an unverified selling pack',()=>{
 const api=require('../site/assets/amazon-links.js'),time=Date.parse('2026-11-15T12:00:00Z');
 const editorial={offer_id:'paco:4587',title:'Monge - Monge Adult Monoprotein Coniglio Per Gatti',brand:'Monge',variant:'Sacco da 1,5 kg',gtin:'08009470011945',asin:'B000000001',checked_at:'2026-11-01',evidence_url:'https://www.amazon.it/dp/B000000001'};
 const registry={tracking_id:'offerte4zam02-21',links:[editorial]},exact={...editorial,id:editorial.offer_id,weight_kg:1.5,checked_at:'2026-11-15T01:13:00Z'};
 assert(api.productLink(exact,registry,time));
 for(const patch of [{variant:'Formato e ricetta da verificare nel negozio'}, {gtin:'4006381333931'},
  {variant:'Formato e ricetta da verificare nel negozio',gtin:'',weight_kg:null,quantity_verified:false,quantity:{kind:'sales_unit',value:1,unit:'confezione',verified:false}}]){
  const current={...exact,...patch};
  assert.equal(api.productLink(current,registry,time),null);
  assert.equal(api.comparisonLink(current,[current],registry,time),null);
 }
});
test('a rejected editorial identity can use only the exact destination of a currently verified peer',()=>{
 const api=require('../site/assets/amazon-links.js'),time=Date.parse('2026-11-15T12:00:00Z');
 const seed={id:'paco:1',title:'Current item',brand:'Brand',variant:'1,5 kg',gtin:'4006381333931',weight_kg:1.5,checked_at:'2026-11-15T01:13:00Z'};
 const peer={...seed,id:'bauzaar:2',title:'Same product at other shop',variant:'Sacco 1,5 kg'};
 const editorial=(o,asin)=>({...o,offer_id:o.id,asin,checked_at:'2026-11-01',evidence_url:'https://www.amazon.it/dp/'+asin});
 const registry={tracking_id:'offerte4zam02-21',links:[editorial({...seed,variant:'old selling pack'},'B000000001'),editorial(peer,'B000000002')]};
 assert.equal(api.productLink(seed,registry,time),null);
 const expected=api.productLink(peer,registry,time);assert(expected);
 assert.deepEqual(api.comparisonLink(seed,[seed,peer],registry,time),expected);
 assert.equal(api.comparisonLink(seed,[seed,{...peer,gtin:''}],registry,time),null);
});
test('expired, future, ambiguous or unsafe mapping never generates a link',()=>{for(const patch of [{checked_at:'2026-01-01'},{checked_at:'2027-01-01'},{asin:'bad'},{evidence_url:'https://www.amazon.it.evil.test/dp/'+row.asin}])assert.equal(productLink(offer,{...config,links:[{...row,...patch}]},now),null);assert.equal(productLink(offer,{...config,links:[row,row]},now),null);assert.equal(productLink(offer,null,now),null);});

test('editorial registry has unique offer IDs and size-specific KONG destinations',()=>{
 assert.equal(new Set(config.links.map(r=>r.offer_id)).size,config.links.length);
 const expected={'bauzaar:58411806589253':'B0002AR15U','isola-dei-tesori:000158950':'B0002AR15U','bauzaar:58411806523717':'B0002AR0I8','isola-dei-tesori:000158952':'B0002AR0I8','bauzaar:58411806458181':'B0002AR0HO','isola-dei-tesori:000158953':'B0002AR0HO'};
 for(const [id,asin] of Object.entries(expected))assert.equal(config.links.find(r=>r.offer_id===id)?.asin,asin);
 for(const entry of config.links){
  assert(!Object.keys(entry).some(k=>/price|availability|available|image|rating|review/i.test(k)));
  const resolved=productLink({id:entry.offer_id,...entry},config,Date.parse(entry.checked_at+'T12:00:00Z'));
  assert(resolved);if(entry.sitestripe_url)assert.equal(resolved.url,entry.sitestripe_url);else assert.equal(new URL(resolved.url).pathname,'/dp/'+entry.asin);
 }
});

test('verified Amazon link can follow exact cross-store identity but never guessed variants',()=>{
 const now=Date.now(),o={id:'paco:1',title:'Item',brand:'Brand',variant:'2 kg',gtin:'4006381333931',weight_kg:2,checked_at:new Date(now).toISOString()};
 const other={...o,id:'other:1'};
 const config={tracking_id:'offerte4zam02-21',links:[{...other,offer_id:other.id,asin:'B000000001',evidence_url:'https://www.amazon.it/dp/B000000001'}]};
 const api=require('../site/assets/amazon-links.js');
 assert(api.comparisonLink(o,[o,other],config,now));
 assert.equal(api.comparisonLink({...o,weight_kg:4},[other],config,now),null);
 assert.equal(api.comparisonLink({...o,gtin:''},[other],config,now),null);
});


test('brand typography normalization preserves previously verified Amazon links',()=>{
 for(const entry of config.links){const seed={id:entry.offer_id,...entry,brand:require('../site/assets/catalog-metadata.js').brand(entry.brand)};assert(productLink(seed,config,Date.parse(entry.checked_at+'T12:00:00Z')));assert.equal(productLink({...seed,brand:seed.brand+' Veterinary'},config,now),null);}
});

test('five owner-confirmed variants preserve original SiteStripe URLs in client and SSR',async()=>{
 const {resolveAmazonOffer}=await import('../worker/amazon-product.mjs');
 const entries=config.links.filter(r=>r.sitestripe_url);
 assert.equal(new Set(entries.map(r=>r.asin)).size,5);
 for(const entry of entries){
  const o={id:entry.offer_id,...entry},p={offers:[o]},time=Date.parse(entry.checked_at+'T12:00:00Z');
  assert.equal(productLink(o,config,time).url,entry.sitestripe_url);
  assert.equal(resolveAmazonOffer(p,config,time).url,entry.sitestripe_url);
  for(const patch of [
   {sitestripe_url:'https://link.amazon.evil.test/B0cNP6c1L'},
   {sitestripe_url:'javascript:alert(1)'},
   {sitestripe_url:'https://link.amazon/B0cNP6c1L?tag=other'},
   {sitestripe_url:null},
   {owner_variant_confirmed:false},
   {resolved_tracking_id:'other-21'},
   {resolved_asin:'B000000000'},
   {checked_at:'2026-01-01'}
  ]){
   const altered={...config,links:[{...entry,...patch}]};
   assert.equal(productLink(o,altered,time),null);
   assert.equal(resolveAmazonOffer(p,altered,time),null);
  }
  assert.equal(resolveAmazonOffer({offers:[{...o,variant:'wrong pack'}]},config,time),null);
 }
});
test('mismatched packs and lines are not activated',()=>{
 const selection=JSON.parse(fs.readFileSync(new URL('../automation/amazon-sitestripe-selection.json',import.meta.url),'utf8'));
 assert.deepEqual(selection.products.filter(p=>p.publication_ready).map(p=>p.selection_number),[4,6,9,10,11]);
 const activeIds=new Set(config.links.map(r=>r.offer_id));
 for(const p of selection.products.filter(p=>!p.publication_ready))for(const id of p.offer_ids)assert(!activeIds.has(id));
});

test('editorial proof is valid at the 30-day boundary and expires one millisecond later',()=>{
 const cutoff=Date.parse(row.checked_at)+30*86400000;
 assert(productLink(offer,config,cutoff));
 assert.equal(productLink(offer,config,cutoff+1),null);
});
