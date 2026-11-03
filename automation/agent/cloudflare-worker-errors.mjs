/** Aggregated, read-only Worker error metrics. Never download raw visitor logs.
 * Cloudflare GraphQL accepts POST for a query; no GraphQL mutations are used.
 */
export async function workerErrorMetrics({token,accountId,transport=fetch,now=Date.now()}={}){
 if(typeof token!=='string'||!token.trim()||typeof accountId!=='string'||!/^[0-9a-f]{32}$/i.test(accountId))return {status:'metrics_not_configured'};
 const end=new Date(now),start=new Date(now-24*3600000);
 if(!Number.isFinite(now))return {status:'invalid_time'};
 const query='query WorkerErrors($accountTag: string!, $start: Time!, $end: Time!, $scriptName: string!) { viewer { accounts(filter: {accountTag: $accountTag}) { workersInvocationsAdaptive(limit: 100, filter: {scriptName: $scriptName, datetime_geq: $start, datetime_leq: $end}) { sum { requests errors } } } } }';
 try{
  const res=await transport('https://api.cloudflare.com/client/v4/graphql',{
   method:'POST',redirect:'manual',
   headers:{Authorization:'Bearer '+token.trim(),'Content-Type':'application/json',Accept:'application/json'},
   body:JSON.stringify({query,variables:{accountTag:accountId,start:start.toISOString(),end:end.toISOString(),scriptName:'zampachiara'}}),
   signal:AbortSignal.timeout(12000)
  });
  if(res.status===401||res.status===403)return {status:'metrics_not_authorized'};
  if(!res.ok||res.status>=300||!/application\/json/.test(res.headers.get('content-type')||''))return {status:'metrics_unavailable'};
  const raw=await res.text();if(raw.length>65536)return {status:'metrics_unavailable'};
  const data=JSON.parse(raw);
  if(data.errors?.length||!Array.isArray(data.data?.viewer?.accounts)||data.data.viewer.accounts.length!==1)return {status:'metrics_unavailable'};
  const rows=data.data.viewer.accounts[0]?.workersInvocationsAdaptive;
  if(!Array.isArray(rows))return {status:'metrics_unavailable'};
  let requests=0,errors=0;
  for(const row of rows){
   const r=row?.sum?.requests,e=row?.sum?.errors;
   if(!Number.isSafeInteger(r)||r<0||!Number.isSafeInteger(e)||e<0||e>r)return {status:'metrics_unavailable'};
   requests+=r;errors+=e;
  }
  if(!Number.isSafeInteger(requests)||!Number.isSafeInteger(errors))return {status:'metrics_unavailable'};
  const error_rate=requests?Math.round(10000*errors/requests)/100:0;
  return {status:'metrics_available',window_hours:24,requests,errors,error_rate_pct:error_rate,alert:requests>=50&&errors>=5&&error_rate>=5};
 }catch{return {status:'metrics_unavailable'};}
}
