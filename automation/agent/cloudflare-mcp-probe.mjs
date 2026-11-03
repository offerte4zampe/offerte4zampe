/** Read-only handshake with Cloudflare's official MCP endpoint.
 * Requires an explicit Cloudflare API token in the environment; never logs it.
 * Does not list or invoke Cloudflare tools, change resources or perform OAuth.
 */
export const MCP_ENDPOINT = 'https://mcp.cloudflare.com/mcp';
export async function probeCloudflareMcp({token, transport = fetch} = {}) {
  if (typeof token !== 'string' || !token.trim()) return {status:'not_authorized'};
  let res;
  try {
    res = await transport(MCP_ENDPOINT, {
      method:'POST',
      redirect:'manual',
      headers: {
        Authorization:'Bearer ' + token.trim(),
        'Content-Type':'application/json',
        Accept:'application/json, text/event-stream',
        'MCP-Protocol-Version':'2025-06-18'
      },
      body:JSON.stringify({jsonrpc:'2.0',id:1,method:'initialize',params:{
        protocolVersion:'2025-06-18',
        capabilities:{},
        clientInfo:{name:'offerte4zampe-readonly-probe',version:'0.1.0'}
      }}),
      signal:AbortSignal.timeout(10000)
    });
  } catch {return {status:'network_error'};}
  if (res.status===401||res.status===403) return {status:'not_authorized'};
  if (res.status>=300&&res.status<400) return {status:'redirect_requires_review'};
  if (!res.ok) return {status:'http_error',http_status:res.status};
  const type=res.headers.get('content-type')||'';
  if (!/application\/json|text\/event-stream/i.test(type)) return {status:'unexpected_response'};
  return {status:'handshake_accepted',http_status:res.status};
}
if (process.argv[1] && import.meta.url===new URL('file://' + process.argv[1]).href) {
  const status=await probeCloudflareMcp({token:process.env.CLOUDFLARE_MCP_TOKEN});
  console.log(JSON.stringify(status));
  if(status.status!=='handshake_accepted') process.exitCode=1;
}
