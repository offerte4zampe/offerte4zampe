/** Dry-run, read-only planner for a future Cloudflare Code Mode agent.
 * Does not publish, make network requests, invent discounts or handle secrets.
 */
const HOSTS={bauzaar:'cdn.shopify.com','isola-dei-tesori':'www.isoladeitesori.it',paco:'www.pacopetshop.it'};
const DAY=86400000;
function fresh(s,now){const t=typeof s==='string'?Date.parse(s):NaN;return Number.isFinite(t)&&t<=now&&now-t<=DAY;}
function photo(o){try{const u=new URL(o.image);return u.protocol==='https:'&&!u.username&&!u.password&&u.hostname===HOSTS[o.merchant_id]&&/\.(png|jpe?g)$/i.test(u.pathname);}catch{return false;}}
function valid(o,s,now){
 if(!o||!s||s.id!==o.merchant_id||s.status!=='ok'||!fresh(s.checked_at,now)||!fresh(o.checked_at,now))return false;
 if(o.available!==true||!Number.isFinite(o.price)||o.price<=0||!Number.isFinite(o.weight_kg)||o.weight_kg<=0||!photo(o))return false;
 if(typeof o.id!=='string'||!o.id||o.id.length>200||typeof o.title!=='string'||!o.title.trim()||o.title.length>240||typeof o.merchant!=='string'||!o.merchant.trim())return false;
 return Boolean(String(o.variant||o.canonical_format||'').trim()||/\d+(?:[.,]\d+)?\s*(?:kg|g|gr|grammi|ml|l)\b/i.test(o.title));
}
export function planVerifiedOffers(catalog,{now=Date.now(),maxCandidates=5}={}){
 if(!Number.isFinite(now)||!Number.isSafeInteger(maxCandidates)||maxCandidates<1||maxCandidates>20)throw new TypeError('invalid_planner_options');
 if(!catalog||!Array.isArray(catalog.offers)||!Array.isArray(catalog.sources))return {status:'invalid_catalog',publish:false,candidates:[],reviewed:0};
 const sources=new Map(catalog.sources.filter(s=>s&&typeof s.id==='string').map(s=>[s.id,s]));
 const candidates=[],seen=new Set();
 for(const o of catalog.offers.slice(0,50000)){
  if(!valid(o,sources.get(o?.merchant_id),now)||seen.has(o.id))continue;
  seen.add(o.id);
  const path=typeof o.product_url==='string'&&/^\/prodotto\/[a-z0-9-]{1,200}$/.test(o.product_url)?o.product_url:'/prodotto?id='+encodeURIComponent(o.id);
  candidates.push({id:o.id,merchant_id:o.merchant_id,price:o.price,price_per_kg:Math.round(100*o.price/o.weight_kg)/100,checked_at:o.checked_at,path,image:o.image});
  if(candidates.length>=maxCandidates)break;
 }
 return {status:candidates.length?'ready_for_review':'no_verified_offers',publish:false,candidates,reviewed:Math.min(catalog.offers.length,50000)};
}
