/* Expiration is enforced even when a cached document predates the next build. */
(function(){'use strict';
const cards=[...document.querySelectorAll('.coupon')],filters=[...document.querySelectorAll('.filter')];
let shop='all';
function refresh(){
 let count=0;
 for(const card of cards){const until=Date.parse(card.dataset.validUntil);const now=Date.now();card.hidden=!Number.isFinite(until)||now>=until||(shop!=='all'&&shop!==card.dataset.shop);const recheck=card.dataset.recheckAfter;if(recheck){const status=card.querySelector('.status');if(status){const due=Date.parse(recheck);status.textContent=Number.isFinite(due)&&now>=due?'Da riconfermare':'Codice concordato con il partner · confermato dal titolare';}}if(!card.hidden)count++}
 document.querySelector('.count').textContent=count+(count===1?' codice disponibile':' codici disponibili');
 document.querySelector('#coupon-empty').hidden=count>0;
}
filters.forEach(b=>b.addEventListener('click',()=>{shop=b.dataset.shop;filters.forEach(f=>f.setAttribute('aria-pressed',String(f===b)));refresh()}));
document.querySelectorAll('.copy').forEach(b=>b.addEventListener('click',async()=>{
 const card=b.closest('.coupon');refresh();if(card.hidden)return;
 const toast=document.querySelector('.toast');
 try{await navigator.clipboard.writeText(b.dataset.code);toast.textContent='Codice '+b.dataset.code+' copiato. Controlla i requisiti e il totale nel negozio.'}
 catch{toast.textContent='Seleziona e copia il codice '+b.dataset.code+' dal riquadro.'}
}));
document.querySelectorAll('.coupon-visit').forEach(a=>a.addEventListener('click',e=>{refresh();if(a.closest('.coupon').hidden)e.preventDefault()}));
refresh();setInterval(refresh,60000);document.addEventListener('visibilitychange',refresh);
})();
