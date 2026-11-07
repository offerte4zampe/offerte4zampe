(function(root){'use strict';
const metadata=typeof module!=='undefined'&&module.exports?require('./catalog-metadata.js'):root.O4ZMetadata;
// Data adapter only: all fee/threshold/weight calculations stay in shipping().
function shippingRulesFromRows(rows,now=Date.now(),zone='IT'){
 const merchants=Object.create(null),selected=new Map();
 for(const row of rows){
  const start=Date.parse(row.valid_from),end=row.valid_to==null?Infinity:Date.parse(row.valid_to);
  if(row.zone!==zone||!Number.isFinite(start)||Number.isNaN(end)||start>now||end<=now)continue;
  const prior=selected.get(row.shop_id);if(!prior||Date.parse(prior.valid_from)<start)selected.set(row.shop_id,row);
 }
 for(const [id,row] of selected){
  const r={name:row.shop_name||id,status:row.status,checked_at:row.verified_at,verified_until:row.verified_until,valid_from:row.valid_from,valid_to:row.valid_to,source:row.source_url,note:row.notes};
  if(row.status==='uncertain')r.conflict=true;
  if(row.status==='verified'){
   if(!Number.isSafeInteger(row.std_cents)||row.std_cents<0)throw Error('Invalid shipping fee');
   r.fee=row.std_cents/100;
   if(row.free_from_cents!=null){
    if(!Number.isSafeInteger(row.free_from_cents)||row.free_from_cents<0||!['inclusive','exclusive','unknown'].includes(row.threshold_mode))throw Error('Invalid shipping threshold');
    if(row.threshold_mode==='inclusive')r.free_from=row.free_from_cents/100;
    else {r.free_above=row.free_from_cents/100;if(row.threshold_mode==='unknown')r.boundary_unknown=row.free_from_cents/100;}
   }
  }
  if(row.max_weight_g!=null){if(!Number.isSafeInteger(row.max_weight_g)||row.max_weight_g<=0)throw Error('Invalid shipping weight');r.max_shipping_weight_kg=row.max_weight_g/1000;}
  merchants[id]=r;
 }
 return {merchants};
}
function shipping(o,rules,quantity=1,territory='standard',now=Date.now()){
 const destination=territory==='standard'?'Italia continentale standard: esclusi isole, CAP disagiati, Livigno, Campione e servizi opzionali':'Località o servizi particolari';
 const unknown=reason=>({status:'unknown',destination,reason});
 if(!o||o.quantity_verified===false||o.quantity?.verified===false)return unknown('Formato della confezione non verificato: totale non confrontabile');
 if(!Number.isFinite(now)||!Number.isFinite(o.price)||o.price<=0||!Number.isSafeInteger(Math.round(o.price*quantity*100)))return unknown('Prezzo o quantità non validi: totale non calcolato');
 const stamp=Date.parse(o.checked_at);
 if(!Number.isFinite(stamp)||stamp>now+300000)return unknown('Data del prezzo non valida: totale non calcolato');
 const result=shippingExact(o,rules,quantity,territory,now);
 if(['range','from'].includes(result.status))return {...result,destination};
 if(!Number.isFinite(result.fee)||result.fee<0||!Number.isFinite(result.total)||result.total<0){
  const {fee,total,...details}=result;
  return {...details,...unknown(result.reason||'Tariffa non verificabile: totale non calcolato')};
 }
 return {...result,status:'exact',destination};
}
function shippingExact(o,rules,quantity=1,territory='standard',now=Date.now()){
 if(o.quantity_verified===false)return {reason:'Formato della confezione non verificato: totale non confrontabile'};
 const r=rules?.merchants?.[o.merchant_id];if(!r)return {reason:'Condizioni non disponibili'};
 const ruleDate=r.checked_at||rules.checked_at,observed=Date.parse(ruleDate),until=r.verified_until!==undefined?Date.parse(r.verified_until):observed+(rules.verification_max_age_days??7)*86400000;
 // Seven days is retained only for older cached payloads; new JSON/D1 rows own expiry.
 if(!Number.isFinite(observed)||!Number.isFinite(until)||until<observed||now>=until||observed>now+300000||(r.valid_from!==undefined&&(!Number.isFinite(Date.parse(r.valid_from))||Date.parse(r.valid_from)>now))||(r.valid_to!=null&&(!Number.isFinite(Date.parse(r.valid_to))||Date.parse(r.valid_to)<=now)))return {reason:'Condizioni da ricontrollare',rule:r};
 if(r.status&&r.status!=='verified'&&!r.conflict)return {reason:'Condizioni non verificate: verifica il checkout',rule:r};
 if(territory!=='standard')return {reason:'Località o servizi particolari: verifica nel negozio',rule:r};
 if(!Number.isInteger(quantity)||quantity<1||quantity>10)return {reason:'Quantità non valida',rule:r};
 if(r.conflict)return {reason:'Indicazioni del negozio non coerenti: verifica il checkout',rule:r};
 if(now-Date.parse(o.checked_at)>36*3600000||!Number.isFinite(Date.parse(o.checked_at)))return {reason:'Prezzo non recente: totale non calcolato',rule:r};
 const subtotal=Math.round(o.price*quantity*100)/100;
 if(r.boundary_unknown===subtotal)return {reason:'Soglia esatta da verificare nel negozio',rule:r};
 if(o.shipping_weight_checked_at&&(!Number.isFinite(Date.parse(o.shipping_weight_checked_at))||now-Date.parse(o.shipping_weight_checked_at)>7*86400000))return {reason:'Peso di spedizione da aggiornare',rule:r};
 if(r.max_shipping_weight_kg&&(!(o.shipping_weight_kg>0)||o.shipping_weight_kg*quantity>r.max_shipping_weight_kg))return {reason:'Peso di spedizione mancante o supplementi possibili',rule:r};
 // Optional bounds must come from a verified current source, never inferred from unknown rules.
 const bounds=r.quote_bounds;
 if(bounds){
  const source=(()=>{try{return new URL(r.source).protocol==='https:'}catch{return false}})();
  if(r.status!=='verified'||!source||typeof r.checked_at!=='string'||typeof r.verified_until!=='string'||bounds.territory!==territory||bounds.quantity!==quantity||!['range','from'].includes(bounds.kind)||!Number.isFinite(bounds.fee_min)||bounds.fee_min<0||!Number.isSafeInteger(Math.round((subtotal+bounds.fee_min)*100))||r.free_from!==undefined||r.free_above!==undefined)return {reason:'Intervallo di spedizione non verificabile',rule:r};
  const total_min=Math.round((subtotal+bounds.fee_min)*100)/100;
  if(bounds.kind==='range'){
   if(!Number.isFinite(bounds.fee_max)||bounds.fee_max<bounds.fee_min||!Number.isSafeInteger(Math.round((subtotal+bounds.fee_max)*100)))return {reason:'Intervallo di spedizione non verificabile',rule:r};
   return {status:'range',subtotal,fee_min:bounds.fee_min,fee_max:bounds.fee_max,total_min,total_max:Math.round((subtotal+bounds.fee_max)*100)/100,reason:'Intervallo documentato per la destinazione e la quantità selezionate; importo finale nel checkout',rule:r};
  }
  if(bounds.fee_max!==undefined)return {reason:'Limite di spedizione non verificabile',rule:r};
  return {status:'from',subtotal,fee_min:bounds.fee_min,total_min,reason:'Costo minimo documentato; supplementi e importo finale da verificare nel checkout',rule:r};
 }
 const fee=(r.free_from!==undefined&&subtotal>=r.free_from)||(r.free_above!==undefined&&subtotal>r.free_above)?0:r.fee;
 return {subtotal,fee,total:Math.round((subtotal+fee)*100)/100,rule:r};
}
// The feeds expose comparison/list prices, not a verified reduction basis.
// Keep promotional percentages disabled until an evidenced source is integrated.
function merchantPromotion(o,now=Date.now()){
 const p=o.merchant_promotion;if(!p||!['shopify_compare_at','feed_regular_price'].includes(p.kind)||o.available!==true||o.quantity_verified===false||o.weight_conflict)return null;
 if(p.offer_id!==o.id||o.url&&p.source_url!==o.url||p.observed_at!==o.checked_at||p.price_cents!==Math.round(o.price*100))return null;
 try{const u=new URL(p.source_url);if(u.protocol!=='https:'||u.username||u.password||!['webpet.it','www.webpet.it','animaliapet.eu','www.animaliapet.eu','bauzaar.it','www.bauzaar.it','pacopetshop.it','www.pacopetshop.it'].includes(u.hostname))return null}catch{return null}
 const stamp=Date.parse(p.observed_at),end=p.valid_until?Date.parse(p.valid_until):null;
 if(!Number.isFinite(stamp)||now-stamp>12*3600000||stamp>now+300000||end!==null&&(!Number.isFinite(end)||now>end))return null;
 const ref=p.reference_cents,price=p.price_cents;if(!Number.isSafeInteger(ref)||!Number.isSafeInteger(price)||!(0<price&&price<ref&&ref<10000000))return null;
 return {reference_cents:ref,saved_cents:ref-price,percent:Math.floor((ref-price)*1000/ref)/10};
}
function merchantPromotionHTML(o,now=Date.now()){
 const p=merchantPromotion(o,now);if(!p)return '';
 const euro=n=>new Intl.NumberFormat('it-IT',{style:'currency',currency:'EUR'}).format(n/100),percent=new Intl.NumberFormat('it-IT',{maximumFractionDigits:1}).format(p.percent);
 return '<span class="merchant-promo" data-merchant-promo><span class="merchant-promo-badge">−'+percent+'% · PROMO NEGOZIO</span><span class="merchant-promo-reference">Rif. negozio <s>'+euro(p.reference_cents)+'</s></span><span class="merchant-promo-saving">Risparmi '+euro(p.saved_cents)+' sul riferimento</span></span>';
}
function appendMerchantPromotion(parent,o,now=Date.now()){const html=merchantPromotionHTML(o,now);if(html){const template=document.createElement('template');template.innerHTML=html;parent.append(template.content)}}
function discount(o,now=Date.now()){return Boolean(merchantPromotion(o,now))}
function merchant(url){
 try{const u=new URL(url);if(u.protocol!=='https:'||u.username||u.password)return '';if(['www.amazon.it','amazon.it'].includes(u.hostname)&&/^\/dp\/[A-Z0-9]{10}\/?$/.test(u.pathname)&&u.searchParams.getAll('tag').length===1&&u.searchParams.get('tag')==='offerte4zam02-21')return 'Amazon';const shops={'www.pacopetshop.it':'Paco Pet Shop','pacopetshop.it':'Paco Pet Shop','www.isoladeitesori.it':'Isola dei Tesori','isoladeitesori.it':'Isola dei Tesori','www.bauzaar.it':'Bauzaar','bauzaar.it':'Bauzaar','webpet.it':'WebPet','www.webpet.it':'WebPet','animaliapet.eu':'Animaliapet','www.animaliapet.eu':'Animaliapet'};if(shops[u.hostname])return shops[u.hostname];if(u.hostname==='tc.tradetracker.net'&&u.searchParams.get('c')==='16143'&&u.searchParams.get('a')==='518044')return 'Bauzaar';if(u.hostname==='tc.tradetracker.net'&&u.searchParams.get('c')==='31221'&&u.searchParams.get('a')==='518044')return 'Isola dei Tesori';return ''}catch{return ''}
}
function matchKey(o,now=Date.now()){
 if(o.quantity_verified===false||o.weight_conflict)return '';
 if(o.identity_review&&(!Number.isFinite(Date.parse(o.identity_expires_at))||Date.parse(o.identity_expires_at)<now))return '';
 const observed=Date.parse(o.checked_at);
 if(['name_characteristics','gtin_with_name'].includes(o.product_matching_method)&&/^p-[a-f0-9]{20}$/.test(o.product_id||'')&&o.brand?.trim()&&Number.isFinite(observed)&&now-observed<=36*3600000&&observed<=now+300000)return JSON.stringify(['characteristics',o.product_id]);
 const code=String(o.gtin||''),stamp=Date.parse(o.checked_at);if(![8,12,13,14].includes(code.length)||!/^\d+$/.test(code)||new Set(code).size===1||!Number.isFinite(stamp)||now-stamp>36*3600000||stamp>now+300000||!o.brand?.trim())return '';
 const digits=[...code.slice(0,-1)].reverse();const check=(10-digits.reduce((n,d,i)=>n+Number(d)*(i%2?1:3),0)%10)%10;if(check!==Number(code.at(-1)))return '';
 if(o.product_identity_verified===true&&/^p-[a-f0-9]{20}$/.test(o.product_id||''))return JSON.stringify(['canonical',o.product_id]);
 if(!(o.weight_kg>0))return '';
 return JSON.stringify([code.padStart(14,'0'),o.weight_kg,(metadata?metadata.brand(o.brand):o.brand).trim().toLowerCase()]);
}
function groupOffers(rows,now=Date.now()){
 const index=new Map(),keys=[];
 for(const o of rows){const k=matchKey(o,now);keys.push(k);if(k){let group=index.get(k);if(!group){group={offers:[],merchants:new Set()};index.set(k,group)}group.offers.push(o);group.merchants.add(o.merchant_id)}}
 const used=new Set(),result=[];
 for(let i=0;i<rows.length;i++){const k=keys[i],group=index.get(k);if(!group||(group.merchants.size<2&&!rows[i].product_identity_verified)){result.push([rows[i]]);continue}if(!used.has(k)){used.add(k);result.push(group.offers)}}
 return result;
}
// Preserve the feed URL byte-for-byte; never reconstruct affiliate parameters.
function merchantUrl(o){const value=o.affiliate_url||o.url;try{const u=new URL(value);return u.protocol==='https:'&&!u.username&&!u.password&&!/[\u0000-\u0020\u007f]/.test(value)?value:''}catch{return ''}}
function formatTimestamp(value){const d=new Date(value);if(value==null||!Number.isFinite(+d))return 'non disponibile';const options={timeZone:'Europe/Rome',day:'2-digit',month:'2-digit',year:'numeric'};if(!/^\d{4}-\d{2}-\d{2}$/.test(String(value))){options.hour='2-digit';options.minute='2-digit';}return new Intl.DateTimeFormat('it-IT',options).format(d)}
function relativeTime(value,now=Date.now()){const delta=Date.parse(value)-now;if(!Number.isFinite(delta))return 'non disponibile';const size=Math.abs(delta),unit=size>=86400000?'day':size>=3600000?'hour':size>=60000?'minute':'second',divisor={day:86400000,hour:3600000,minute:60000,second:1000}[unit];return new Intl.RelativeTimeFormat('it',{numeric:'always'}).format(Math.trunc(delta/divisor),unit)}
function freshnessLabel(value,now=Date.now()){const t=Date.parse(value),hours=(now-t)/3600000;return !Number.isFinite(t)||t>now+300000?'Data aggiornamento non disponibile':hours>12?'Dati non aggiornati da '+Math.floor(hours)+' ore':''}
function productUrl(o){const slug=o?.product_slug;if(typeof slug==='string'&&/^[a-z0-9][a-z0-9-]{1,200}$/.test(slug))return '/prodotto/'+slug;const path=o?.product_url;return typeof path==='string'&&/^\/prodotto\/[a-z0-9][a-z0-9-]{1,200}$/.test(path)?path:'/confronta-cibo'}
function goUrl(o,page='other'){return '/go/'+encodeURIComponent(o.id)+'?from='+(['home','catalog','product','basket','other'].includes(page)?page:'other')}
function reportUrl(o){const p=new URLSearchParams();for(const [key,source,limit] of [['id','id',100],['title','title',240],['shop','merchant',100],['price','price',30],['checked','checked_at',60]])p.set(key,String(o[source]??'').slice(0,limit));return 'segnala-errore.html#'+p;}
const api={merchantPromotion,merchantPromotionHTML,appendMerchantPromotion,formatTimestamp,relativeTime,freshnessLabel,productUrl,merchantUrl,goUrl,shippingRulesFromRows,shipping,discount,merchant,matchKey,groupOffers,reportUrl};if(typeof module!=='undefined')module.exports=api;else root.O4ZTrade=api;
})(typeof window!=='undefined'?window:this);
