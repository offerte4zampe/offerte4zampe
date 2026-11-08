/* Observations only. Missing days are not interpolated. No historical discount claim. */
(function(root){'use strict';
const DAY=86400000;
const ALLOWED_MERCHANTS=new Set(['bauzaar','isola-dei-tesori','paco','webpet','animaliapet']);
function allowedOffer(id){return typeof id==='string'&&id.includes(':')&&ALLOWED_MERCHANTS.has(id.split(':',1)[0].toLowerCase());}
function summarize(rows,days,now=Date.now()){
 days=[30,90,180].includes(Number(days))?Number(days):30;
 const today=Math.floor(now/DAY)*DAY,cutoff=today-(days-1)*DAY;
 const valid=(Array.isArray(rows)?rows:[]).filter(r=>{const stamp=Date.parse(r.day+'T00:00:00Z');return /^\d{4}-\d{2}-\d{2}$/.test(r.day)&&Number.isFinite(stamp)&&new Date(stamp).toISOString().slice(0,10)===r.day&&stamp>=cutoff&&stamp<=today&&Number.isFinite(r.low)&&r.low>0&&Number.isFinite(r.high)&&r.high>=r.low;}).sort((a,b)=>a.day.localeCompare(b.day));
 const observed=valid.filter(r=>Number.isFinite(r.last)&&r.last>0),mean=observed.length?observed.reduce((n,r)=>n+r.last,0)/observed.length:null;
 return {rows:valid,days,mean,chart:days===30||new Set(valid.map(r=>r.day)).size>30,low:valid.length?Math.min(...valid.map(r=>r.low)):null,high:valid.length?Math.max(...valid.map(r=>r.high)):null,observedDays:new Set(valid.map(r=>r.day)).size};
}
const pending=new Map();
async function load(id){
 if(!allowedOffer(id))throw Error('merchant history not allowed');
 const hash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(id)),prefix=new Uint8Array(hash)[0].toString(16).padStart(2,'0');
 if(!pending.has(prefix))pending.set(prefix,fetch('data/history/'+prefix+'.json.gz').then(async r=>{if(!r.ok)throw Error('history');const b=await r.arrayBuffer(),raw=new Uint8Array(b);return JSON.parse(raw[0]===31&&raw[1]===139?await new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip'))).text():new TextDecoder().decode(b));}).catch(e=>{pending.delete(prefix);throw e}));return pending.get(prefix);
}
function mount(id){
 if(!allowedOffer(id))return document.createDocumentFragment();
 const date=value=>root.O4ZTrade?.formatTimestamp(value)||value;
 const node=(tag,value)=>{const n=document.createElement(tag);if(value)n.textContent=value;return n;};
 const details=node('details'),summary=node('summary','Storico del prezzo rilevato');details.className='observed-history';details.append(summary);let loaded=false;
 details.addEventListener('toggle',async()=>{if(!details.open||loaded)return;loaded=true;const body=node('div');body.className='micro';body.textContent='Recupero delle rilevazioni disponibili…';details.append(body);
 try{const history=await load(id),all=history.offers[id]||[],label=node('label','Periodo osservato '),select=node('select');for(const days of [30,90,180]){const option=node('option',days+' giorni');option.value=days;select.append(option);}label.append(select);const view=node('div');body.replaceChildren(label,view);
 function render(){const data=summarize(all,select.value);view.replaceChildren();view.append(node('p','Prezzi della singola offerta e confezione nel negozio, spedizione esclusa. Giorni UTC; nessun riempimento dei giorni mancanti. Il recupero del feed non prova quando il negozio ha modificato il prezzo.'));
 if(!data.rows.length){view.append(node('p','Nessuna rilevazione valida nel periodo selezionato.'));return;}
 const money=n=>new Intl.NumberFormat('it-IT',{style:'currency',currency:'EUR'}).format(n);
 view.append(node('p',data.observedDays+' giorni con rilevazioni su '+data.days+' selezionati · dal '+date(data.rows[0].day)+' al '+date(data.rows.at(-1).day)+'. Minimo '+money(data.low)+' · massimo '+money(data.high)+'.'));
 if(data.observedDays<2)view.append(node('p','Prime rilevazioni: non c’è ancora un andamento di più giorni.'));
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 300 100');svg.setAttribute('role','img');svg.setAttribute('aria-label','Prezzi osservati: minimo '+money(data.low)+', massimo '+money(data.high)+', media '+(data.mean===null?'non disponibile':money(data.mean))+'. Valori e date nella tabella seguente.');svg.style.width='100%';svg.style.maxWidth='360px';
 const end=Math.floor(Date.now()/DAY)*DAY,start=end-(data.days-1)*DAY,range=data.high-data.low||1;
 for(const row of data.rows){const x=10+(Date.parse(row.day+'T00:00:00Z')-start)/(end-start||DAY)*280,y=v=>85-(v-data.low)/range*70;const line=document.createElementNS(svg.namespaceURI,'line');for(const [k,v] of Object.entries({x1:x,x2:x,y1:y(row.low),y2:y(row.high),stroke:'currentColor','stroke-width':2}))line.setAttribute(k,v);svg.append(line);const dot=document.createElementNS(svg.namespaceURI,'circle');dot.setAttribute('cx',x);dot.setAttribute('cy',y(row.low));dot.setAttribute('r',3);dot.setAttribute('fill','currentColor');svg.append(dot);}
 if(data.chart)view.append(svg);else view.append(node('p','Storico breve: grafico esteso disponibile dopo più di 30 giorni osservati. La tabella mostra tutti i dati disponibili.'));const table=node('table'),caption=node('caption','Rilevazioni giornaliere disponibili (non prezzi garantiti al checkout)'),thead=node('thead'),tr=node('tr');for(const name of ['Giorno UTC','Minimo','Massimo','Disponibile*']){const th=node('th',name);th.scope='col';tr.append(th);}thead.append(tr);const tbody=node('tbody');for(const row of data.rows){const tr=node('tr');for(const value of [date(row.day),money(row.low),money(row.high),row.available?'Sì':'No'])tr.append(node('td',value));tbody.append(tr);}table.append(caption,thead,tbody);const scroll=node('div');scroll.style.overflowX='auto';scroll.append(table);view.append(scroll,node('p','* Disponibilità all’ultimo recupero del giorno; gli intervalli possono includere prezzi di prodotti non disponibili. Non è un prezzo precedente certificato per calcolare sconti.'));
 }
 select.addEventListener('change',render);render();
 }catch{body.textContent='Storico momentaneamente non disponibile. Riapri per riprovare.';loaded=false;body.remove();summary.textContent='Storico non disponibile · riapri per riprovare';}
 });return details;
}
if(typeof module==='object'&&module.exports)module.exports={summarize};if(root&&root.document){root.O4ZHistory={mount};for(const host of document.querySelectorAll('[data-history-offer]'))host.replaceChildren(mount(host.dataset.historyOffer));}
})(typeof window==='undefined'?null:window);
