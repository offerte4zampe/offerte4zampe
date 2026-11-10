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
test('SSR history remains recoverable for an eligible non-Amazon merchant with flag enabled',()=>{
  const offer={id:'bauzaar:fixture',merchant_id:'bauzaar',merchant:'Bauzaar',title:'Demo 2 kg',price:12,available:true,checked_at:'2026-11-07T11:00:00Z',quantity:{verified:true},unit_price:null,unit_prices:{},url:'https://example.test/item'};
  const enabledState={...state,rows:[offer],quotes:new Map([[offer.id,{status:'unknown',destination:'Italia'}]]),aggregateHistorySafe:true};
  const page=content({...product,offers:[offer]},enabledState,true);
  assert.match(page.body,/Storico prezzi/);
  assert.match(page.body,/data-history-offer="bauzaar:fixture"/);
  const denied={...offer,id:'amazon:ASIN',merchant_id:'amazon',merchant:'Amazon'};
  const mixed=content({...product,offers:[offer,denied]}, {...enabledState,rows:[offer,denied],quotes:new Map([[offer.id,{status:'unknown',destination:'Italia'}],[denied.id,{status:'unknown',destination:'Italia'}]]),aggregateHistorySafe:false}, true);
  assert.doesNotMatch(mixed.body,/data-history-offer="amazon:ASIN"/);
  assert.doesNotMatch(mixed.body,/Minimo 0,01/);
});
