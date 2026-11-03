import test from 'node:test';
import assert from 'node:assert/strict';
import {checkTelegramStatus} from './telegram-status-monitor.mjs';
const base={integration:'telegram-v1',configured:true,halted:false,test_status:'sent',channel_matches:true,last_sent_day:'2026-11-03'};
const reply=(d,status=200)=>new Response(JSON.stringify(d),{status,headers:{'Content-Type':'application/json'}});
test('operational status, never sends Telegram messages',async()=>{
 let calls=0;const r=await checkTelegramStatus({now:Date.parse('2026-11-03T12:00:00Z'),transport:async(url,opts)=>{
  calls++;assert.equal(url,'https://offerte4zampe.it/api/telegram/status');assert.equal(opts.method,'GET');assert.equal(opts.redirect,'manual');
  return reply(base);
 }});
 assert.equal(calls,1);assert.deepEqual(r,{status:'telegram_operational',last_sent_day:'2026-11-03',sent_today:true});
});
test('no fresh post today is not treated as failure',async()=>{
 const r=await checkTelegramStatus({now:Date.parse('2026-11-03T12:00:00Z'),transport:async()=>reply({...base,last_sent_day:'2026-11-02'})});
 assert.equal(r.status,'telegram_operational');assert.equal(r.sent_today,false);
});
test('halts and missing configuration are errors, with no sensitive details',async()=>{
 for(const [d,status] of [[{...base,halted:true},'telegram_halted'],[{...base,configured:false},'telegram_not_configured'],[{...base,test_status:'pending'},'telegram_test_incomplete']]){
  const r=await checkTelegramStatus({transport:async()=>reply(d)});
  assert.equal(r.status,status);assert.equal(JSON.stringify(r).includes('token'),false);
 }
});
test('unexpected responses and redirects fail closed',async()=>{
 for(const response of [reply({},200),reply(base,503),new Response(null,{status:302,headers:{location:'https://evil.test'}}),new Response('unsafe',{status:200,headers:{'content-type':'text/plain'}})]){
  const r=await checkTelegramStatus({transport:async()=>response});
  assert.notEqual(r.status,'telegram_operational');
 }
});
