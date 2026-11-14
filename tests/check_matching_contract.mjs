// Calls the actual Worker in memory; no external network, consent, telemetry or redirect following.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';
import {pathToFileURL,fileURLToPath} from 'node:url';
export function verifyRedirectResponse(response,expected){
 assert.equal(response.status,302);
 assert.equal(response.headers.get('Location'),expected);
 assert.equal(response.headers.get('X-Robots-Tag'),'noindex, nofollow');
}
async function responses(root){
 const {outbound}=await import(pathToFileURL(path.join(root,'worker/outbound.mjs')));
 const rows=JSON.parse(gunzipSync(fs.readFileSync(path.join(root,'site/data/catalog.json.gz')))).offers;
 const cache=new Map(),result={};
 const env={ASSETS:{fetch:async req=>{
  const p=new URL(req.url).pathname;
  if(!cache.has(p))cache.set(p,fs.readFileSync(path.join(root,'site',p)));
  return new Response(cache.get(p),{headers:{'Content-Type':'application/json'}});
 }}};
 for(const o of rows){
  const r=await outbound(new Request('https://offerte4zampe.it/go/'+encodeURIComponent(o.id),{method:'HEAD'}),env,null,Date.parse(o.checked_at));
  assert.equal(r.status,302,o.id);assert.equal(r.headers.get('X-Robots-Tag'),'noindex, nofollow',o.id);
  if(o.available&&(!o.identity_review||Date.parse(o.identity_expires_at)>=Date.parse(o.checked_at))){
   verifyRedirectResponse(r,o.affiliate_url||o.url);
   result[o.id]=[r.status,r.headers.get('Location'),r.headers.get('X-Robots-Tag')];
  }
 }
 return result;
}
if(process.argv[1]===fileURLToPath(import.meta.url)){
 const [base,head]=process.argv.slice(2);
 const left=await responses(base),right=await responses(head);
 assert.deepEqual(left,right);
 console.log(JSON.stringify({active_redirect_responses:Object.keys(right).length,status:302,location:'byte-identical',robots:'noindex, nofollow',redirects_followed:false}));
}
