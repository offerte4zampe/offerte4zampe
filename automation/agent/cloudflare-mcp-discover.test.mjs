import test from 'node:test';
import assert from 'node:assert/strict';
import {discoverMcpTools,MCP_ENDPOINT} from './cloudflare-mcp-discover.mjs';
function respond(body,status=200,headers={}){return new Response(typeof body==='string'?body:JSON.stringify(body),{status,headers:{'Content-Type':'application/json',...headers}});}
const init={jsonrpc:'2.0',id:1,result:{protocolVersion:'2025-06-18',capabilities:{tools:{}},serverInfo:{name:'test',version:'1'}}};
test('no token means no network call',async()=>{
 let count=0;const r=await discoverMcpTools({transport:async()=>{count++;throw Error('unexpected')}});
 assert.equal(r.status,'not_authorized');assert.equal(count,0);
});
test('only initialize, initialized notification, tools/list',async()=>{
 const methods=[];const r=await discoverMcpTools({token:'sentinel-token',transport:async(url,opts)=>{
  assert.equal(url,MCP_ENDPOINT);assert.equal(opts.method,'POST');assert.equal(opts.redirect,'manual');
  assert.equal(opts.headers.Authorization,'Bearer sentinel-token');
  const req=JSON.parse(opts.body);methods.push(req.method);
  if(req.method==='initialize')return respond(init,200,{'Mcp-Session-Id':'sess-1'});
  assert.equal(opts.headers['Mcp-Session-Id'],'sess-1');
  if(req.method==='notifications/initialized')return new Response(null,{status:202});
  if(req.method==='tools/list')return respond({jsonrpc:'2.0',id:2,result:{tools:[{name:'list_workers',description:'SECRET'},{name:'list_workers'},{name:'invalid name;'},{name:'get_deploy'}]}});
  throw Error('unexpected_method');
 }});
 assert.deepEqual(methods,['initialize','notifications/initialized','tools/list']);
 assert.deepEqual(r,{status:'tools_discovered',tool_count:2,tool_names:['get_deploy','list_workers'],has_more:false});
 assert.equal(JSON.stringify(r).includes('sentinel-token'),false);
 assert.equal(JSON.stringify(r).includes('SECRET'),false);
});
test('SSE and pagination info without exposing cursor',async()=>{
 const sse='event: message\ndata: '+JSON.stringify({jsonrpc:'2.0',id:2,result:{tools:[{name:'workers_list'}],nextCursor:'SECRET'}})+'\n\n';
 const r=await discoverMcpTools({token:'test',transport:async(url,opts)=>{
  const req=JSON.parse(opts.body);
  if(req.method==='initialize')return respond(init);
  if(req.method==='notifications/initialized')return new Response(null,{status:202});
  return new Response(sse,{headers:{'content-type':'text/event-stream'}});
 }});
 assert.equal(r.status,'tools_discovered');assert.equal(r.has_more,true);assert.equal(JSON.stringify(r).includes('SECRET'),false);
});
test('refusal, redirects and errors never return server body or token',async()=>{
 for(const code of [401,403,302,500]){
  const r=await discoverMcpTools({token:'secret',transport:async()=>respond({error:'secret'},code)});
  assert.notEqual(r.status,'tools_discovered');
  assert.equal(JSON.stringify(r).includes('secret'),false);
 }
 const r=await discoverMcpTools({token:'secret',transport:async()=>respond({jsonrpc:'2.0',id:1,error:{message:'secret'}})});
 assert.equal(r.status,'invalid_initialization');
});
