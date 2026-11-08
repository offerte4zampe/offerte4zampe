import test from 'node:test';
import assert from 'node:assert/strict';
import {priceHistoryAllowed,historicalOfferAllowed} from '../worker/price-merchant-policy.mjs';
import {view,content} from '../worker/canonical-product.mjs';

test('Amazon denied even when other merchants are allowed',()=>{
  assert.equal(priceHistoryAllowed('amazon'),false);
  assert.equal(priceHistoryAllowed('AMAZON'),false);
  assert.equal(historicalOfferAllowed('amazon:B012345678'),false);
  assert.equal(priceHistoryAllowed('unknown-new-shop'),false);
  assert.equal(priceHistoryAllowed('bauzaar'),true);
});
test('legacy mixed-store summary is hidden and Amazon history hook is absent',()=>{
  const now=Date.parse('2026-11-08T12:00:00Z');
  const make=(id,merchant)=>({id,merchant_id:merchant,merchant,price:12,available:true,checked_at:'2026-11-08T11:00:00Z',quantity:{verified:true,kind:'pieces',value:40,unit:'pz'},unit_prices:{pz:0.3},unit_price:0.3,unit_price_unit:'pz',url:'https://example.test/item'});
  const product={id:'p-test',slug:'mixed',name:'Mixed',brand:'Brand',format:'40 pezzi',quantity:{verified:true,kind:'pieces',value:40,unit:'pz'},offers:[make('amazon:ASIN','amazon'),make('bauzaar:1','bauzaar')],history:[{day:'2026-11-07',low:1,high:2,sum:3,count:2}]};
  const state=view(product,{},now);
  assert.equal(state.aggregateHistorySafe,false);
  const page=content(product,state);
  assert.equal(page.body.includes('Minimo '+new Intl.NumberFormat('it-IT',{style:'currency',currency:'EUR'}).format(1)),false);
  assert.equal(page.body.includes('data-history-offer="amazon:ASIN"'),false);
  assert.equal(page.body.includes('data-history-offer="bauzaar:1"'),true);
});
