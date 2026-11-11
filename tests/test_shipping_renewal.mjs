import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import trade from '../site/assets/trade.js';
const rules=JSON.parse(fs.readFileSync(new URL('../site/data/shipping-rules.json',import.meta.url)));
const now=Math.max(...Object.values(rules.merchants).map(r=>Date.parse(r.checked_at||rules.checked_at)))+3600000;
const ids=['bauzaar','isola-dei-tesori','paco','webpet','hygge'];
function quote(id,price,weight,territory='standard',quantity=1,time=now){if(arguments.length<3)weight=1;return trade.shipping({merchant_id:id,price,shipping_weight_kg:weight,checked_at:new Date(time).toISOString(),quantity_verified:true},rules,quantity,territory,time)}
for(const id of ids){
 const r=rules.merchants[id], threshold=r.free_above;
 test(`${id}: cent below, exact, cent above`,()=>{
  assert.equal(quote(id,threshold-.01).fee,r.fee);
  const exact=quote(id,threshold);assert.equal(exact.status,'unknown');assert.equal(exact.total,undefined);assert.equal(exact.fee,undefined);
  assert.equal(quote(id,threshold+.01).fee,0);
 });
 test(`${id}: excluded destinations and services never yield total`,()=>{
  for(const territory of ['special','islands','cap-disagiati','livigno','campione','contrassegno','appuntamento','punto-poste','fermopoint-brt','unknown'])assert.equal(quote(id,100,1,territory).total,undefined);
 });
 test(`${id}: thirty days expiry and exact expiry boundary`,()=>{
  const end=Date.parse(r.verified_until);assert.equal(end-Date.parse(r.checked_at),30*86400000);
  assert.equal(quote(id,threshold+.01,1,'standard',1,end-1).fee,0);
  assert.equal(quote(id,threshold+.01,1,'standard',1,end).total,undefined);
  assert.equal(quote(id,threshold+.01,1,'standard',1,end+1).total,undefined);
  assert.equal(new URL(r.source).searchParams.has('utm_source'),false);
 });
}
test('Bauzaar: actual shipping weight required and 35kg cap applies to order',()=>{
 for(const weight of [undefined,null,0,NaN,35.001,36])assert.equal(quote('bauzaar',100,weight).total,undefined);
 assert.equal(quote('bauzaar',100,35).fee,0);
 assert.equal(quote('bauzaar',100,17.5,'standard',2).fee,0);
 assert.equal(quote('bauzaar',100,17.501,'standard',2).total,undefined);
});
test('Animaliapet flat policy fee and weight limits',()=>{
 for(const price of [1,68.99,69,69.01,100])assert.equal(quote('animaliapet',price,1).fee,5.99);
 assert.equal(quote('animaliapet',100,30).total,105.99);
 for(const weight of [undefined,null,0,30.001,31])assert.equal(quote('animaliapet',100,weight).total,undefined);
 assert.equal(quote('animaliapet',100,15,'standard',2).total,205.99);
 assert.equal(quote('animaliapet',100,15.001,'standard',2).total,undefined);
 for(const dest of ['special','islands','livigno','campione'])assert.equal(quote('animaliapet',100,1,dest).total,undefined);
});
