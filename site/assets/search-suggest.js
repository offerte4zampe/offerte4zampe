(function(root){'use strict';
const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('it').trim();
function candidates(offers,query,now=Date.now()){
 const q=norm(query);if(q.length<2)return [];const words=q.split(/\s+/),seen=new Set();
 return offers.filter(o=>{const stamp=Date.parse(o.checked_at),title=norm(o.title);
 if(!title||o.available!==true||!Number.isFinite(stamp)||now-stamp>36*3600000||stamp>now+300000)return false;
 const hay=norm([o.title,o.variant,o.brand,o.gtin].join(' '));return words.every(w=>hay.includes(w))})
 .sort((a,b)=>Number(!norm(a.title).startsWith(q))-Number(!norm(b.title).startsWith(q))||String(a.title).localeCompare(String(b.title),'it')||String(a.variant||'').localeCompare(String(b.variant||''),'it')||String(a.merchant||'').localeCompare(String(b.merchant||''),'it'))
 .filter(o=>{const key=norm(o.title)+'|'+norm(o.variant);if(seen.has(key))return false;seen.add(key);return true}).slice(0,8);
}
let catalogPromise;
function catalog(){if(!catalogPromise)catalogPromise=fetch('data/search-index.json?v=product-id-2',{cache:'no-cache'}).then(async r=>{
 if(!r.ok)throw Error('search-index');const data=await r.json();if(!Array.isArray(data.offers))throw Error('search-index');return data.offers.filter(o=>typeof o.id==='string'&&o.id.length>0);
 }).catch(e=>{catalogPromise=null;throw e});return catalogPromise}

function mount(input,provide,choose){
 if(!input)return;
 const wrap=document.createElement('div');wrap.className='search-suggest';input.before(wrap);wrap.append(input);
 const list=document.createElement('ul');list.id=input.id+'-suggestions';list.className='search-suggest-list';list.role='listbox';list.setAttribute('aria-label','Prodotti suggeriti');list.hidden=true;wrap.append(list);
 const status=document.createElement('span');status.className='sr-only';status.setAttribute('role','status');status.setAttribute('aria-live','polite');wrap.append(status);
 input.setAttribute('role','combobox');input.setAttribute('aria-autocomplete','list');input.setAttribute('aria-controls',list.id);input.setAttribute('aria-expanded','false');input.autocomplete='off';
 let rows=[],active=-1,version=0,timer,composing=false,interacting=false;
 function close(){version++;clearTimeout(timer);list.hidden=true;active=-1;input.setAttribute('aria-expanded','false');input.removeAttribute('aria-activedescendant');status.textContent=''}
 function highlight(i){active=i;[...list.children].forEach((n,index)=>n.setAttribute('aria-selected',String(index===active)));if(i>=0){input.setAttribute('aria-activedescendant',list.children[i].id);list.children[i].scrollIntoView({block:'nearest'})}}
 function accept(i){const o=rows[i];if(!o)return;input.value=o.title;close();choose(o)}
 async function update(){
 const ticket=++version,q=input.value;if(norm(q).length<2){close();return}
 status.textContent='Ricerca suggerimenti…';
 try{const offers=await provide();if(ticket!==version||document.activeElement!==input||composing)return;rows=candidates(offers,q);list.replaceChildren();active=-1;input.removeAttribute('aria-activedescendant');
 rows.forEach((o,i)=>{const option=document.createElement('li');option.id=list.id+'-'+i;option.role='option';option.setAttribute('aria-selected','false');option.dataset.query=o.title;option.dataset.productId=o.id||'';
 const title=document.createElement('span');title.textContent=o.title;option.append(title);
 if(o.variant){const detail=document.createElement('small');detail.textContent=o.variant;option.append(detail)}
 let start=null,chosen=false;
 const chooseOnce=()=>{if(chosen)return;chosen=true;interacting=false;accept(i)};
 option.addEventListener('pointerdown',e=>{start={x:e.clientX,y:e.clientY,id:e.pointerId};interacting=true;if(e.pointerType==='mouse')e.preventDefault()});
 option.addEventListener('pointerup',e=>{const tap=start&&start.id===e.pointerId&&Math.hypot(e.clientX-start.x,e.clientY-start.y)<12;start=null;interacting=Boolean(tap);if(!tap&&document.activeElement!==input)close()});
 option.addEventListener('pointercancel',()=>{start=null;interacting=false;if(document.activeElement!==input)close()});
 option.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();chooseOnce()});list.append(option)});
 list.hidden=!rows.length;input.setAttribute('aria-expanded',String(Boolean(rows.length)));status.textContent=rows.length?rows.length+' suggerimenti. Usa le frecce e Invio per selezionare.':'Nessun suggerimento. Puoi continuare la ricerca.';
 }catch{if(ticket===version){close();status.textContent='Suggerimenti non disponibili. Puoi comunque premere Cerca.'}}
 }
 function schedule(){close();if(!composing)timer=setTimeout(update,100)}
 document.addEventListener('pointerdown',e=>{if(!wrap.contains(e.target)){interacting=false;close()}});
 input.addEventListener('input',schedule);input.addEventListener('focus',schedule);input.addEventListener('blur',()=>{if(!interacting)close()});
 input.addEventListener('compositionstart',()=>{composing=true;close()});input.addEventListener('compositionend',()=>{composing=false;schedule()});
 input.addEventListener('keydown',e=>{if(e.isComposing||composing)return;if(e.key==='Escape'){if(!list.hidden)e.preventDefault();close();return}if(e.key==='Tab'){close();return}if(list.hidden)return;
 if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();highlight(e.key==='ArrowDown'?(active+1)%rows.length:(active<0?rows.length-1:(active-1+rows.length)%rows.length))}
 else if(e.key==='Enter'&&active>=0){e.preventDefault();accept(active)}
 });
}
const api={normalizeSearch:norm,candidates,catalog,mount};if(typeof module!=='undefined'&&module.exports)module.exports=api;if(root)root.O4ZSuggest=api;
})(typeof window!=='undefined'?window:null);
