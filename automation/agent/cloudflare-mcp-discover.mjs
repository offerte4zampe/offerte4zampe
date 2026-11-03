/** Explicit, non-mutating MCP capability discovery.
 * Never invokes tools/call or Cloudflare account APIs.
 * Prints sanitized tool names/counts only, never tokens or resource data.
 */
export const MCP_ENDPOINT = 'https://mcp.cloudflare.com/mcp';
const PROTOCOL='2025-06-18';
function parseMessage(text,type){
 if(text.length>1048576)throw Error('response_too_large');
 if(/application\/json/i.test(type))return JSON.parse(text);
 if(/text\/event-stream/i.test(type)){
  for(const part of text.split(/\r?\n\r?\n/)){
   const data=part.split(/\r?\n/).filter(s=>s.startsWith('data:')).map(s=>s.slice(5).trim()).join('\n');
   if(!data||data==='[DONE]')continue;
   const item=JSON.parse(data);
   if(item?.jsonrpc==='2.0'&&Object.prototype.hasOwnProperty.call(item,'id'))return item;
  }
 }
 throw Error('invalid_mcp_response');
}
function cleanName(s){return typeof s==='string'&&/^[a-zA-Z0-9_.-]{1,96}$/.test(s)?s:null;}
export async function discoverMcpTools({token,transport=fetch}={}){
 if(typeof token!=='string'||!token.trim())return {status:'not_authorized'};
 let sessionId;
 const headers={Authorization:'Bearer '+token.trim(),'Content-Type':'application/json',Accept:'application/json, text/event-stream','MCP-Protocol-Version':PROTOCOL};
 async function send(body){
  const res=await transport(MCP_ENDPOINT,{method:'POST',redirect:'manual',headers:{...headers,...(sessionId?{'Mcp-Session-Id':sessionId}:{})},body:JSON.stringify(body),signal:AbortSignal.timeout(12000)});
  if(res.status===401||res.status===403)throw Error('not_authorized');
  if(res.status>=300&&res.status<400)throw Error('redirect_rejected');
  if(!res.ok)throw Error('remote_http_error');
  const sid=res.headers.get('mcp-session-id');
  if(sid&&/^[\w-]{1,256}$/.test(sid))sessionId=sid;
  return res;
 }
 try{
  const init=await send({jsonrpc:'2.0',id:1,method:'initialize',params:{protocolVersion:PROTOCOL,capabilities:{},clientInfo:{name:'offerte4zampe-capabilities-only',version:'0.2.0'}}});
  const initType=init.headers.get('content-type')||'';
  if(!/application\/json|text\/event-stream/i.test(initType))return {status:'invalid_initialization'};
  const initData=parseMessage(await init.text(),initType);
  if(initData.id!==1||!initData.result||initData.error)return {status:'invalid_initialization'};
  const notif=await send({jsonrpc:'2.0',method:'notifications/initialized'});
  if(notif.body)await notif.body.cancel();
  const res=await send({jsonrpc:'2.0',id:2,method:'tools/list',params:{}});
  const type=res.headers.get('content-type')||'';
  if(!/application\/json|text\/event-stream/i.test(type))return {status:'unexpected_response'};
  const data=parseMessage(await res.text(),type);
  if(data.id!==2||!Array.isArray(data.result?.tools)||data.error)return {status:'invalid_tools_list'};
  const unique=[...new Set(data.result.tools.map(t=>cleanName(t?.name)).filter(Boolean))].sort();
  return {status:'tools_discovered',tool_count:unique.length,tool_names:unique,has_more:Boolean(data.result.nextCursor)};
 }catch(e){
  const msg=String(e?.message||'');
  return {status:['not_authorized','redirect_rejected','remote_http_error','response_too_large'].includes(msg)?msg:'discovery_failed'};
 }
}
if(process.argv[1]&&import.meta.url===new URL('file://'+process.argv[1]).href){
 const result=await discoverMcpTools({token:process.env.CLOUDFLARE_MCP_TOKEN});
 console.log(JSON.stringify(result));
 if(result.status!=='tools_discovered')process.exitCode=1;
}
