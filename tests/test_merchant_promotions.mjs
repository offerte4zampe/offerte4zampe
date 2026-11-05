import test from 'node:test';import assert from 'node:assert/strict';import {createRequire}from'node:module';
const require=createRequire(import.meta.url),{merchantPromotion,merchantPromotionHTML,discount}=require('../site/assets/trade.js');
const now=Date.parse('2026-11-05T12:00:00Z'),o={id:'a',available:true,price:8,url:'https://webpet.it/products/food?variant=1',checked_at:'2026-11-05T12:00:00Z'};
o.merchant_promotion={kind:'shopify_compare_at',offer_id:'a',price_cents:800,reference_cents:1000,observed_at:o.checked_at,source_url:o.url,valid_until:null};
test('merchant reference, percentage and savings have explicit labels',()=>{
 assert.deepEqual(merchantPromotion(o,now),{reference_cents:1000,saved_cents:200,percent:20});assert(discount(o,now));
 const h=merchantPromotionHTML(o,now);assert(h.includes('PROMO NEGOZIO'));assert(h.includes('<s>'));assert(h.includes('sul riferimento'));assert(!h.includes('Prima'));
 assert.equal(discount({price:8,previous_price:10},now),false);
});
test('mismatched snapshots, unavailable or unverified offers and expired claims never get badges',()=>{
 for(const extra of [{price:7},{id:'b'},{url:'https://other.test'},{available:false},{quantity_verified:false},{weight_conflict:true}])assert.equal(merchantPromotion({...o,...extra},now),null);
 assert.equal(merchantPromotion(o,now+13*3600000),null);
 for(const p of [{reference_cents:700},{reference_cents:NaN},{valid_until:'2026-11-05T11:00:00Z'},{observed_at:'2026-11-04T12:00:00Z'}])assert.equal(merchantPromotion({...o,merchant_promotion:{...o.merchant_promotion,...p}},now),null);
});
test('compact listing rows retain evidence without needing outbound URLs',()=>{
 const compact={...o};delete compact.url;
 assert.equal(merchantPromotion(compact,now).percent,20);
 assert.equal(merchantPromotion({...o,url:'https://evil.test',merchant_promotion:{...o.merchant_promotion,source_url:'https://evil.test'}},now),null);
});
