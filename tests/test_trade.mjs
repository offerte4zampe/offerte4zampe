import test from 'node:test';import assert from 'node:assert/strict';import {createRequire} from 'node:module';const require=createRequire(import.meta.url);const {shipping,discount}=require('../site/assets/trade.js');
const now=Date.parse('2026-10-18T12:00:00Z'),rules={checked_at:'2026-10-18',merchants:{a:{fee:6.9,free_above:59,boundary_unknown:59,max_shipping_weight_kg:35},b:{fee:5.9,free_from:39.9},c:{conflict:true}}},o={price:30,merchant_id:'a',shipping_weight_kg:12,checked_at:'2026-10-18T10:00:00Z'};
test('shipping threshold and quantity use declared shipping weight',()=>{assert.equal(shipping(o,rules,1,'standard',now).total,36.9);assert.equal(shipping(o,rules,2,'standard',now).total,60);assert.equal(shipping(o,rules,3,'standard',now).total,undefined);assert.equal(shipping({...o,price:59},rules,1,'standard',now).total,undefined)});
test('unknown weights, conflicting rules, special destinations and stale prices never produce a total',()=>{for(const [offer,territory] of [[{...o,shipping_weight_kg:null},'standard'],[{...o,merchant_id:'c'},'standard'],[o,'special'],[{...o,checked_at:'2026-10-15'},'standard']])assert.equal(shipping(offer,rules,1,territory,now).total,undefined);assert.equal(shipping(o,{...rules,checked_at:'2026-10-01'},1,'standard',now).total,undefined)});
test('inclusive threshold and suspicious reference prices',()=>{assert.equal(shipping({...o,price:39.9,merchant_id:'b'},rules,1,'standard',now).fee,0);assert.equal(discount({price:1.7,previous_price:31.9}),false);assert.equal(discount({price:80,previous_price:100}),false)});

const {merchant,matchKey,groupOffers}=require('../site/assets/trade.js');
test('direct and approved affiliate clicks resolve to a merchant without sending URLs',()=>{
 assert.equal(merchant('https://tc.tradetracker.net/?c=16143&a=518044&u=%2Fproducts%2Ffoo'),'Bauzaar');
 assert.equal(merchant('https://www.bauzaar.it/products/foo'),'Bauzaar');
 assert.equal(merchant('https://tc.tradetracker.net/?c=31221&a=518044'),'Isola dei Tesori');
 assert.equal(merchant('https://www.isoladeitesori.it/prodotto/foo/123.html'),'Isola dei Tesori');
 assert.equal(merchant('https://tc.tradetracker.net/?c=31221&a=999'),'');
 for(const u of ['https://tc.tradetracker.net/?c=999&a=518044','https://evil.test/?c=16143&a=518044','http://www.bauzaar.it/'])assert.equal(merchant(u),'');
});
test('group only fresh same-code same-brand same-weight offers across different shops',()=>{
 const a={id:'a',merchant_id:'a',gtin:'4006381333931',brand:'Brand',weight_kg:2,checked_at:'2026-10-18T10:00:00Z'};
 const b={...a,id:'b',merchant_id:'b',gtin:'04006381333931',brand:'BRAND'};
 assert.equal(groupOffers([a,b],now).length,1);
 for(const bad of [{...b,weight_kg:4},{...b,brand:'Other'},{...b,gtin:'4006381333932'},{...b,checked_at:'2026-10-10'},{...b,gtin:''},{...b,merchant_id:'a'}])assert.equal(groupOffers([a,bad],now).length,2);
 assert.equal(matchKey({...a,checked_at:'not-a-date'},now),'');
});
test('expired supplementary shipment weights cannot produce totals',()=>{assert.equal(shipping({...o,shipping_weight_checked_at:'2026-10-01'},rules,1,'standard',now).total,undefined)});
test('Isola official standard shipping preserves ambiguous exact threshold',()=>{
 const actual=require('../site/data/shipping-rules.json'),time=Date.parse(actual.checked_at)+3600000;
 const offer={price:30,merchant_id:'isola-dei-tesori',checked_at:new Date(time).toISOString()};
 assert.equal(shipping(offer,actual,1,'standard',time).total,35.9);
 assert.equal(shipping(offer,actual,2,'standard',time).total,60);
 assert.equal(shipping({...offer,price:59},actual,1,'standard',time).total,undefined);
 assert.equal(shipping(offer,actual,1,'special',time).total,undefined);
});

