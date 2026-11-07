'use strict';
const assert=require('node:assert/strict');
const {test}=require('node:test');
const amazon=require('../site/assets/amazon-affiliate.js');
const product={gtin:'8001234567890',brand:'Marca Pet',weight_kg:2};
const curated={asin:'B0ABC12345',gtin:'8001234567890',brand:'Marca Pet',weight_kg:2,reviewed:true};
test('direct tagged Amazon.it link only for manually verified exact GTIN/brand/pack',()=>{
  assert.equal(amazon.affiliateUrl(product,curated,'offerte4zampe-21'),'https://www.amazon.it/dp/B0ABC12345?tag=offerte4zampe-21');
});
test('missing tag, invalid ASIN or unreviewed mapping produce no affiliate link',()=>{
  assert.equal(amazon.affiliateUrl(product,curated,''),null);
  assert.equal(amazon.affiliateUrl(product,{...curated,reviewed:false},'offerte4zampe-21'),null);
  assert.equal(amazon.affiliateUrl(product,{...curated,asin:'NOT_AN_ASIN'},'offerte4zampe-21'),null);
});
test('no loose GTIN, brand or pack-size matching',()=>{
  assert.equal(amazon.affiliateUrl({...product,gtin:''},curated,'offerte4zampe-21'),null);
  assert.equal(amazon.affiliateUrl({...product,gtin:'8001234567891'},curated,'offerte4zampe-21'),null);
  assert.equal(amazon.affiliateUrl({...product,brand:'Altra Marca'},curated,'offerte4zampe-21'),null);
  assert.equal(amazon.affiliateUrl({...product,weight_kg:4},curated,'offerte4zampe-21'),null);
});
test('no displayed price or availability is embedded in the builder',()=>{
  assert.deepEqual(Object.keys(amazon).sort(),['affiliateUrl','disclosure','eligible']);
  assert.match(amazon.disclosure,/Affiliato Amazon/);
});
