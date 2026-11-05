(()=>{'use strict';const $=id=>document.getElementById(id),money=new Intl.NumberFormat('it-IT',{style:'currency',currency:'EUR'}),integer=new Intl.NumberFormat('it-IT');
const el=(tag,value,cls)=>{const e=document.createElement(tag);e.textContent=value;if(cls)e.className=cls;return e};
const url=(s,image=false)=>{if(image&&/^\/img\/p\/[a-f0-9]{24}-400\.webp$/.test(s))return s;try{const u=new URL(s);return u.protocol==='https:'?u.href:''}catch{return ''}};
function link(label,params,cls){const a=el('a',label,cls);a.href='/confronta-cibo?'+new URLSearchParams(params);return a}
function productTitle(o,tag){const h=el(tag,''),a=el('a',o.canonical_title||o.title,'product-title-link'),dest=O4ZTrade.productUrl(o);if(!dest)return el(tag,o.title);a.href=dest;h.append(a);return h}
function card(o,spotlight=false){const a=document.createElement('article');a.className=spotlight?'spotlight-product':'home-deal';a.dataset.homeOffer=o.checked_at;const im=url(o.image_local||o.image,true);if(im){const img=document.createElement('img');img.src=im;img.alt='';img.decoding='async';if(spotlight)img.fetchPriority='high';img.loading=spotlight?'eager':'lazy';img.width=160;img.height=145;a.append(img)}
a.append(el('p',o.merchant+' · '+o.brand,'micro'),productTitle(o,'h3'),el('p',o.variant,'micro'));
const historyDrop=Number.isFinite(o.verified_discount_pct)&&o.verified_discount_pct>=5&&Number.isFinite(o.verified_before_price)&&o.verified_before_price>o.price;
const comparison=!historyDrop&&Number.isFinite(o.comparison_savings_pct)&&o.comparison_savings_pct>=5&&Number.isFinite(o.comparison_other_price)&&o.comparison_other_price>o.price&&typeof o.comparison_other_merchant==='string';
if(historyDrop||comparison)a.classList.add('has-price-proof');
const p=el('p','','catalog-price');p.append(el('span','Qui','price-now-label'),el('strong',money.format(o.price)));a.append(p);
if(historyDrop||comparison){
 const evidence=el('div','','price-evidence '+(historyDrop?'is-drop':'is-comparison'));
 const percent=historyDrop?o.verified_discount_pct:o.comparison_savings_pct;
 evidence.append(el('span','−'+percent.toLocaleString('it-IT')+'% '+(historyDrop?'RIBASSO':'TRA NEGOZI'),'savings-badge'));
 const before=el('p','','price-before');before.append(document.createTextNode(historyDrop?'Prima ':'Altrove '));
 if(historyDrop)before.append(el('del',money.format(o.verified_before_price)));else before.append(el('strong',money.format(o.comparison_other_price)));
 evidence.append(before);
 evidence.append(el('p',historyDrop?'Prezzo precedente osservato sulla stessa offerta':'Confronto sullo stesso prodotto con '+o.comparison_other_merchant+' · non è uno sconto del negozio','price-proof-note'));
 a.append(evidence);
}else a.append(el('p','Prezzo aggiornato · nessuno sconto verificato','micro price-no-discount'));
O4ZTrade.appendMerchantPromotion(a,o);
if(o.unit_price&&o.unit_price_unit)a.append(el('p',money.format(o.unit_price)+'/'+o.unit_price_unit,'micro'));else if(o.weight_kg)a.append(el('p',money.format(o.price/o.weight_kg)+'/kg','micro'));
a.append(el('p','Rilevato: '+O4ZTrade.formatTimestamp(o.checked_at),'micro'));
const detail=el('a',(o.canonical_shop_count??2)<2?'Vedi offerta →':'Confronta nei negozi →','btn secondary');detail.href=O4ZTrade.productUrl(o);a.append(detail);const report=el('a','Prezzo o dati sbagliati? Segnala','micro');report.href=O4ZTrade.reportUrl(o);report.rel='nofollow';a.append(report);return a}
O4ZSuggest.mount($('home-query'),O4ZSuggest.catalog,o=>{if(o.id){$('home-query').dataset.selectedProduct=o.id;$('home-query').dataset.selectedUrl=O4ZTrade.productUrl(o);location.assign(O4ZTrade.productUrl(o))}});
$('home-query').addEventListener('input',()=>{delete $('home-query').dataset.selectedProduct;delete $('home-query').dataset.selectedUrl});
$('home-query').form.addEventListener('submit',e=>{const id=$('home-query').dataset.selectedProduct;if(id){e.preventDefault();location.assign($('home-query').dataset.selectedUrl||O4ZTrade.productUrl({id}))}});
$('home-query').addEventListener('focus',()=>{O4ZSuggest.catalog().catch(()=>{})},{once:true});
const fresh=s=>Number.isFinite(Date.parse(s))&&Date.now()-Date.parse(s)<=12*3600000&&Date.now()-Date.parse(s)>=-300000;
for(const node of document.querySelectorAll('[data-home-offer]'))if(!fresh(node.dataset.homeOffer))node.replaceChildren(el('p','Rilevazione da aggiornare. Consulta il catalogo per verificare il prezzo.','micro'),link('Apri il catalogo →',{},'btn secondary'));
(async()=>{try{const r=await fetch('data/home.json',{cache:'no-cache'});if(!r.ok)throw Error();const d=await r.json();if(document.getElementById('main').dataset.homeGenerated===d.generated_at)return;const rows=d.offers.filter(o=>Number.isFinite(o.price)&&o.price>0&&o.available&&url(o.url));
$('home-stats').replaceChildren(el('span',integer.format(d.stats.offers)+' offerte importate'),el('span',d.stats.brands+' marche'),el('span',(d.sources||[]).filter(s=>s.offers>0).length+' negozi'),el('span','Verifiche programmate ogni '+d.refresh_hours+' ore'));
const recent=rows.filter(o=>fresh(o.checked_at));const sales=recent.filter(o=>o.image&&(Number.isFinite(o.verified_discount_pct)&&o.verified_discount_pct>=5||Number.isFinite(o.comparison_savings_pct)&&o.comparison_savings_pct>=5));
const picked=[],brands=new Set();for(const o of sales){if(picked.length>=6)break;if(!brands.has(o.brand)){picked.push(o);brands.add(o.brand)}}
if(picked.length)$('home-deals').replaceChildren(...picked.map(o=>card(o)));
else $('home-deals').replaceChildren(el('p','Oggi non risultano ribassi o risparmi tra negozi sufficientemente verificati. Consulta il comparatore per i prezzi aggiornati.','home-no-proof'));
const verified=picked.filter(o=>Number.isFinite(o.verified_discount_pct)&&o.verified_discount_pct>=5).length;
const compared=picked.filter(o=>!Number.isFinite(o.verified_discount_pct)&&Number.isFinite(o.comparison_savings_pct)&&o.comparison_savings_pct>=5).length;
$('home-deals-status').textContent='Catalogo aggiornato: '+O4ZTrade.formatTimestamp(d.generated_at)+'. '+verified+' ribassi storici verificati, '+compared+' risparmi tra negozi verificati. In questa sezione non pubblichiamo prezzi senza prova di risparmio. Spedizione esclusa.';
const hero=picked.find(o=>o.id===d.daily_pick_id)||picked[0];
if($('daily-pick-label'))$('daily-pick-label').textContent=hero?'OFFERTA DEL GIORNO':'NESSUNA OFFERTA VERIFICATA OGGI';
if(hero)$('home-spotlight').replaceChildren(el('h2','Risparmio verificato in evidenza','sr-only'),card(hero,true));
else $('home-spotlight').replaceChildren(el('p','Nessun risparmio verificato al momento. Esplora il comparatore per i prezzi rilevati.','micro'),link('Esplora il catalogo →',{},'btn secondary'));

const brandPages=JSON.parse($('home-brands').dataset.brandPages||'{}');
$('home-brands').replaceChildren(...d.top_brands.map(brand=>{const a=link(brand,{brand}),path=brandPages[brand];a.href='/marche';if(typeof path==='string'&&/^\/marca-[a-z0-9-]+$/.test(path))a.href=path;return a}));
$('home-shops').replaceChildren(...(d.sources||[]).filter(s=>s.offers>0).map(s=>link(s.name+' · '+integer.format(s.offers)+' offerte →',{shop:s.name})));
}catch{$('home-deals-status').textContent+=' Aggiornamento online non disponibile: controlla la data delle offerte e verifica nel negozio.';}})();})();

// First-party newsletter invitation, loaded only on the homepage.
(()=>{const script=document.createElement('script');script.src='/assets/newsletter-popup.js';script.defer=true;document.body.append(script)})();
