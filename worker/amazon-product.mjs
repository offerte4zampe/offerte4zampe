// Direct Amazon.it affiliate links only. Server-side canonical product integration.
// Do not infer ASINs, fetch Amazon content, quote prices, or rank Amazon as a priced shop.
const ASIN=/^[A-Z0-9]{10}$/;
const TAG=/^[a-z0-9][a-z0-9-]*-21$/i;
const normalize=s=>String(s??'').trim().toLocaleLowerCase('it');
export const AMAZON_DISCLOSURE='In qualità di Affiliato Amazon io ricevo un guadagno dagli acquisti idonei';
export const AMAZON_PRICE_NOTICE='Il prezzo valido è quello indicato su Amazon al momento dell’acquisto.';

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
  matched.push(row.asin);
 }
 const unique=[...new Set(matched)];
 if(unique.length!==1)return null;
 return {url:'https://www.amazon.it/dp/'+unique[0]+'?tag='+encodeURIComponent(registry.tracking_id),asin:unique[0]};
}
