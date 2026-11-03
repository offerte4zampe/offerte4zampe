import test from 'node:test';
import assert from 'node:assert/strict';
import {auditCloudflareWorker} from './cloudflare-worker-audit.mjs';
const ACCOUNT='a'.repeat(32);
const reply=v=>new Response(JSON.stringify(v),{status:200,headers:{'content-type':'application/json'}});
const tool=(id,value)=>({jsonrpc:'2.0',id,result:{content:[{type:'text',text:JSON.stringify(value)}]}});
const init={jsonrpc:'2.0',id:1,result:{protocolVersion:'2025-06-18',capabilities:{},serverInfo:{name:'mock',version:'1'}}};
function transport({worker=true,user=false,fail=false}={}){
 const methods=[];
 return {methods,fetch:async (url,opt)=>{
  assert.equal(url,'https://mcp.cloudflare.com/mcp');assert.equal(opt.method,'POST');
  assert.equal(opt.redirect,'manual');assert.equal(opt.headers.Authorization,'Bearer fake');
  const req=JSON.parse(opt.body);methods.push(req.method==='tools/call'?req.params.name:req.method);
  if(req.method==='initialize')return reply(init);
  if(req.method==='notifications/initialized')return new Response(null,{status:202});
  if(req.params?.name==='whoami')return reply(tool(2,{id:(user?'user:xyz':'account:'+ACCOUNT)}));
  if(req.params?.name==='execute'){
   const code=req.params.arguments.code;
   assert.match(code,/method: "GET"/);assert.doesNotMatch(code,/method:\s*"(POST|DELETE|PUT|PATCH)"/);
   assert.match(code,/zampachiara/);
   assert.equal(req.params.arguments.account_id,ACCOUNT);
   return reply(tool(3,{api_success:!fail,worker_found:worker,modified_on:'2026-11-03T15:00:00Z'}));
  }
  throw Error('unexpected request');
 }};
}
test('no token never connects',async()=>{
 let n=0;const r=await auditCloudflareWorker({transport:async()=>{n++;throw Error('should not call')}});
 assert.equal(r.status,'missing_token');assert.equal(n,0);
});
test('account-token read-only verification with no sensitive output',async()=>{
 const t=transport();const r=await auditCloudflareWorker({token:'fake',transport:t.fetch});
 assert.equal(r.status,'worker_verified');assert.equal(r.worker,'zampachiara');
 assert.deepEqual(t.methods,['initialize','notifications/initialized','whoami','execute']);
 assert.equal(JSON.stringify(r).includes(ACCOUNT),false);
 assert.equal(JSON.stringify(r).includes('fake'),false);
});
test('user token requires explicit account id',async()=>{
 const t=transport({user:true});
 assert.equal((await auditCloudflareWorker({token:'fake',transport:t.fetch})).status,'account_id_required');
 const t2=transport({user:true});
 assert.equal((await auditCloudflareWorker({token:'fake',accountId:ACCOUNT,transport:t2.fetch})).status,'worker_verified');
});
test('account mismatch, missing worker and failed worker read are safe failures',async()=>{
 const mismatch=transport();
 assert.equal((await auditCloudflareWorker({token:'fake',accountId:'b'.repeat(32),transport:mismatch.fetch})).status,'account_mismatch');
 const missing=transport({worker:false});
 assert.equal((await auditCloudflareWorker({token:'fake',transport:missing.fetch})).status,'worker_not_found');
 const failed=transport({fail:true});
 assert.equal((await auditCloudflareWorker({token:'fake',transport:failed.fetch})).status,'workers_read_failed');
});
