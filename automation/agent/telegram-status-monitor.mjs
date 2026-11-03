/** Read-only public status check. No bot token, no publish endpoint, no Telegram API calls. */
const STATUS_URL='https://offerte4zampe.it/api/telegram/status';
export async function checkTelegramStatus({transport=fetch,now=Date.now()}={}){
 try{
  const res=await transport(STATUS_URL,{method:'GET',redirect:'manual',signal:AbortSignal.timeout(12000),headers:{Accept:'application/json'}});
  if(res.status===401||res.status===403)return {status:'status_access_denied',http_status:res.status};
  if(!res.ok||res.status>=300)return {status:'status_unavailable',http_status:res.status};
  if(!/application\/json/i.test(res.headers.get('content-type')||''))return {status:'unexpected_content_type'};
  const raw=await res.text();
  if(raw.length>16384)return {status:'oversize_response'};
  const d=JSON.parse(raw);
  if(!d||d.integration!=='telegram-v1'||typeof d.configured!=='boolean'||typeof d.halted!=='boolean')return {status:'invalid_response'};
  if(!d.configured||d.channel_matches===false)return {status:'telegram_not_configured'};
  if(d.halted)return {status:'telegram_halted'};
  if(d.test_status!=='sent')return {status:'telegram_test_incomplete'};
  // No posts today is not automatically an error: no fresh product photos may exist.
  // Report a nonfatal freshness indicator, not an invented publishing failure.
  const day=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Rome',year:'numeric',month:'2-digit',day:'2-digit'}).format(now);
  return {status:'telegram_operational',last_sent_day:typeof d.last_sent_day==='string'?d.last_sent_day:null,
    sent_today:d.last_sent_day===day};
 }catch{return {status:'status_unavailable'};}
}
if(process.argv[1]&&import.meta.url===new URL('file://'+process.argv[1]).href){
 const r=await checkTelegramStatus();
 console.log(JSON.stringify(r));
 if(r.status==='status_access_denied'||r.status==='status_unavailable'){
  console.log('::warning::Telegram status cannot be verified from the GitHub runner; delivery state is unknown, not failed.');
 }else if(r.status!=='telegram_operational')process.exitCode=1;
}