test('grouping preserves first occurrence, row order and singleton shops without mutation',()=>{
 const a={id:'a',merchant_id:'a',gtin:'4006381333931',brand:'Brand',weight_kg:2,checked_at:'2026-10-18T10:00:00Z'};
 const rows=[{...a,id:'single',weight_kg:4},a,{...a,id:'same-shop'},{...a,id:'b',merchant_id:'b'}, {...a,id:'invalid',gtin:'bad'}];
 const snapshot=JSON.stringify(rows);
 assert.deepEqual(groupOffers(rows,now).map(group=>group.map(o=>o.id)),[['single'],['a','same-shop','b'],['invalid']]);
 assert.equal(JSON.stringify(rows),snapshot);
 assert.deepEqual(groupOffers([],now),[]);
 const sameShop=Array.from({length:2000},(_,i)=>({...a,id:String(i)}));
 assert.equal(groupOffers(sameShop,now).length,2000);
});

test('Amazon recognition accepts only explicit Italian product links with the project tag',()=>{
 assert.equal(merchant('https://www.amazon.it/dp/B0722X975H?tag=offerte4zam02-21'),'Amazon');
 assert.equal(merchant('https://amazon.it/dp/B0002AR15U/?tag=offerte4zam02-21'),'Amazon');
 for(const url of ['https://www.amazon.it/s?k=collare&tag=offerte4zam02-21','https://www.amazon.it/dp/B0722X975H','https://www.amazon.it/dp/B0722X975H?tag=someone-21','https://www.amazon.it/dp/B0722X975H?tag=offerte4zam02-21&tag=other-21','https://amazon.it.evil.test/dp/B0722X975H?tag=offerte4zam02-21','http://www.amazon.it/dp/B0722X975H?tag=offerte4zam02-21','https://user:pass@www.amazon.it/dp/B0722X975H?tag=offerte4zam02-21'])assert.equal(merchant(url),'');
});


test('per-merchant shipping verification cannot renew stale rules for other shops',()=>{
 const now=Date.parse('2026-10-24T12:00:00Z'),offer={merchant_id:'paco',price:50,checked_at:'2026-10-24T11:00:00Z'};
 const rules={checked_at:'2026-09-01',merchants:{paco:{checked_at:'2026-10-24',fee:5.9,free_above:79,boundary_unknown:79},other:{fee:1}}};
 assert.equal(shipping(offer,rules,1,'standard',now).total,55.9);
 assert.equal(shipping({...offer,price:80},rules,1,'standard',now).total,80);
 assert.equal(shipping({...offer,price:79},rules,1,'standard',now).total,undefined);
 assert.equal(shipping({...offer,merchant_id:'other'},rules,1,'standard',now).total,undefined);
 assert.equal(shipping(offer,rules,1,'special',now).total,undefined);
 assert.equal(shipping(offer,{...rules,merchants:{paco:{...rules.merchants.paco,checked_at:'2026-11-01'}}},1,'standard',now).total,undefined);
});

test('reviewed identity expires independently of price freshness',()=>{
 const {matchKey}=require('../site/assets/trade.js');
 const now=Date.parse('2026-10-28T12:00:00Z');
 const o={gtin:'4006381333931',brand:'Brand',weight_kg:.03,checked_at:'2026-10-28T11:00:00Z',identity_review:'explicit-review',identity_expires_at:'2026-10-29T00:00:00Z'};
 assert(matchKey(o,now));
 assert.equal(matchKey({...o,identity_expires_at:'2026-10-27'},now),'');
 assert.equal(matchKey({...o,identity_expires_at:undefined},now),'');
});

test('unverified selling quantities and conflicting net weights never become matches or totals',()=>{
 const {matchKey}=require('../site/assets/trade.js');
 const unverified={...o,quantity_verified:false,gtin:'4006381333931',brand:'Brand',weight_kg:2};
 assert.equal(shipping(unverified,rules,1,'standard',now).total,undefined);
 assert.equal(matchKey(unverified,now),'');
 assert.equal(matchKey({...unverified,quantity_verified:true,weight_conflict:true},now),'');
});

test('explicit characteristic groups retain provenance and require fresh verified quantities',()=>{
 const a={id:'a',merchant_id:'a',brand:'Brand',gtin:'',product_matching_method:'name_characteristics',product_id:'p-01234567890123456789',quantity_verified:true,checked_at:'2026-10-18T10:00:00Z'};
 const b={...a,id:'b',merchant_id:'b'};
 assert.equal(groupOffers([a,b],now).length,1);
 for(const extra of [{quantity_verified:false},{checked_at:'2026-10-01'},{product_matching_method:'unattached'},{product_id:'invalid'}])assert.equal(groupOffers([a,{...b,...extra}],now).length,2);
});
