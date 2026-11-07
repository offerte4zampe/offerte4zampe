(()=>{'use strict';
const $=id=>document.getElementById(id),money=new Intl.NumberFormat('it-IT',{style:'currency',currency:'EUR'});
const el=(tag,value,cls)=>{const n=document.createElement(tag);n.textContent=value;if(cls)n.className=cls;return n};
const safe=s=>{try{const u=new URL(s);return u.protocol==='https:'&&!u.username&&!u.password?u.href:''}catch{return ''}};
let catalog,id,shippingRules=null,amazonLinks=null;const offerTools=new Map();
function comparisonTable(view){
 let container=$('product-price-table');if(!container){container=el('section','','product-comparison');container.id='product-price-table';$('product-quantity').closest('.panel').before(container)}
 container.replaceChildren(el('h2','Prezzi nei negozi'),el('p','Su schermi piccoli scorri la tabella per vedere totale e collegamenti ai negozi.','micro'));
 const wrap=el('div','','comparison-scroll');wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label','Tabella prezzi e spedizioni, scorribile');
 const table=el('table','','comparison-table'),caption=el('caption','Stesso prodotto e formato · prezzi rilevati, da confermare nel negozio');table.append(caption);
 const head=el('thead',''),tr=el('tr','');for(const label of ['Negozio','Prezzo','Spedizione','Totale stimato','Disponibilità','Offerta']){const th=el('th',label);th.scope='col';tr.append(th)}head.append(tr);table.append(head);
 const body=el('tbody','');
 for(const shop of view.shops){for(const offer of shop.offers){const row=el('tr',''),q=shop.quotes.get(offer.id);row.dataset.comparisonOffer=offer.id;
 const seller=el('th',shop.source.name);seller.scope='row';if(offer.identity_review)seller.append(el('small','Abbinamento revisionato'));
 const priceCell=el('td',money.format(offer.price));O4ZTrade.appendMerchantPromotion(priceCell,offer);row.append(seller,priceCell,el('td',q.fee!==undefined?money.format(q.fee):'Da verificare'),el('td',q.total!==undefined?money.format(q.total):'Non calcolabile'));
 const status=el('td',offer.quantity_verified===false?'Disponibilità dal feed; formato non verificato':offer.available?'Disponibile al rilevamento':'Esaurito al rilevamento');status.append(el('small',O4ZTrade.formatTimestamp(offer.checked_at)));row.append(status);
 const action=el('td',''),target=O4ZTrade.merchantUrl(offer)?O4ZTrade.goUrl(offer,'product'):'';if(offer.available&&target){const a=el('a','Vai al negozio ↗','btn secondary');a.href=target;a.target='_blank';a.rel=offer.affiliate_url?'sponsored nofollow noopener noreferrer':'sponsored nofollow noopener noreferrer';action.append(a)}row.append(action);body.append(row);
 }}
 table.append(body);wrap.append(table);container.append(wrap,el('p','Il totale usa quantità e destinazione selezionate. Le spese mancanti non valgono zero. I link affiliati possono generare una commissione, senza costi aggiuntivi.','micro'));
}
function render(){
 const quantity=Number($('product-quantity').value),territory=$('product-territory').value;
 const view=O4ZProduct.productView(catalog,id,Date.now(),shippingRules,quantity,territory);
 if(!view){$('product-status').textContent='Questo prodotto non è presente nel catalogo corrente. Non mostriamo prezzi precedenti come attuali.';return}
 const amazon=$('product-amazon');amazon.replaceChildren();amazon.hidden=true;
 if(window.O4ZAmazonLinksEnabled===true){
 const amazonLink=O4ZAmazon.comparisonLink(view.seed,catalog.offers,amazonLinks);
 amazon.hidden=false;amazon.append(el('h2','Amazon'),el('p','Prezzo: non disponibile · Disponibilità: non verificata','micro'));
 if(amazonLink){
  amazon.append(el('p','Prezzo e disponibilità da verificare su Amazon. Questa opzione non partecipa alla classifica dei prezzi.','micro'));
  const link=el('a','Verifica prezzo su Amazon ↗','btn secondary');link.href=amazonLink.url;link.target='_blank';link.rel='sponsored nofollow noopener noreferrer';amazon.append(link,el('p','In qualità di Affiliato Amazon io ricevo un guadagno dagli acquisti idonei. Il prezzo valido è quello indicato su Amazon al momento dell’acquisto; disponibilità e condizioni possono cambiare.','micro'));
 }
 else amazon.append(el('p','Corrispondenza esatta non ancora verificata: non proponiamo ricerche generiche o prodotti simili.','micro'));
 }
 const o=view.seed;if(!$('product-watch').dataset.ready){O4ZWatch.mount($('product-watch'),o);$('product-watch').dataset.ready='1';}$('product-title').textContent=O4ZProductMetadata.name(o.canonical_title||o.title);document.title=O4ZProductMetadata.title(o.canonical_title||o.title,o.brand,o.canonical_format||o.variant);
 $('product-format').textContent=[o.brand,o.variant==='1ct'?'':o.variant,o.weight_kg?(o.weight_kg<1?Number((o.weight_kg*1000).toFixed(3))+' g':o.weight_kg+' kg'):''].filter(Boolean).join(' · ');
 const image=/^\/img\/p\/[a-f0-9]{24}-400\.webp$/.test(o.image_local||'')?o.image_local:safe(o.image);if(image){const img=document.createElement('img');img.src=image;img.alt=o.title;img.width=180;img.height=160;img.style.objectFit='contain';$('product-image').replaceChildren(img)}
 const reviewed=view.shops.some(s=>s.offers.some(o=>o.identity_review));
 const availableShops=view.shops.filter(s=>s.offers.some(o=>o.available)).length;
 $('product-status').textContent=availableShops+' negoz'+(availableShops===1?'io':'i')+' con offerte disponibili al rilevamento. '+(view.exact?(['name_characteristics','gtin_with_name'].includes(o.product_matching_method)?'Abbinamento per nome e caratteristiche: alcune offerte non hanno un GTIN condiviso. Verifica la variante nel negozio.':reviewed?'Confronto con abbinamento revisionato delle schede e del formato. Il codice non è dichiarato da tutti i negozi.':'Confronto dello stesso GTIN, marca e peso netto. Verifica comunque ricetta e confezione prima di acquistare.'):'Identità condivisa non verificabile: mostriamo la sola offerta selezionata, senza abbinare prodotti dai nomi simili.');
 comparisonTable(view);
 const grid=$('product-shops');grid.replaceChildren();const other=el('details','','panel'),summary=el('summary','Altri negozi: copertura e dati non disponibili');other.append(summary);for(const shop of view.shops){
 const card=el('article','','panel');card.dataset.productShop=shop.source.id;card.append(el('h3',shop.source.name));
 if(shop.source.status==='pending-feed'){
 card.append(el('p','Prezzo: non disponibile · Disponibilità: non verificata','micro'),el('p','Catalogo '+shop.source.name+' non ancora collegato. Non possiamo confermare lo stesso prodotto e formato né indicarne il prezzo.','micro'));
 }
 else if(shop.state!=='listed'){const labels={missing:'Nessuna offerta abbinata con certezza: il negozio potrebbe vendere questo prodotto',unknown:'Disponibilità non verificabile: catalogo non aggiornato o non disponibile',unmatched:'Corrispondenza non verificata in questo negozio',stale:'Dati da aggiornare: prezzo e disponibilità non confermati'};card.append(el('p',labels[shop.state]));if(shop.source.status==='ok'){const a=el('a','Cerca tra le offerte importate di '+shop.source.name+' →','micro');a.dataset.catalogSearch='';a.href='/confronta-cibo?'+new URLSearchParams({shop:shop.source.name,q:o.title.split(' - ')[0].split(/\s+/).slice(0,5).join(' ')});card.append(a)}}
 for(const offer of shop.offers){
 const row=el('section','','matched-offer');row.append(el('p',offer.variant||offer.title,'micro'),el('strong',money.format(offer.price)),el('p',offer.weight_kg?money.format(offer.price/offer.weight_kg)+'/kg · spedizione esclusa':'Spedizione esclusa','micro'),el('p',offer.quantity_verified===false?'Disponibilità dal feed; formato non verificato':offer.available?'Disponibile al rilevamento':'Esaurito al rilevamento'),el('p','Rilevato: '+O4ZTrade.formatTimestamp(offer.checked_at),'micro'));
 O4ZTrade.appendMerchantPromotion(row,offer);
 const quote=shop.quotes.get(offer.id);const estimate=el('p',quote.total!==undefined?'Totale stimato: '+money.format(quote.total)+' ('+quantity+' confezioni · spedizione '+money.format(quote.fee)+')':'Totale non calcolato: '+quote.reason,'micro');estimate.dataset.shippingEstimate=offer.id;row.append(estimate);
 if(quote.rule){const conditions=el('a','Condizioni di spedizione','micro');conditions.href=safe(quote.rule.source);conditions.target='_blank';conditions.rel='noopener noreferrer';conditions.dataset.shippingConditions='';row.append(conditions)}
 const target=O4ZTrade.merchantUrl(offer)?O4ZTrade.goUrl(offer,'product'):'';
 if(offer.available&&target){const a=el('a','Vai al negozio ↗','btn');a.href=target;a.target='_blank';a.rel=offer.affiliate_url?'sponsored nofollow noopener noreferrer':'sponsored nofollow noopener noreferrer';row.append(a);if(offer.affiliate_url)row.append(el('p','Possiamo ricevere una commissione, senza costi aggiuntivi per te.','micro'))}
 if(!offerTools.has(offer.id)){
  const tools=el('div','','product-tools');tools.append(O4ZHistory.mount(offer.id),O4ZDaily.mount(offer));
  const add=el('button','Aggiungi una confezione alla lista','btn secondary');add.type='button';add.dataset.productBasket=offer.id;add.disabled=!offer.available||offer.quantity_verified===false;add.onclick=()=>{$('product-list-status').textContent=O4ZBasket.addProduct(offer,catalog.offers)};tools.append(add);
  const report=el('a','Prezzo o dati sbagliati? Segnala','micro');report.href=O4ZTrade.reportUrl(offer);report.rel='nofollow';report.dataset.productReport='';tools.append(report);
  offerTools.set(offer.id,tools);
 }
 row.append(offerTools.get(offer.id));
 card.append(row)}
 if(shop.state==='listed')grid.append(card);else other.append(card)}if(other.children.length>1)grid.append(other);
 $('product-coverage').textContent='Confrontiamo '+view.shops.filter(s=>s.source.status!=='pending-feed').length+' cataloghi importati, non tutto il mercato. L’assenza dal catalogo non prova che il negozio non venda il prodotto. Prezzi non in tempo reale; conferma disponibilità e totale nel negozio.';
}
async function load(){try{
 id=new URLSearchParams(location.search).get('id');if(!id)throw Error('missing');
 const amazon=fetch('data/amazon-links.json',{cache:'no-cache'}).then(r=>r.ok?r.json():null).catch(()=>null);
 const rules=fetch('data/shipping-rules.json',{cache:'no-cache'}).then(r=>r.ok?r.json():null).catch(()=>null);
 const r=await fetch('data/catalog.json.gz',{cache:'no-cache'});if(!r.ok)throw Error('network');
 const bytes=await r.arrayBuffer(),raw=new Uint8Array(bytes);
 catalog=JSON.parse(raw[0]===31&&raw[1]===139?await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text():new TextDecoder().decode(bytes));
 catalog.offers=catalog.offers.map(O4ZMetadata.normalize);[shippingRules,amazonLinks]=await Promise.all([rules,amazon]);render();
 const selected=catalog.offers.find(o=>o.id===id);if(selected)O4ZShare.mount($('product-share'),selected);
 for(const control of ['product-quantity','product-territory'])$(control).addEventListener('change',render);
 }catch{$('product-status').textContent='Impossibile caricare questa scheda. Riprova tra poco oppure torna alla ricerca.'}}
load();
})();
