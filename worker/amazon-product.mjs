// Direct Amazon.it affiliate links only. Server-side canonical product integration.
// Do not infer ASINs, fetch Amazon content, quote prices, or rank Amazon as a priced shop.
const ASIN=/^[A-Z0-9]{10}$/;
const TAG=/^[a-z0-9][a-z0-9-]*-21$/i;
const normalize=s=>String(s??'').trim().toLocaleLowerCase('it');
export const AMAZON_DISCLOSURE='In qualità di Affiliato Amazon io ricevo un guadagno dagli acquisti idonei';
export const AMAZON_PRICE_NOTICE='Il prezzo valido è quello indicato su Amazon al momento dell’acquisto.';

function curatedURL(row,tag){
 if(!Object.hasOwn(row,'sitestripe_url'))return 'https://www.amazon.it/dp/'+row.asin+'?tag='+encodeURIComponent(tag);
 if(row.owner_variant_confirmed!==true||row.resolved_tracking_id!==tag||row.resolved_asin!==row.asin)return null;
 try{const u=new URL(row.sitestripe_url);if(u.protocol!=='https:'||u.hostname!=='link.amazon'||u.port||u.username||u.password||u.search||u.hash||!/^\/[A-Za-z0-9]{9}$/.test(u.pathname))return null;return row.sitestripe_url;}catch{return null}
}

export function resolveAmazonOffer(product,registry,now=Date.now()){
 if(!Array.isArray(product?.offers)||!TAG.test(registry?.tracking_id||'')||!Array.isArray(registry?.links))return null;
 const matched=[];
 for(const row of registry.links){
  if(!ASIN.test(row?.asin||''))continue;
  const stamp=Date.parse(String(row.checked_at||'')+'T00:00:00Z');
  if(!Number.isFinite(stamp)||stamp>now||now-stamp>30*86400000)continue;
  const offer=product.offers.find(o=>o.id===row.offer_id);
  if(!offer)continue;
  if(!['brand','title','variant','gtin'].every(k=>normalize(row[k])===normalize(offer[k])))continue;
  try {
   const e=new URL(row.evidence_url);
   if(e.protocol!=='https:'||e.hostname!=='www.amazon.it'||e.username||e.password||!e.pathname.endsWith('/dp/'+row.asin))continue;
  }catch{continue}
  const url=curatedURL(row,registry.tracking_id);if(!url)continue;
  matched.push({asin:row.asin,url});
 }
 const unique=[...new Set(matched.map(m=>m.asin))];
 if(unique.length!==1)return null;
 return matched[0];
}
