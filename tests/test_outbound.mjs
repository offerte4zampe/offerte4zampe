import test from 'node:test';import assert from 'node:assert/strict';
import fs from 'node:fs';import path from 'node:path';import {gunzipSync} from 'node:zlib';
import trade from '../site/assets/trade.js';import {outbound} from '../worker/outbound.mjs';
const now=Date.parse('2026-10-29T12:00:00Z'),slug='brand-adult-2-kg-123';
const offer={id:'bauzaar:123',merchant_id:'bauzaar',price:12.34,available:true,checked_at:'2026-10-29T11:00:00Z',url:'https://www.bauzaar.it/a?x=1&b=2',affiliate_url:'https://tc.tradetracker.net/?c=16143&m=600171&a=518044&u=https%3A%2F%2Fwww.bauzaar.it%2Fa%3Fx%3D1%26b%3D2'};
function fixture(o=offer){const points=[],pending=[];return {points,pending,ctx:{waitUntil:p=>pending.push(p)},env:{OUTBOUND_CLICKS:{writeDataPoint:x=>points.push(x)},ASSETS:{fetch:async r=>Response.json(new URL(r.url).pathname.includes('canonical-routes')?{[offer.id]:slug}:{[slug]:{id:'p-public',offers:[o]}})}}}}
function req(extra={},id=offer.id){return new Request('https://offerte4zampe.it/go/'+encodeURIComponent(id)+'?from=product&url=https://evil.test',{headers:extra})}
test('302 preserves exact affiliate bytes and works without consent or JS',async()=>{const f=fixture();const r=await outbound(req(),f.env,f.ctx,now);assert.equal(r.status,302);assert.equal(r.headers.get('Location'),offer.affiliate_url);assert.equal(r.headers.get('Cache-Control'),'no-store');assert.equal(r.headers.get('X-Robots-Tag'),'noindex, nofollow');assert.equal(r.headers.get('Referrer-Policy'),'no-referrer');assert.equal(f.pending.length,0)});
test('consented analytics are minimised; privacy signals, duplicate cookies and HEAD suppress writes',async()=>{
 for(const [headers,count] of [[{Cookie:'__Host-o4z-statistics=yes'},1],[{Cookie:'__Host-o4z-statistics=no'},0],[{Cookie:'__Host-o4z-statistics=yes','Sec-GPC':'1'},0],[{Cookie:'__Host-o4z-statistics=yes',DNT:'1'},0],[{Cookie:'__Host-o4z-statistics=yes; __Host-o4z-statistics=no'},0],[{Cookie:'__Host-o4z-statistics=yes','Sec-Purpose':'prefetch'},0]]){
 const f=fixture();await outbound(req(headers),f.env,f.ctx,now);await Promise.all(f.pending);assert.equal(f.points.length,count);if(count)assert.deepEqual(f.points[0],{indexes:['bauzaar'],blobs:['bauzaar','p-public',offer.id,'product'],doubles:[1234]});
 }
 const f=fixture();await outbound(new Request(req({Cookie:'__Host-o4z-statistics=yes'}),{method:'HEAD'}),f.env,f.ctx,now);assert.equal(f.pending.length,0);
});
test('missing, throwing or rejected analytics never break redirect',async()=>{for(const mode of ['missing','throw','reject']){const f=fixture();if(mode==='missing')delete f.env.OUTBOUND_CLICKS;else f.env.OUTBOUND_CLICKS.writeDataPoint=()=>{if(mode==='throw')throw Error('blocked');return Promise.reject(Error('blocked'))};assert.equal((await outbound(req({Cookie:'__Host-o4z-statistics=yes'}),f.env,f.ctx,now)).headers.get('Location'),offer.affiliate_url);await Promise.all(f.pending)}});
test('inactive, stale, unsafe or invalidated offers return to product; unknown goes to search',async()=>{for(const o of [{...offer,available:false},{...offer,checked_at:'2026-10-01'},{...offer,affiliate_url:'javascript:alert(1)'},{...offer,identity_review:true,identity_expires_at:'2026-10-28'}]){const f=fixture(o);assert.equal((await outbound(req(),f.env,f.ctx,now)).headers.get('Location'),'/prodotto/'+slug)}const f=fixture();assert.equal((await outbound(req({},'missing'),f.env,f.ctx,now)).headers.get('Location'),'/confronta-cibo');assert.equal((await outbound(req({},'https://evil.test'),f.env,f.ctx,now)).headers.get('Location'),'/confronta-cibo')});
test('all snapshot offers retain the old direct target byte-for-byte through real shard resolution',async()=>{
 const root=new URL('../site/',import.meta.url),snapshot=JSON.parse(gunzipSync(fs.readFileSync(new URL('data/catalog.json.gz',root))));
 // Catalog imports can remove historical example IDs. Exercise both affiliate
 // programs using current eligible rows rather than requiring stale products.
 const withheld=['bauzaar','isola-dei-tesori'].map(merchant=>{
  const o=snapshot.offers.find(o=>o.merchant_id===merchant&&o.available&&trade.merchantUrl(o)&&(!o.identity_review||Date.parse(o.identity_expires_at)>=Date.parse(o.checked_at)));
  assert(o,'snapshot must contain an eligible '+merchant+' redirect');return {id:o.id,offer:o};
 });
 const withheldIds=new Set(withheld.map(r=>r.id));assert.equal(withheldIds.size,2);
 const cache=new Map(),env={ASSETS:{fetch:async r=>{const pathname=new URL(r.url).pathname;
  if(pathname==='/data/store-audit.json')return Response.json({commercial_suppression:{withheld}});
  if(!cache.has(pathname)){
   let data=JSON.parse(fs.readFileSync(path.join(root.pathname,pathname),'utf8'));
   if(pathname.includes('canonical-routes'))for(const id of withheldIds)delete data[id];
   if(pathname.includes('canonical-products'))for(const p of Object.values(data))p.offers=p.offers?.filter(o=>!withheldIds.has(o.id));
   cache.set(pathname,JSON.stringify(data));
  }
  return new Response(cache.get(pathname),{headers:{'Content-Type':'application/json'}});
 }}};
 let compared=0,active=0;
 for(const o of snapshot.offers){const old=o.affiliate_url||o.url;assert.equal(trade.merchantUrl(o),old,o.id);compared++;
 const r=await outbound(req({},o.id),env,null,Date.parse(o.checked_at));if(o.available&&(!o.identity_review||Date.parse(o.identity_expires_at)>=Date.parse(o.checked_at))){assert.equal(r.headers.get('Location'),old,o.id);active++}else assert.match(r.headers.get('Location'),/^\/prodotto\//);}
 assert(compared>10000);console.log(JSON.stringify({equivalence_offers:compared,active_redirects:active}));
});
test('withheld exact original rows retain affiliate bytes without claiming current price telemetry',async()=>{
 for(const withSlug of [false,true])for(const method of ['GET','HEAD']){
  const pending=[],env={OUTBOUND_CLICKS:{writeDataPoint:()=>assert.fail('withheld price must not be recorded')},ASSETS:{fetch:async r=>{
   const p=new URL(r.url).pathname;
   if(p.includes('canonical-routes'))return Response.json(withSlug?{[offer.id]:slug}:{});
   if(p==='/data/store-audit.json')return Response.json({commercial_suppression:{withheld:[{id:offer.id,offer}]}});
   return Response.json({[slug]:{id:'p-public',offers:[]}});
  }}};
  const r=await outbound(new Request(req({Cookie:'__Host-o4z-statistics=yes'}),{method}),env,{waitUntil:p=>pending.push(p)},now);
  assert.equal(r.status,302);assert.equal(r.headers.get('Location'),offer.affiliate_url);
  assert.equal(r.headers.get('X-Robots-Tag'),'noindex, nofollow');assert.equal(r.headers.get('Cache-Control'),'no-store');assert.equal(r.headers.get('Referrer-Policy'),'no-referrer');assert.equal(pending.length,0);
 }
});
test('withheld rows cannot bypass existing freshness, stock, identity or safe target guards',async()=>{
 for(const row of [{...offer,available:false},{...offer,checked_at:'2026-10-01'},{...offer,checked_at:'2026-10-30'},{...offer,affiliate_url:'https://evil.test/steal'},{...offer,affiliate_url:offer.affiliate_url.replace('https%3A%2F%2Fwww.bauzaar.it%2Fa%3Fx%3D1%26b%3D2','https%3A%2F%2Fevil.test%2Fsteal')},{...offer,affiliate_url:offer.affiliate_url.replace('c=16143','c=31221')},{...offer,affiliate_url:offer.affiliate_url.replace('a=518044','a=999')},{...offer,affiliate_url:offer.affiliate_url.replace('m=600171','m=1618255')},{...offer,affiliate_url:offer.affiliate_url+'&u=https%3A%2F%2Fevil.test'},{...offer,identity_review:true,identity_expires_at:'2026-10-28'},{...offer,id:'another:123'}]){
  const env={ASSETS:{fetch:async r=>Response.json(new URL(r.url).pathname==='/data/store-audit.json'?{commercial_suppression:{withheld:[{id:offer.id,offer:row}]}}:{})}};
  const r=await outbound(req(),env,null,now);assert.equal(r.status,302);assert.equal(r.headers.get('Location'),'/confronta-cibo');
 }
});
