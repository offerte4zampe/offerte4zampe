import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import {execFileSync} from 'node:child_process';import trade from '../site/assets/trade.js';
const source=JSON.parse(fs.readFileSync(new URL('../site/data/shipping-rules.json',import.meta.url))),data=JSON.parse(execFileSync('python',['automation/build_shipping_seed.py','--json'],{encoding:'utf8'}));
const now=Date.parse(source.checked_at)+3600000;
const original=structuredClone(source);// Preserve explicit per-rule expiry, including the still-expired conflicting merchant.
const outcome=q=>({fee:q.fee,total:q.total,subtotal:q.subtotal,reason:q.reason});
function offer(id,price,weight=1,time=now){return {merchant_id:id,price,shipping_weight_kg:weight,available:true,checked_at:new Date(time).toISOString()};}
test('all shops preserve legacy totals over threshold, weight, quantity, expiry and destination matrix',()=>{
 let cases=0;
 for(const [id,r] of Object.entries(original.merchants)){
  const threshold=r.free_from??r.free_above??69;
  for(const p of [threshold-.01,threshold,threshold+.01,1,100])for(const weight of [undefined,1,35,35.001])for(const qty of [1,2,3])for(const territory of ['standard','special']){
   const o=offer(id,p,weight);if(weight===undefined)delete o.shipping_weight_kg;
   assert.deepEqual(outcome(trade.shipping(o,trade.shippingRulesFromRows(data.rules,now),qty,territory,now)),outcome(trade.shipping(o,original,qty,territory,now)),`${id} ${p} ${weight} ${qty} ${territory}`);cases++;
  }
  for(const time of [Date.parse(data.rules.find(r=>r.shop_id===id).verified_until),Date.parse(data.rules.find(r=>r.shop_id===id).verified_until)+1]){
   const o=offer(id,20,1,time);assert.deepEqual(outcome(trade.shipping(o,trade.shippingRulesFromRows(data.rules,time),1,'standard',time)),outcome(trade.shipping(o,original,1,'standard',time)));cases++;
  }
 }
 assert.equal(cases,610);
});
test('future and ended rules are never selected, and latest valid version wins',()=>{
 const base=data.rules.find(r=>r.shop_id==='webpet');
 assert.equal(trade.shipping(offer('webpet',20),trade.shippingRulesFromRows([{...base,valid_from:new Date(now+86400000).toISOString()}],now),1,'standard',now).total,undefined);
 assert.equal(trade.shipping(offer('webpet',20),trade.shippingRulesFromRows([{...base,valid_to:new Date(now).toISOString()}],now),1,'standard',now).total,undefined);
 const rows=[{...base,valid_to:new Date(now).toISOString()},{...base,valid_from:new Date(now).toISOString(),std_cents:700}];
 assert.equal(trade.shipping(offer('webpet',20),trade.shippingRulesFromRows(rows,now),1,'standard',now).total,27);
});
test('explicit verification expiry in data overrides the legacy seven-day fallback',()=>{
 const row={...data.rules.find(r=>r.shop_id==='webpet'),verified_until:'2026-10-28T11:59:59Z'};
 assert.equal(trade.shipping(offer('webpet',20),trade.shippingRulesFromRows([row],now),1,'standard',now).total,undefined);
});
test('SQLite seed roundtrip feeds the same pricing implementation',()=>{
 const script="import sqlite3,json;from pathlib import Path;c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row;c.executescript(Path('worker/schema/0002_shipping_rules.sql').read_text());c.executescript(Path('worker/seeds/shipping-rules.sql').read_text());print(json.dumps([dict(r) for r in c.execute('SELECT r.*,s.name AS shop_name FROM shipping_rule r JOIN shop s ON s.id=r.shop_id')]))";
 const rows=JSON.parse(execFileSync('python',['-c',script],{encoding:'utf8'}));
 for(const shop of data.shops)assert.deepEqual(outcome(trade.shipping(offer(shop.id,59),trade.shippingRulesFromRows(rows,now),1,'standard',now)),outcome(trade.shipping(offer(shop.id,59),source,1,'standard',now)));
});
test('all three threshold modes distinguish one cent below, exact and one cent above',()=>{
 const base=data.rules.find(r=>r.shop_id==='webpet');
 for(const [mode,expected] of [['inclusive',[5.9,0,0]],['exclusive',[5.9,5.9,0]],['unknown',[5.9,undefined,0]]]){
  const rules=trade.shippingRulesFromRows([{...base,free_from_cents:5900,threshold_mode:mode}],now);
  for(const [i,cents] of [5899,5900,5901].entries())assert.equal(trade.shipping(offer('webpet',cents/100),rules,1,'standard',now).fee,expected[i]);
 }
});
test('a current uncertain rule never falls back to an older verified rule',()=>{
 const base=data.rules.find(r=>r.shop_id==='webpet');
 const rows=[{...base,valid_to:new Date(now).toISOString()},{...base,valid_from:new Date(now).toISOString(),status:'uncertain',std_cents:null,free_from_cents:null}];
 assert.equal(trade.shipping(offer('webpet',100),trade.shippingRulesFromRows(rows,now),1,'standard',now).total,undefined);
});
