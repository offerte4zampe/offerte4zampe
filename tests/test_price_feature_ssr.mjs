import test from 'node:test';
import assert from 'node:assert/strict';
import {content} from '../worker/canonical-product.mjs';

const product={slug:'demo-2-kg',name:'Demo 2 kg',brand:'Brand',format:'2 kg',quantity:null,gtin:'',history:[{day:'2026-11-07',low:0.01,high:999,count:1,sum:999}],related:[]};
const state={shops:2,rows:[],quotes:new Map(),best:null,available:[{price:2,merchant:'Shop A',url:'https://shop-a.example/item'},{price:3,merchant:'Shop B',url:'https://shop-b.example/item'}],quantity:1,territory:'standard',now:Date.parse('2026-11-07T12:00:00Z')};
test('SSR flag off omits history, minima, graphs and price-history DOM hooks',()=>{
  const page=content(product,state,false);
  assert.doesNotMatch(page.body,/Storico prezzi|Storico disponibile|data-history-offer|<svg|Minimo|massimo|rilevazioni effettive per negozio/i);
  assert.doesNotMatch(page.description,/storico|avvis[oi] prezzo/i);
});
test('SSR JSON-LD AggregateOffer ranges use current available merchant prices, never historical series',()=>{
  const page=content(product,state,false);
  assert.equal(page.schema.offers.lowPrice,2);
  assert.equal(page.schema.offers.highPrice,3);
  assert.equal(page.schema.offers.offerCount,2);
  assert.notEqual(page.schema.offers.highPrice,999);
});
test('SSR history remains recoverable behind explicitly enabled feature flag',()=>{
  const page=content(product,state,true);
  assert.match(page.body,/Storico prezzi/);
});
