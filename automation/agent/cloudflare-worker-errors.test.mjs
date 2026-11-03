import test from 'node:test';
import assert from 'node:assert/strict';
import {workerErrorMetrics} from './cloudflare-worker-errors.mjs';
const accountId='a'.repeat(32);
const resp=(body,status=200)=>new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json'}});
const rows=entries=>({data:{viewer:{accounts:[{workersInvocationsAdaptive:entries.map(([requests,errors])=>({sum:{requests,errors}}))}]}}});
test('query is read-only GraphQL with bounded 24h window',async()=>{
 let calls=0;
 const result=await workerErrorMetrics({token:'fake',accountId,now:Date.parse('2026-11-03T12:00:00Z'),transport:async(url,options)=>{
  calls++;assert.equal(url,'https://api.cloudflare.com/client/v4/graphql');assert.equal(options.redirect,'manual');
  assert.equal(options.headers.Authorization,'Bearer fake');
  const body=JSON.parse(options.body);assert.match(body.query,/^query WorkerErrors/);assert.doesNotMatch(body.query,/mutation/i);
  assert.equal(body.variables.accountTag,accountId);assert.equal(body.variables.scriptName,'zampachiara');
  assert.equal(body.variables.start,'2026-11-02T12:00:00.000Z');
  return resp(rows([[200,2],[300,1]]));
 }});
 assert.equal(calls,1);
 assert.deepEqual(result,{status:'metrics_available',window_hours:24,requests:500,errors:3,error_rate_pct:0.6,alert:false});
 assert.equal(JSON.stringify(result).includes(accountId),false);
});
test('high error rate flags a failure, low traffic does not',async()=>{
 const high=await workerErrorMetrics({token:'fake',accountId,transport:async()=>resp(rows([[100,12]]))});
 assert.equal(high.alert,true);
 const low=await workerErrorMetrics({token:'fake',accountId,transport:async()=>resp(rows([[20,10]]))});
 assert.equal(low.alert,false);
});
test('no token, permission error and invalid metrics are not misreported as zero',async()=>{
 assert.equal((await workerErrorMetrics({accountId})).status,'metrics_not_configured');
 assert.equal((await workerErrorMetrics({token:'fake',accountId,transport:async()=>resp({errors:['forbidden']},403)})).status,'metrics_not_authorized');
 assert.equal((await workerErrorMetrics({token:'fake',accountId,transport:async()=>resp({errors:[{message:'no access'}]})})).status,'metrics_unavailable');
 assert.equal((await workerErrorMetrics({token:'fake',accountId,transport:async()=>resp(rows([[10,20]]))})).status,'metrics_unavailable');
});
