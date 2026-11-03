import test from 'node:test';
import assert from 'node:assert/strict';
import {planVerifiedOffers} from './offer-planner.mjs';
const now=Date.parse('2026-11-03T12:00:00Z');
const stamp=new Date(now-3600000).toISOString();
const offer={id:'bauzaar:1',merchant_id:'bauzaar',merchant:'Bauzaar',title:'Cibo 2 kg',price:12.5,weight_kg:2,available:true,checked_at:stamp,image:'https://cdn.shopify.com/pet.jpg',product_url:'/prodotto/cibo-2-kg'};
const catalog=(o=offer,s={id:'bauzaar',status:'ok',checked_at:stamp})=>({offers:[o],sources:[s]});
test('fresh source yields dry-run plan and correct unit price',()=>{
 const p=planVerifiedOffers(catalog(),{now});
 assert.equal(p.status,'ready_for_review');assert.equal(p.publish,false);
 assert.equal(p.candidates[0].price_per_kg,6.25);
});
test('rejects stale source, stale or future offer',()=>{
 assert.equal(planVerifiedOffers(catalog(offer,{id:'bauzaar',status:'stale',checked_at:stamp}),{now}).candidates.length,0);
 for(const checked_at of ['2026-10-01T00:00:00Z',new Date(now+1000).toISOString()])
  assert.equal(planVerifiedOffers(catalog({...offer,checked_at}),{now}).candidates.length,0);
});
test('rejects bad price, stock, image and format',()=>{
 for(const o of [{...offer,price:0},{...offer,available:false},{...offer,image:'https://cdn.shopify.com.evil.test/a.jpg'},{...offer,image:'http://cdn.shopify.com/a.jpg'},{...offer,title:'Cibo',product_url:'/prodotto/test'}])
  assert.equal(planVerifiedOffers(catalog(o),{now}).candidates.length,0);
});
test('invalid input, duplicates and bounded output',()=>{
 assert.equal(planVerifiedOffers(null,{now}).status,'invalid_catalog');
 const c=catalog();c.offers=[offer,offer];
 assert.equal(planVerifiedOffers(c,{now}).candidates.length,1);
 assert.throws(()=>planVerifiedOffers(c,{now,maxCandidates:50}));
});
