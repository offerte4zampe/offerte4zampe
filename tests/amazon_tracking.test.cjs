'use strict';
const assert=require('node:assert/strict');
const {test}=require('node:test');
const config=require('../site/data/amazon-links.json');
const {productLink,comparisonLink}=require('../site/assets/amazon-links.js');
const now=Date.parse('2026-11-12T12:00:00Z');
function offerFrom(row){return {id:row.offer_id,brand:row.brand,title:row.title,variant:row.variant,gtin:row.gtin};}
test('Amazon.it uses the confirmed tracking ID for curated product links',()=>{
  assert.equal(config.tracking_id,'offerte4zam0c-21');
  assert.ok(config.links.length>0);
  for(const row of config.links){
    const result=productLink(offerFrom(row),config,now);
    assert.ok(result,'expected reviewed matching product: '+row.offer_id);
    if(Object.hasOwn(row,'sitestripe_url')){
      assert.equal(result.url,row.sitestripe_url,'SiteStripe must remain byte-for-byte unchanged');
      assert.equal(row.owner_variant_confirmed,true);
      assert.equal(row.resolved_tracking_id,config.tracking_id);
      assert.equal(row.resolved_asin,row.asin);
      assert.equal(new URL(result.url).hostname,'link.amazon');
      continue;
    }
    const url=new URL(result.url);
    assert.equal(url.hostname,'www.amazon.it');
    assert.equal(url.pathname,'/dp/'+row.asin);
    assert.equal(url.searchParams.get('tag'),'offerte4zam0c-21');
    assert.equal(url.searchParams.size,1);
  }
});
test('Amazon link is blocked for mismatched products, invalid tags and expired evidence',()=>{
  const row=config.links[0],offer=offerFrom(row);
  assert.equal(productLink({...offer,gtin:'wrong'},config,now),null);
  assert.equal(productLink({...offer,variant:'different'},config,now),null);
  assert.equal(productLink({...offer,title:'similar product'},config,now),null);
  assert.equal(productLink(offer,{...config,tracking_id:''},now),null);
  assert.equal(productLink(offer,{...config,tracking_id:'other-21'},Date.parse('2026-12-01T12:00:00Z')),null);
  assert.equal(productLink(offer,{...config,links:[{...row,evidence_url:'https://example.org/dp/'+row.asin}]},now),null);
});
test('comparison never invents Amazon prices or availability',()=>{
  const row=config.links[0],offer=offerFrom(row);
  const result=comparisonLink(offer,[offer],config,now);
  assert.ok(result);
  assert.deepEqual(Object.keys(result).sort(),['checked_at','url']);
});

test('each reviewed link rejects future and expired evidence independently',()=>{
  for(const row of config.links){
    const stamp=Date.parse(row.checked_at),offer=offerFrom(row);
    assert.equal(productLink(offer,config,stamp-300001),null,row.offer_id+' future evidence');
    assert.equal(productLink(offer,config,stamp+30*86400000+1),null,row.offer_id+' expired evidence');
    assert.ok(productLink(offer,config,stamp+12*3600000),row.offer_id+' fresh reviewed evidence');
  }
});
