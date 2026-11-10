import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../worker/index.mjs';

const blocked=['/data/history/00.json.gz','/data/price-history.json.gz','/data/price-observatory.json','/api/price-history/thing','/api/price-alerts','/api/alerts/subscribe','/api/watchlist','/osservatorio-prezzi','/leggere-storico-prezzi','/preferiti'];
test('default-off worker returns 410 before asset access on historical and alert routes',async()=>{
  let fetched=0;
  const env={ASSETS:{fetch:async()=>{fetched++;throw Error('asset must not be read')}}};
  for(const path of blocked){
    const result=await worker.fetch(new Request('https://offerte4zampe.it'+path),env,{waitUntil(){}});
    assert.equal(result.status,410,path);
    assert.equal(result.headers.get('Cache-Control'),'no-store',path);
  }
  assert.equal(fetched,0);
});
test('default-off Worker is not enabled by any truthy-looking flag',async()=>{
  const env={PRICE_TRACKING_ENABLED:'TRUE',ASSETS:{fetch:async()=>{throw Error('must block')}}};
  const result=await worker.fetch(new Request('https://offerte4zampe.it/data/history/00.json.gz'),env,{waitUntil(){}});
  assert.equal(result.status,410);
});

test('disabled favorites returns a useful informational 410 page, never a blank asset',async()=>{
 let fetches=0;
 const env={PRICE_TRACKING_ENABLED:'false',ASSETS:{fetch:async()=>{fetches++;throw Error('no assets allowed')}}};
 for(const path of ['/preferiti','/preferiti.html','/preferiti/']){
  const r=await worker.fetch(new Request('https://offerte4zampe.it'+path),env,{waitUntil(){}});
  assert.equal(r.status,410,path);
  assert.match(r.headers.get('content-type'),/text\/html/);
  assert.match(r.headers.get('x-robots-tag'),/noindex/);
  const html=await r.text();
  assert.match(html,/Funzione non disponibile/);
  assert.match(html,/href="\/confronta-cibo"/);
  assert.doesNotMatch(html,/prezzo desiderato|avvisi|soglia|storico|notifiche/i);
 }
 assert.equal(fetches,0);
});
