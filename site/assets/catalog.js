(()=>{'use strict';
const $=id=>document.getElementById(id), money=new Intl.NumberFormat('it-IT',{style:'currency',currency:'EUR'});let data=[],selected=new Set(),limit=30,shippingRules=null,quoteCache=new Map(),quoteQuantity=1,quoteTerritory='standard';
let loaderThread='not-loaded',loaderReason=null;const profiling=new URLSearchParams(location.search).get('profile')==='1',profileRows=[];
function timed(name,fn){if(!profiling)return fn();const start=performance.now();try{return fn()}finally{profileRows.push({stage:name,ms:performance.now()-start})}}
function duration(name,start){if(profiling)profileRows.push({stage:name,ms:performance.now()-start})}
const compareItalian=new Intl.Collator('it').compare;
const text=(tag,value,cls)=>{const e=document.createElement(tag);e.textContent=value;if(cls)e.className=cls;return e};
const date=O4ZTrade.formatTimestamp;
const params=new URLSearchParams(location.search);
function refreshFreshness(sources){const box=$('catalog-freshness');if(!box)return;const messages=sources.map(s=>({name:s.name,label:O4ZTrade.freshnessLabel(s.checked_at)})).filter(s=>s.label);box.replaceChildren(...messages.map(s=>text('p',s.name+': '+s.label)));box.hidden=!messages.length;}
try{refreshFreshness(JSON.parse($('catalog-freshness-data')?.textContent||'[]'))}catch{}
const preview=$('catalog-preview');
if(preview&&['q','shop','brand','gtin','matched','animal','type','age','size','pack'].some(key=>params.has(key)))preview.hidden=true;
$('catalog-multishop').checked=params.get('matched')==='1';
$('catalog-query').value=(params.get('q')||'').slice(0,120);$('catalog-sale').checked=false;$('catalog-sale').disabled=true;$('catalog-sale').closest('label').hidden=true;$('catalog-sale').closest('label').style.display='none';
const allowedSort=['name','price','total','kg','matched'];if(allowedSort.includes(params.get('sort')))$('catalog-sort').value=params.get('sort');
$('catalog-stock').checked=params.get('stock')!=='all';
const sharedQuantity=Number(params.get('quantity'));if(Number.isInteger(sharedQuantity)&&sharedQuantity>=1&&sharedQuantity<=10)$('shipping-quantity').value=sharedQuantity;
if(params.get('territory')==='special')$('shipping-territory').value='special';
const safeUrl=(s,image=false)=>{if(image&&/^\/img\/p\/[a-f0-9]{24}-400\.webp$/.test(s))return s;try{const u=new URL(s);return u.protocol==='https:'?u.href:''}catch{return ''}};
function productTitle(o,tag='h3',label=o.canonical_title||o.title){const heading=text(tag,''),a=text('a',label,'product-title-link'),url=O4ZTrade.productUrl(o);a.href=url;a.setAttribute('aria-label',label+' — '+o.merchant);heading.append(a);return heading}
function stale(o){return Date.now()-Date.parse(o.checked_at)>36*3600000}
function fillSelect(id,values){for(const value of [...new Set(values.filter(Boolean))].sort((a,b)=>compareItalian(a,b))){const o=text('option',value);o.value=value;$(id).append(o)}}
const facetKeys=['animal','type','age','size','pack'];
let searchText=new Map(),identityIndex=new Map(),facetIndex=new Map(),coverageIndex=new Map();
const identity=o=>JSON.stringify([o.gtin,o.weight_kg,String(o.brand||'').trim().toLowerCase()]);
function shown(allowed){const filters=Object.fromEntries(facetKeys.map(k=>[k,$('catalog-'+k).value]));const q=$('catalog-query').value.toLocaleLowerCase('it').trim().split(/\s+/).filter(Boolean),shop=$('catalog-shop').value,brand=$('catalog-brand').value,stock=$('catalog-stock').checked,sale=$('catalog-sale').checked,sort=$('catalog-sort').value;
return (allowed?data.filter(o=>allowed.has(o.id)):data).filter(o=>(!params.get('gtin')||(o.gtin===params.get('gtin')&&String(o.weight_kg)===params.get('weight')&&o.brand.trim().toLowerCase()===params.get('matchbrand')))&&(allowed||O4ZMetadata.matchesFacets(facetIndex.get(o.id),filters)&&(!shop||o.merchant===shop)&&(!brand||o.brand===brand)&&(!stock||o.available)&&(!sale||O4ZTrade.discount(o))&&q.every(w=>(searchText.get(o.id)||'').includes(w)))).sort((a,b)=>{
switch(sort){case 'matched':return shopCount(b)-shopCount(a)||(quote(a).total??Infinity)-(quote(b).total??Infinity)||a.price-b.price;case 'total':return (quote(a).total??Infinity)-(quote(b).total??Infinity)||compareItalian(a.title,b.title);case 'price':return a.price-b.price;case 'kg':return (a.weight_kg?a.price/a.weight_kg:Infinity)-(b.weight_kg?b.price/b.weight_kg:Infinity);case 'discount':return (b.previous_price?1-b.price/b.previous_price:0)-(a.previous_price?1-a.price/a.previous_price:0);default:return compareItalian(a.title,b.title)}})}
function basketButton(o){const b=text('button','Aggiungi alla lista','btn secondary');b.type='button';b.dataset.basketAdd=o.id;const stamp=Date.parse(o.checked_at);b.disabled=o.quantity_verified===false||!o.available||!Number.isFinite(stamp)||Date.now()-stamp>36*3600000||stamp>Date.now()+300000;b.onclick=()=>{$('catalog-basket-status').textContent=O4ZBasket.addProduct(o,data)};return b}
function shopCount(o){return o.canonical_shop_count??coverageIndex.get(o.id)??0;}
function productCard(o){const card=text('article','','catalog-card'),url=O4ZTrade.productUrl(o);const imgUrl=safeUrl(o.image_local||o.image,true);if(imgUrl){const img=document.createElement('img');img.src=imgUrl;img.alt='';img.decoding='async';img.loading='lazy';img.width=150;img.height=130;card.append(img)}
card.append(text('p',shopCount(o)===0?'Formato non verificato':shopCount(o)+' negoz'+(shopCount(o)===1?'io':'i')+' con offerte disponibili al rilevamento','micro'),text('p',o.merchant+' · '+o.brand,'micro'),productTitle(o),text('p',o.canonical_format||o.variant,'micro'));
const prices=text('p','','catalog-price');prices.append(text('strong',money.format(o.price)));O4ZTrade.appendMerchantPromotion(prices,o);card.append(prices);
card.append(text('p',o.unit_price!==undefined&&o.unit_price!==null?money.format(o.unit_price)+'/'+o.unit_price_unit+' · '+o.canonical_format:o.weight_kg?money.format(o.price/o.weight_kg)+'/kg · confezione '+o.weight_kg+' kg':'Quantità netta non verificata: prezzo unitario non calcolato','micro'));
card.append(text('p',(o.quantity_verified===false?'Disponibilità indicata dal feed; formato non verificato':o.available?'Disponibile al rilevamento':'Non disponibile al rilevamento')+(stale(o)?' · Dato da aggiornare':''),'micro'),text('p','Rilevato: '+date(o.checked_at)+' ('+O4ZTrade.relativeTime(o.checked_at)+')','micro'));
const freshLabel=O4ZTrade.freshnessLabel(o.checked_at);if(freshLabel)card.append(text('p',freshLabel,'notice'));
const q=quote(o);card.append(text('p',q.total!==undefined?'Totale stimato: '+money.format(q.total)+' ('+$('shipping-quantity').value+(Number($('shipping-quantity').value)===1?' confezione':' confezioni')+' · spedizione '+money.format(q.fee)+')':'Totale non calcolato: '+q.reason,'micro'));
if(q.rule){const a=text('a','Condizioni di spedizione','micro');a.href=q.rule.source;a.target='_blank';a.rel='noopener noreferrer';card.append(a)}

if(o.gtin){card.append(text('p','GTIN: '+o.gtin+(o.identity_review?' · abbinamento revisionato, codice dalla scheda di riferimento':' · codice dal negozio'),'micro'));const matches=(identityIndex.get(identity(o))||[]).filter(x=>x.merchant_id!==o.merchant_id);if(matches.length){const a=text('a','Stesso codice e formato in altri negozi →','micro');a.href=O4ZTrade.productUrl(o);card.append(a)}}
card.append(O4ZHistory.mount(o.id),O4ZDaily.mount(o));
const actions=text('div','','buttons');if(url){const a=text('a',o.canonical_shop_count===undefined?'Confronta nei negozi →':o.canonical_shop_count>=2?'Confronta '+o.canonical_shop_count+' negozi →':'Vedi offerta →','btn secondary');a.href=O4ZTrade.productUrl(o);actions.append(a);if(o.affiliate_url||o.affiliate)actions.append(text('span','Possiamo ricevere una commissione, senza costi aggiuntivi per te.','micro'))}const b=text('button',selected.has(o.id)?'Rimuovi dal confronto':'Confronta','btn secondary');b.type='button';b.setAttribute('aria-pressed',selected.has(o.id));b.addEventListener('click',()=>{if(selected.has(o.id))selected.delete(o.id);else if(selected.size<4)selected.add(o.id);else{$('catalog-selection-status').textContent='Puoi confrontare fino a quattro offerte. Rimuovine una prima.';return}render()});actions.append(b);actions.append(basketButton(o),O4ZWatch.button(o));card.append(actions);const report=text('a','Prezzo o dati sbagliati? Segnala','micro');report.href=O4ZTrade.reportUrl(o);report.rel='nofollow';card.append(report);return card}
function groupCard(rows){
 const sorted=[...rows].sort((a,b)=>Number(b.available)-Number(a.available)||(['total','matched'].includes($('catalog-sort').value)?(quote(a).total??Infinity)-(quote(b).total??Infinity):a.price-b.price)||a.price-b.price),seed=sorted[0];
 const card=text('article','','catalog-card catalog-group'),imgUrl=safeUrl(seed.image_local||seed.image,true);
 if(imgUrl){const img=document.createElement('img');img.src=imgUrl;img.alt='';img.decoding='async';img.loading='lazy';img.width=150;img.height=130;card.append(img)}
 const shops=new Set(rows.map(o=>o.merchant_id)).size,live=sorted.filter(o=>o.available),minimum=Math.min(...live.map(o=>o.price));
 card.append(text('p',shops+' negozi · stesso prodotto e formato','tag'),productTitle(seed),text('p',(seed.canonical_format||seed.weight_kg+' kg')+' · '+seed.brand,'micro'));
 if(live.length)card.append(text('p','Da '+money.format(minimum),'catalog-price'),text('p',money.format(minimum/(seed.quantity?.value||seed.weight_kg||1))+'/'+(seed.unit_price_unit||'kg')+' · spedizione esclusa','micro'));
 card.append(text('p',rows.some(o=>['name_characteristics','gtin_with_name'].includes(o.product_matching_method))?'Abbinamento per nome e caratteristiche; GTIN non condiviso da tutte le offerte.':rows.some(o=>o.identity_review)?'Abbinamento revisionato delle schede e della confezione.':'Confronto per GTIN, marca e peso dichiarato.','micro'));
 const list=text('ul','','store-price-summary');
 for(const o of sorted){const li=text('li','');li.append(text('span',o.merchant),text('strong',money.format(o.price)),text('small',o.available?'Disponibile al rilevamento':'Esaurito al rilevamento'));const warning=O4ZTrade.freshnessLabel(o.checked_at);if(warning)li.append(text('small',warning,'notice'));O4ZTrade.appendMerchantPromotion(li,o);list.append(li)}
 card.append(list);
 const action=text('a',shops>=2?'Confronta '+shops+' negozi →':'Vedi offerta →','btn');action.href=O4ZTrade.productUrl(seed);card.append(action,text('p','Strumenti riferiti all’offerta di '+seed.merchant,'micro'),basketButton(seed),O4ZWatch.button(seed),O4ZDaily.mount(seed),O4ZHistory.mount(seed.id));
 return card;
}

let renderVersion=0,filterWorker=null;
async function candidates(){if(!filterWorker)return null;return filterWorker.filter({words:$('catalog-query').value.toLocaleLowerCase('it').trim().split(/\s+/).filter(Boolean),shop:$('catalog-shop').value,brand:$('catalog-brand').value,stock:$('catalog-stock').checked,facets:Object.fromEntries(facetKeys.map(k=>[k,$('catalog-'+k).value]))})}

function configureQuotes(){const quantity=Number($('shipping-quantity').value),territory=$('shipping-territory').value;if(quantity!==quoteQuantity||territory!==quoteTerritory){quoteCache=new Map();quoteQuantity=quantity;quoteTerritory=territory;}}
function groupRows(rows){return O4ZTrade.groupOffers(rows).filter(g=>!$('catalog-multishop').checked||new Set(g.map(o=>o.merchant_id)).size>1)}
function displayRows(rows,groups){$('catalog-count').textContent=groups.length+' prodotti e formati · '+groups.reduce((n,g)=>n+g.length,0)+' offerte · '+groups.filter(g=>new Set(g.map(o=>o.merchant_id)).size>1).length+' confronti automatici tra negozi · '+data.length+' offerte importate';if(preview)preview.hidden=true;const grid=$('catalog-grid');timed('render_cards',()=>grid.replaceChildren(...groups.slice(0,limit).map(g=>g.length>1?groupCard(g):productCard(g[0]))));$('catalog-more').hidden=groups.length<=limit;$('catalog-empty').hidden=groups.length>0;timed('render_comparison',renderComparison);if(profiling)window.O4ZCatalogProfile={loader_thread:loaderThread,fallback_reason:loaderReason,offers:data.length,groups:groups.length,cards:Math.min(groups.length,limit),samples:profileRows.slice()}}
async function render(){if(!catalogReady){ensureLoad();return}const version=++renderVersion;configureQuotes();const allowed=await candidates();if(version!==renderVersion)return;const rows=timed('filter_sort',()=>shown(allowed));displayRows(rows,timed('group',()=>groupRows(rows)))}
async function renderInitial(){
 const version=++renderVersion,current=()=>version===renderVersion;configureQuotes();
 if($('catalog-sort').value==='total'&&!$('catalog-query').value&&!$('catalog-shop').value&&!$('catalog-brand').value&&!params.get('gtin')&&!facetKeys.some(k=>$('catalog-'+k).value)){
  const stock=$('catalog-stock').checked;
  await O4ZCooperate.each(data,o=>{if(!stock||o.available)quote(o)},{isCurrent:current,onChunk:profiling?ms=>profileRows.push({stage:'quote_chunk_cpu',ms}):null});
 }
 if(!current())return;
 const allowed=await candidates();if(!current())return;const rows=timed('filter_sort',()=>shown(allowed));await O4ZCooperate.yieldToMain();if(!current())return;
 const groups=timed('group',()=>groupRows(rows));await O4ZCooperate.yieldToMain();if(current())displayRows(rows,groups);
}
function renderComparison(){const rows=data.filter(o=>selected.has(o.id));$('catalog-comparison').hidden=!rows.length;$('catalog-selection-status').textContent=rows.length?rows.length+' offerte selezionate (massimo 4).':'';const body=$('catalog-comparison-body');body.replaceChildren();
for(const o of rows){const tr=document.createElement('tr');[o.title+' '+o.variant,o.merchant,money.format(o.price),o.weight_kg?money.format(o.price/o.weight_kg)+'/kg':'Non verificato',o.available?'Sì':'No',date(o.checked_at)].forEach(v=>tr.append(text('td',v)));tr.firstElementChild.replaceChildren(productTitle(o,'span',o.title+' '+o.variant));const td=text('td','');if(o.weight_kg){for(const side of ['A','B']){const b=text('a','Usa come '+side,'btn secondary'),other=rows.find(x=>x.id!==o.id&&x.weight_kg),a=side==='A'?o:other,second=side==='B'?o:other,values=new URLSearchParams({v:'1'});for(const [prefix,offer]of [['a',a],['b',second]])if(offer){values.set(prefix+'p',String(offer.price));values.set(prefix+'k',String(offer.weight_kg));values.set('label'+prefix,offer.title+' — '+offer.merchant)}b.href='/calcolatore#'+values.toString();td.append(b)}}tr.append(td);body.append(tr)}
const same=rows.length>1&&rows[0].gtin&&rows.every(o=>o.gtin===rows[0].gtin&&o.weight_kg===rows[0].weight_kg&&o.brand.trim().toLowerCase()===rows[0].brand.trim().toLowerCase());$('catalog-match-note').textContent=same?'Le offerte condividono lo stesso GTIN e formato. Confronto del prezzo prodotto; spedizione esclusa.':'Le offerte sono scelte da te: non sono automaticamente equivalenti. Controlla ricetta, formato e quantità. Spedizione esclusa.';}
function quote(o){if(quoteCache.has(o.id))return quoteCache.get(o.id);const value=O4ZTrade.shipping(o,shippingRules,quoteQuantity,quoteTerritory);quoteCache.set(o.id,value);return value}
let catalogReady=false,loadPromise=null;
function ensureLoad(){if(catalogReady)return Promise.resolve();if(loadPromise)return loadPromise;const button=$('catalog-load');if(button)button.disabled=true;return loadPromise=load().finally(()=>{if(!catalogReady){loadPromise=null;if(button)button.disabled=false}})}
async function load(){try{const shippingPromise=fetch('data/shipping-rules.json',{cache:'no-cache'}).then(r=>r.ok?r.json():null).catch(()=>null);const loadStart=performance.now(),loaded=await O4ZCatalogLoad.loadIndex(),payload=loaded.payload;refreshFreshness(payload.sources||[]);if(profiling){profileRows.push(...loaded.metrics);duration('load_wall',loadStart);}loaderThread=loaded.thread;loaderReason=loaded.fallback_reason||null;shippingRules=await shippingPromise;const prepareStart=performance.now();const prepared=await O4ZCatalogPrepare.prepare(payload.offers,{index:true,onChunk:profiling?ms=>profileRows.push({stage:'prepare_chunk_cpu',ms}):null});data=prepared.data;catalogReady=true;if($('catalog-load'))$('catalog-load').hidden=true;for(const group of O4ZTrade.groupOffers(data)){const count=new Set(group.filter(o=>o.available&&Number.isFinite(Date.parse(o.checked_at))&&!stale(o)&&Date.parse(o.checked_at)<=Date.now()+300000).map(o=>o.merchant_id)).size;for(const o of group)coverageIndex.set(o.id,count);}facetIndex=new Map(data.map(o=>[o.id,O4ZMetadata.facets(o)]));identityIndex=prepared.identityIndex;searchText=prepared.searchText;filterWorker=O4ZCatalogLoad.createFilter(data.map(o=>({id:o.id,merchant:o.merchant,brand:o.brand,available:o.available,search:searchText.get(o.id)||'',facets:facetIndex.get(o.id)})));duration('prepare_indexes',prepareStart);const controlsStart=performance.now();fillSelect('catalog-shop',data.map(o=>o.merchant));fillSelect('catalog-brand',data.map(o=>o.brand));for(const key of facetKeys){fillSelect('catalog-'+key,data.map(o=>facetIndex.get(o.id)[key]));const value=params.get(key);if(value&&[...$('catalog-'+key).options].some(o=>o.value===value))$('catalog-'+key).value=value;}for(const [key,id] of [['shop','catalog-shop'],['brand','catalog-brand'],...facetKeys.map(k=>[k,'catalog-'+k])]){const value=params.get(key);if(value&&Array.from($(id).options).some(o=>o.value===value))$(id).value=value;}
duration('prepare_controls',controlsStart);$('catalog-status').textContent='Cataloghi importati automaticamente · aggiornamento previsto ogni '+payload.refresh_hours+' ore · ultima esecuzione '+date(payload.generated_at)+'. I link Bauzaar, Isola dei Tesori e Paco Pet Shop possono generare commissioni, senza costi aggiuntivi per te.';
fetch('data/product-coverage.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error();return r.json()}).then(a=>{$('catalog-identity-status').textContent=a.multi_shop_products+' prodotti confrontabili in più negozi su '+a.active_products+' attivi ('+a.multi_shop_percent+'%). '+a.unattached_offers+' offerte restano separate. '+(a.characteristic_multi_shop_products||0)+' confronti includono abbinamenti per nome e caratteristiche, segnalati nelle schede.'}).catch(()=>{});const sources=$('catalog-sources');for(const s of payload.sources||[]){sources.append(text('li',s.name+': '+s.offers+' offerte · '+(s.status==='ok'?'importazione riuscita':s.status==='stale'?'aggiornamento fallito; dati precedenti conservati':'fonte non disponibile')+' · ultimo dato '+date(s.checked_at)+(['bauzaar','isola-dei-tesori'].includes(s.id)?' · feed ufficiale aggiornato dal fornitore giornalmente':'')))}if(params.get('gtin'))$('catalog-status').textContent+=' Vista per codice GTIN e peso esplicito; ricetta ed etichetta vanno comunque controllate. Per uscire apri Confronta prezzi dal menu.';O4ZSuggest.mount($('catalog-query'),()=>data.filter(o=>(!$('catalog-shop').value||o.merchant===$('catalog-shop').value)&&(!$('catalog-brand').value||o.brand===$('catalog-brand').value)),o=>{location.href=O4ZTrade.productUrl(o)});await renderInitial();}catch{catalogReady=false;if($('catalog-load'))$('catalog-load').hidden=false;$('catalog-status').textContent='Catalogo completo momentaneamente non disponibile. La selezione statica, se presente, riporta data e fonte del rilevamento; verifica sempre il prezzo nel negozio. Riprova più tardi.';$('catalog-filters').hidden=true}}
$('catalog-share').addEventListener('click',async()=>{
 const shared=new URL(location.pathname,location.origin),query=shared.searchParams;
 for(const [key,id] of [['q','catalog-query'],['shop','catalog-shop'],['brand','catalog-brand'],...facetKeys.map(k=>[k,'catalog-'+k])]){const value=$(id).value.trim();if(value)query.set(key,value);}
 for(const key of ['gtin','weight','matchbrand'])if(params.has(key))query.set(key,params.get(key));
 if($('catalog-multishop').checked)query.set('matched','1');
 if($('catalog-sort').value!=='matched')query.set('sort',$('catalog-sort').value);
 if(!$('catalog-stock').checked)query.set('stock','all');
 const quantity=Number($('shipping-quantity').value);if(Number.isInteger(quantity)&&quantity>=1&&quantity<=10&&quantity!==1)query.set('quantity',quantity);
 if($('shipping-territory').value==='special')query.set('territory','special');
 $('catalog-share-url').value=shared.href;$('catalog-share-fallback').hidden=true;
 try{await navigator.clipboard.writeText(shared.href);$('catalog-share-status').textContent='Link copiato. Condivide filtri e stima spedizione, non la lista personale. Prezzi e disponibilità possono cambiare.';}
 catch{$('catalog-share-fallback').hidden=false;$('catalog-share-url').focus();$('catalog-share-url').select();$('catalog-share-status').textContent='Copia il link dal campo. Condivide filtri e stima spedizione; prezzi e disponibilità possono cambiare.';}
});
let renderTimer;
$('catalog-reset').addEventListener('click',()=>{
 clearTimeout(renderTimer);
 $('catalog-status').textContent=$('catalog-status').textContent.replace(' Vista per codice GTIN e peso esplicito; ricetta ed etichetta vanno comunque controllate. Per uscire apri Confronta prezzi dal menu.','');
 for(const key of ['q','shop','brand','gtin','weight','matchbrand','matched','sale','sort','stock',...facetKeys])params.delete(key);
 for(const id of ['catalog-query','catalog-shop','catalog-brand',...facetKeys.map(k=>'catalog-'+k)])$(id).value='';
 $('catalog-stock').checked=true;$('catalog-sale').checked=false;$('catalog-multishop').checked=false;$('catalog-sort').value='matched';
 const url=new URL(location.href);url.search=params.toString();history.replaceState(null,'',url);
 $('catalog-query').dispatchEvent(new Event('input',{bubbles:true}));clearTimeout(renderTimer);limit=30;render();
 $('catalog-query').focus();
});

for(const id of ['catalog-query','catalog-shop','catalog-brand','catalog-sort','catalog-stock','catalog-sale','catalog-multishop',...facetKeys.map(k=>'catalog-'+k),'shipping-territory','shipping-quantity'])$(id).addEventListener((id==='catalog-query'||id==='shipping-quantity')?'input':'change',()=>{renderVersion++;limit=30;clearTimeout(renderTimer);if(id==='catalog-query')renderTimer=setTimeout(render,150);else render()});$('catalog-more').addEventListener('click',()=>{limit+=30;render()});$('shipping-refresh').addEventListener('click',()=>{limit=30;render()});$('catalog-clear').addEventListener('click',()=>{selected.clear();render()});
$('catalog-load')?.addEventListener('click',ensureLoad);
$('catalog-filters').addEventListener('focusin',ensureLoad,{once:true});
if(profiling||['q','shop','brand','gtin','matched','animal','type','age','size','pack','sort','stock','quantity','territory'].some(k=>params.has(k)))ensureLoad();
})();
