/** Fixed read-only Analytics Engine query. Only consented redirect aggregates;
 * sampled estimates, never visitors, orders, commissions or all outbound clicks. */
export async function outboundMetrics({token,accountId,transport=fetch,now=Date.now()}={}){
 if(typeof token!=='string'||!token.trim()||typeof accountId!=='string'||!/^[a-f0-9]{32}$/i.test(accountId))return {status:'outbound_not_configured'};
 if(!Number.isFinite(now)||now<0||now>8640000000000000||now<7*86400000)return {status:'outbound_invalid_time'};
 const end=new Date(now),start=new Date(now-7*86400000);
 const sqlDate=d=>d.toISOString().slice(0,19).replace('T',' ');
 const query=`SELECT blob1 AS merchant, SUM(_sample_interval) AS captured_redirects FROM offerte4zampe_outbound WHERE timestamp >= '${sqlDate(start)}' AND timestamp < '${sqlDate(end)}' GROUP BY merchant ORDER BY merchant LIMIT 101 FORMAT JSON`;
 const unavailable={status:'outbound_unavailable'};
 try{
  const res=await transport(`https://api.cloudflare.com/client/v4/accounts/${accountId}/analytics_engine/sql`,{method:'POST',redirect:'manual',headers:{Authorization:'Bearer '+token.trim(),'Content-Type':'text/plain',Accept:'application/json'},body:query,signal:AbortSignal.timeout(12000)});
  if(res.status===401||res.status===403)return {status:'outbound_not_authorized'};
  if(!res.ok||res.status>=300||!/application\/json/i.test(res.headers.get('content-type')||''))return unavailable;
  const text=await res.text();if(text.length>65536)return unavailable;
  const data=JSON.parse(text);
  if(data.errors?.length||!Array.isArray(data.data)||data.data.length>100||!Array.isArray(data.meta)||data.meta.length!==2||data.meta[0]?.name!=='merchant'||data.meta[1]?.name!=='captured_redirects')return unavailable;
  const merchants=[],seen=new Set();let total=0;
  for(const row of data.data){
   if(typeof row?.merchant!=='string'||!/^[a-z0-9][a-z0-9-]{0,79}$/.test(row.merchant)||seen.has(row.merchant))return unavailable;
   const value=row.captured_redirects;
   if(typeof value!=='number'&&!(typeof value==='string'&&/^(0|[1-9][0-9]*)$/.test(value)))return unavailable;
   const n=Number(value);if(!Number.isSafeInteger(n)||n<0)return unavailable;
   total+=n;if(!Number.isSafeInteger(total))return unavailable;
   seen.add(row.merchant);merchants.push({merchant:row.merchant,captured_redirects_estimate:n});
  }
  return {status:merchants.length?'outbound_available':'outbound_no_rows',window_start:start.toISOString().slice(0,19)+'Z',window_end:end.toISOString().slice(0,19)+'Z',window_days:7,measurement:'sample_weighted_consented_redirects_not_revenue',...(merchants.length?{captured_redirects_estimate:total,merchants}:{} )};
 }catch{return unavailable;}
}
