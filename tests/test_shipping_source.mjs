import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import {execFileSync} from 'node:child_process';
import {shippingSource,readShippingRows} from '../worker/shipping-source.mjs';import trade from '../site/assets/trade.js';
const json=JSON.parse(fs.readFileSync(new URL('../site/data/shipping-rules.json',import.meta.url))),data=JSON.parse(execFileSync('python',['automation/build_shipping_seed.py','--json'],{encoding:'utf8'}));
const validation={remote_success:true,attestation_scope:'shipping-infrastructure-v1',ancestor_verified:true,remote_run_id:'123',remote_commit_sha:'fixture-sha',build_commit_sha:'fixture-sha',verified_input_hash:'fixture-hash',current_input_hash:'fixture-hash',verified_at:new Date(Date.parse(json.checked_at)+3600000).toISOString(),database_uuid:'11111111-1111-4111-8111-111111111111'};
const now=Date.parse(json.checked_at)+3600000,offers=[{merchant_id:'webpet',price:20,checked_at:new Date(now).toISOString()}];
function db(rows=data.rules){return {prepare(sql){assert(sql.includes('r.shop_id=?1'));return {bind(...values){return {values}}}},async batch(statements){return statements.map(s=>({success:true,results:rows.filter(r=>r.shop_id===s.values[0]),meta:{rows_read:2,rows_written:0}}))}};}
test('JSON default does not query D1',async()=>{
 const result=await shippingSource({SHIPPING_DB:{batch(){throw Error('must not run')}}},offers,json,{now,validation});assert.equal(result.rules,json);assert.equal(result.source,'json');
});
test('D1 mode adapts selected rows and returns actual binding meta',async()=>{
 const result=await shippingSource({SHIPPING_RULES_SOURCE:'d1',SHIPPING_DB:db()},offers,json,{now,validation});assert.equal(result.source,'d1');assert.equal(result.meta.rows_read,2);assert.equal(trade.shipping(offers[0],result.rules,1,'standard',now).total,25.9);
});
test('missing binding, query errors and missing rules fall back to JSON and log once',async()=>{
 for(const binding of [undefined,{prepare(){throw Error('quota limit')}},db([])]){
  const events=[];const r=await shippingSource({SHIPPING_RULES_SOURCE:'d1',SHIPPING_DB:binding},offers,json,{now,validation,log:e=>events.push(e)});
  assert.equal(r.rules,json);assert.equal(r.fallback,true);assert.equal(events.length,1);assert.equal(events[0].event,'shipping_d1_fallback');
 }
});
test('shadow keeps JSON visible and logs only differences',async()=>{
 const events=[];await shippingSource({SHIPPING_SHADOW:'true',SHIPPING_DB:db()},offers,json,{now,validation,log:e=>events.push(e)});assert.equal(events.length,0);
 const rows=data.rules.map(r=>r.shop_id==='webpet'?{...r,std_cents:700}:r);
 const result=await shippingSource({SHIPPING_SHADOW:'true',SHIPPING_DB:db(rows)},offers,json,{now,validation,log:e=>events.push(e)});
 assert.equal(result.rules,json);assert.equal(events[0].event,'shipping_shadow_difference');assert.equal(events[0].differences[0].d1_total,27);assert(!JSON.stringify(events).includes('checked_at'));
});
test('expired or uncertain D1 policy is not replaced by an older favorable policy',async()=>{
 for(const row of [{...data.rules.find(r=>r.shop_id==='webpet'),status:'uncertain',std_cents:null,free_from_cents:null},{...data.rules.find(r=>r.shop_id==='webpet'),verified_until:'2026-10-28T11:59:00Z'}]){
  const r=await shippingSource({SHIPPING_RULES_SOURCE:'d1',SHIPPING_DB:db([row])},offers,json,{now,validation});assert.equal(r.source,'d1');assert.equal(trade.shipping(offers[0],r.rules,1,'standard',now).total,undefined);
 }
});
test('duplicate merchant offers use one indexed read with UTC parameters',async()=>{
 let statements;const binding=db();const batch=binding.batch.bind(binding);binding.batch=s=>{statements=s;return batch(s)};
 await readShippingRows(binding,['webpet','webpet'],now);assert.equal(statements.length,1);assert.deepEqual(statements[0].values,['webpet','IT',new Date(now).toISOString()]);
});

test('production D1 and shadow flags cannot bypass absent remote validation',async()=>{
 for(const flags of [{SHIPPING_RULES_SOURCE:'d1'},{SHIPPING_SHADOW:'true'}]){
  const events=[];const r=await shippingSource({...flags,SHIPPING_DB:{prepare(){throw Error('must not query')}}},offers,json,{now,log:e=>events.push(e)});
  assert.equal(r.rules,json);assert.equal(r.activationBlocked,true);assert.equal(events[0].event,'shipping_activation_blocked');
 }
});

test('unverified ancestry or a changed input hash blocks validation',async()=>{
 for(const wrong of [{...validation,build_commit_sha:'changed',ancestor_verified:false},{...validation,current_input_hash:'changed'}]){
  const r=await shippingSource({SHIPPING_RULES_SOURCE:'d1',SHIPPING_DB:db()},offers,json,{now,validation:wrong,log:()=>{}});
  assert.equal(r.activationBlocked,true);assert.equal(r.rules,json);
 }
});

test('an attested ancestor remains valid when only build SHA advances',async()=>{
 const r=await shippingSource({SHIPPING_RULES_SOURCE:'d1',SHIPPING_DB:db()},offers,json,{now,validation:{...validation,build_commit_sha:'new-catalog-commit'},log:()=>{}});
 assert.equal(r.source,'d1');assert.equal(r.activationBlocked,undefined);
});
