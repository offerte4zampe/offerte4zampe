import trade from '../site/assets/trade.js';
import {slugForOffer} from './canonical-product.mjs';
const HEADERS={'Cache-Control':'no-store','X-Robots-Tag':'noindex, nofollow','Referrer-Policy':'no-referrer'};
const PAGES=new Set(['home','catalog','product','basket','other']);
function redirect(location){return new Response(null,{status:302,headers:{...HEADERS,Location:location}})}
async function json(env,origin,path){const r=await env.ASSETS.fetch(new Request(new URL(path,origin)));if(!r.ok)throw Error('snapshot unavailable');return r.json()}
// Only the audited merchants and their existing affiliate network may use the
// redirect-only archive. This does not accept a target supplied by the request.
function archivedTargetAllowed(o,target){
 const hosts={bauzaar:'www.bauzaar.it',webpet:'www.webpet.it',animaliapet:'www.animaliapet.eu','isola-dei-tesori':'www.isoladeitesori.it',paco:'www.pacopetshop.it'};
 try{
  const direct=new URL(o.url),destination=new URL(target),host=hosts[o.merchant_id];
  if(!host||direct.protocol!=='https:'||direct.hostname!==host||direct.username||direct.password||direct.port||destination.port)return false;
  if(destination.hostname===host)return target===o.url;
  const campaigns={bauzaar:{c:'16143',m:'600171'},'isola-dei-tesori':{c:'31221',m:'1618255'}},campaign=campaigns[o.merchant_id];
  if(!campaign||destination.hostname!=='tc.tradetracker.net'||destination.pathname!=='/'||destination.hash)return false;
  const expected={...campaign,a:'518044',u:o.url};
  if(!Object.entries(expected).every(([key,value])=>destination.searchParams.getAll(key).length===1&&destination.searchParams.get(key)===value))return false;
  const nested=new URL(destination.searchParams.get('u'));
  return nested.protocol==='https:'&&nested.hostname===host&&!nested.username&&!nested.password&&!nested.port&&nested.href===direct.href;
 }catch{return false}
}
function consent(request){
 const cookies=(request.headers.get('Cookie')||'').split(';').map(x=>x.trim()).filter(x=>x.startsWith('__Host-o4z-statistics='));
 return cookies.length===1&&cookies[0]==='__Host-o4z-statistics=yes'&&request.headers.get('Sec-GPC')!=='1'&&request.headers.get('DNT')!=='1';
}
export async function outbound(request,env,ctx,now=Date.now()){
 if(!['GET','HEAD'].includes(request.method))return new Response(null,{status:405,headers:{...HEADERS,Allow:'GET, HEAD'}});
 const u=new URL(request.url);let id;try{id=decodeURIComponent(u.pathname.slice(4))}catch{return redirect('/confronta-cibo')}
 if(!id||id.length>200||/[\x00-\x1f\x7f/]/.test(id))return redirect('/confronta-cibo');
 let slug,p,o,suppressed=false;
 try{slug=await slugForOffer(env,u.origin,id)}catch{/* A withheld row can retain its existing merchant redirect below. */}
 if(slug&&!/^[a-z0-9-]{1,200}$/.test(slug))return redirect('/confronta-cibo');
 const fallback=slug?'/prodotto/'+slug:'/confronta-cibo';
 if(slug){
  try{
   const hash=new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(slug)))[0].toString(16).padStart(2,'0');
   const shard=await json(env,u.origin,'/data/canonical-products/'+hash+'.json');p=Object.hasOwn(shard,slug)?shard[slug]:null;
   o=p?.offers?.find(x=>x.id===id);
  }catch{/* Try only the exact original row retained by the commercial audit. */}
 }
 if(!o){
  try{
   const audit=await json(env,u.origin,'/data/store-audit.json');
   const record=audit?.commercial_suppression?.withheld?.find(x=>x.id===id&&x.offer?.id===id);
   if(record){o=record.offer;suppressed=true;}
  }catch{/* Missing audit evidence never creates a redirect target. */}
 }
 const stamp=Date.parse(o?.checked_at),expiry=Date.parse(o?.identity_expires_at);
 const target=o&&trade.merchantUrl(o);
 if(!target||suppressed&&!archivedTargetAllowed(o,target)||!o.available||!Number.isFinite(stamp)||stamp>now+300000||now-stamp>36*3600000||o.identity_review&&(!Number.isFinite(expiry)||expiry<now))return redirect(fallback);
 // No network analytics call, request object, IP, full referrer or visitor identifier.
 // Telemetry must never break navigation, including missing/rejected bindings.
 if(!suppressed&&request.method==='GET'&&consent(request)&&ctx?.waitUntil&&env.OUTBOUND_CLICKS&&!request.headers.get('Purpose')?.includes('prefetch')&&!request.headers.get('Sec-Purpose')?.includes('prefetch')){
  const cents=Math.round(o.price*100),page=PAGES.has(u.searchParams.get('from'))?u.searchParams.get('from'):'other';
  if(Number.isSafeInteger(cents)&&cents>=0){
   try{ctx.waitUntil(Promise.resolve().then(()=>env.OUTBOUND_CLICKS.writeDataPoint({indexes:[String(o.merchant_id).slice(0,80)],blobs:[String(o.merchant_id),String(p.id),String(o.id),page],doubles:[cents]})).catch(()=>{}))}catch{}
  }
 }
 return redirect(target);
}
