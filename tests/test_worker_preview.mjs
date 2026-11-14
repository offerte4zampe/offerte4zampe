import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import worker from '../worker/index.mjs';
const config=JSON.parse(fs.readFileSync(new URL('../wrangler.jsonc',import.meta.url),'utf8'));
test('native previews isolate analytics and disable all Telegram publishing paths',()=>{
 const p=config.previews;assert(p,'wrangler preview requires an explicit previews block');
 assert.equal(p.vars.SHIPPING_RULES_SOURCE,'json');assert.equal(p.vars.SHIPPING_SHADOW,'false');
 assert.equal(p.vars.PRICE_TRACKING_ENABLED,'false');assert.equal(p.vars.AMAZON_LINKS_ENABLED,'true');
 assert.equal(p.vars.TELEGRAM_AMAZON_OWNER_ENABLED,'false');assert.equal(p.vars.TELEGRAM_STATUS_RECOVERY,'false');
 assert.deepEqual(p.analytics_engine_datasets,[]);assert.deepEqual(p.durable_objects.bindings,[]);
 assert(!p.routes?.length);assert(!p.triggers?.crons?.length);assert(!p.d1_databases?.length);
 assert.equal(config.vars.PRICE_TRACKING_ENABLED,'false');
 assert.equal(config.analytics_engine_datasets[0].dataset,'offerte4zampe_outbound');
 assert.equal(config.durable_objects.bindings[0].name,'TELEGRAM_PUBLISHER');
});
test('preview without a publisher binding cannot publish or recover Telegram',async()=>{
 const env={...config.previews.vars,ASSETS:{fetch:async()=>{throw Error('Unexpected asset access')}}};
 let pending;worker.scheduled({},env,{waitUntil(p){pending=p}});await pending;
 const r=await worker.fetch(new Request('https://preview.invalid/api/telegram/status?recover=1'),env);
 assert.equal(r.status,503);assert.equal((await r.json()).configured,false);
});
