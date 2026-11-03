/** Account-scoped, read-only Cloudflare Worker audit via official Code Mode MCP.
 * Fixed tool sequence: initialize -> notifications/initialized -> whoami -> execute.
 * The execute code contains one hard-coded GET; no dynamic model-written code.
 * Tokens, account IDs and full API responses are never printed.
 */
const ENDPOINT='https://mcp.cloudflare.com/mcp';
const VERSION='2025-06-18';
const WORKER='zampachiara';
const SCRIPT=String.raw`async () => {
  const r = await cloudflare.request({method: "GET", path: "/accounts/" + accountId + "/workers/scripts"});
  const scripts = Array.isArray(r?.result) ? r.result : [];
  const worker = scripts.find(s => s?.id === "zampachiara" || s?.name === "zampachiara");
  const d = await cloudflare.request({method: "GET", path: "/accounts/" + accountId + "/workers/scripts/zampachiara/deployments?per_page=5"});
  const deployments = d?.result?.deployments;
  const latest = Array.isArray(deployments) ? deployments[0] : null;
  return {api_success: r?.success === true, worker_found: Boolean(worker), modified_on: worker?.modified_on || null,
    deploy_readable: d?.success === true && Array.isArray(deployments),
    latest_deploy_at: typeof latest?.created_on === "string" ? latest.created_on : null,
    version_count: Array.isArray(latest?.versions) ? latest.versions.length : null};
}`;
function messageFromText(body,type){
 if(body.length>1048576)throw Error('oversize');
 if(/application\/json/i.test(type))return JSON.parse(body);
 if(/text\/event-stream/i.test(type)){
  for(const part of body.split(/\r?\n\r?\n/)){
   const data=part.split(/\r?\n/).filter(s=>s.startsWith('data:')).map(s=>s.slice(5).trim()).join('\n');
   if(!data||data==='[DONE]')continue;
   const json=JSON.parse(data);
   if(json.jsonrpc==='2.0'&&Object.prototype.hasOwnProperty.call(json,'id'))return json;
  }
 }
 throw Error('bad_mcp_reply');
}
function embedded(v){
 if(v?.structuredContent&&typeof v.structuredContent==='object')return v.structuredContent;
 const t=v?.content?.find(c=>c?.type==='text'&&typeof c.text==='string')?.text;
 if(!t||t.length>1048576)return null;
 try{return JSON.parse(t);}catch{return null;}
}
export async function auditCloudflareWorker({token,accountId,transport=fetch}={}){
 if(typeof token!=='string'||!token.trim())return {status:'missing_token'};
 if(accountId && !/^[a-f0-9]{32}$/i.test(accountId))return {status:'invalid_account_id'};
 let sessionId;
 const headers={Authorization:'Bearer '+token.trim(),'Content-Type':'application/json',Accept:'application/json, text/event-stream','MCP-Protocol-Version':VERSION};
 async function send(body,notification=false){
  const res=await transport(ENDPOINT,{method:'POST',redirect:'manual',headers:{...headers,...(sessionId?{'Mcp-Session-Id':sessionId}:{})},body:JSON.stringify(body),signal:AbortSignal.timeout(15000)});
  if(res.status===401||res.status===403)throw Error('not_authorized');
  if(!res.ok||res.status>=300)throw Error('http_failure');
  const sid=res.headers.get('mcp-session-id');
  if(sid&&/^[a-zA-Z0-9_-]{1,256}$/.test(sid))sessionId=sid;
  if(notification){if(res.body)await res.body.cancel();return null;}
  const type=res.headers.get('content-type')||'';
  if(!/application\/json|text\/event-stream/i.test(type))throw Error('unexpected_content_type');
  return messageFromText(await res.text(),type);
 }
 try{
  const init=await send({jsonrpc:'2.0',id:1,method:'initialize',params:{protocolVersion:VERSION,capabilities:{},clientInfo:{name:'offerte4zampe-worker-readonly-audit',version:'1.0.0'}}});
  if(init?.id!==1||!init.result||init.error) return {status:'initialize_failed'};
  await send({jsonrpc:'2.0',method:'notifications/initialized'},true);
  const identity=await send({jsonrpc:'2.0',id:2,method:'tools/call',params:{name:'whoami',arguments:{}}});
  const profile=embedded(identity?.result);
  const id=profile?.id||profile?.result?.id;
  if(identity?.id!==2||identity.result?.isError||typeof id!=='string'||!(/^(account|user):/.test(id)))return {status:'identity_unverified'};
  const accountToken=id.startsWith('account:');
  const resolved=accountToken?id.slice(8):accountId;
  if(!resolved||!/^[a-f0-9]{32}$/i.test(resolved))return {status:'account_id_required'};
  // Account tokens are fixed to their authenticated account; user tokens need an explicit account ID.
  if(accountToken&&accountId&&accountId.toLowerCase()!==resolved.toLowerCase())return {status:'account_mismatch'};
  const exec=await send({jsonrpc:'2.0',id:3,method:'tools/call',params:{name:'execute',arguments:{code:SCRIPT,account_id:resolved}}});
  const details=embedded(exec?.result);
  const data=details?.result?.api_success!==undefined?details.result:details;
  if(exec?.id!==3||exec.result?.isError||data?.api_success!==true)return {status:'workers_read_failed'};
  if(data?.worker_found!==true)return {status:'worker_not_found'};
  return {status:'worker_verified',worker:WORKER,modified_on:typeof data.modified_on==='string'?data.modified_on:null,
   deploy_status:data.deploy_readable===true?(typeof data.latest_deploy_at==='string'?'available':'no_deployments'):'not_accessible',
   latest_deploy_at:typeof data.latest_deploy_at==='string'?data.latest_deploy_at:null,
   active_version_count:Number.isSafeInteger(data.version_count)?data.version_count:null};
 }catch(e){
  const s=String(e?.message||'');
  return {status:s==='not_authorized'?'not_authorized':'audit_failed'};
 }
}
if(process.argv[1]&&import.meta.url===new URL('file://'+process.argv[1]).href){
 const r=await auditCloudflareWorker({token:process.env.CLOUDFLARE_MCP_TOKEN,accountId:process.env.CLOUDFLARE_ACCOUNT_ID});
 console.log(JSON.stringify(r));
 if(r.status!=='worker_verified')process.exitCode=1;
}
