import test from 'node:test';
import assert from 'node:assert/strict';
import {probeCloudflareMcp, MCP_ENDPOINT} from './cloudflare-mcp-probe.mjs';
test('does not make requests without authorization', async () => {
 let calls=0;
 const result=await probeCloudflareMcp({transport:async()=>{calls++;throw Error('unexpected')}});
 assert.equal(result.status,'not_authorized');assert.equal(calls,0);
});
test('performs only MCP initialize with an exact endpoint',async()=>{
 let inspected=false;
 const result=await probeCloudflareMcp({token:'test-token',transport:async(url,opts)=>{
  inspected=true;assert.equal(url,MCP_ENDPOINT);
  assert.equal(opts.method,'POST');assert.equal(opts.redirect,'manual');
  assert.equal(opts.headers.Authorization,'Bearer test-token');
  assert.equal(JSON.parse(opts.body).method,'initialize');
  return {status:200,ok:true,headers:new Headers({'content-type':'application/json'})};
 }});
 assert.equal(inspected,true);assert.equal(result.status,'handshake_accepted');
});
test('never returns token or response body on unauthorized, server error or redirect',async()=>{
 for(const code of [401,403,302,500]){
  const response=await probeCloudflareMcp({token:'top-secret',transport:async()=>({status:code,ok:false,headers:new Headers(),text:async()=>'secret details'})});
  assert.equal(JSON.stringify(response).includes('top-secret'),false);
  assert.equal(JSON.stringify(response).includes('secret details'),false);
 }
});
