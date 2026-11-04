(function(){'use strict';
 const button=document.getElementById('mobilemenu'),nav=document.getElementById('navlinks');
 if(button&&nav){
  function setOpen(open){nav.classList.toggle('open',open);button.setAttribute('aria-expanded',String(open));button.setAttribute('aria-label',open?'Chiudi navigazione':'Apri navigazione')}
  button.addEventListener('click',()=>setOpen(button.getAttribute('aria-expanded')!=='true'));
  nav.addEventListener('click',event=>{if(event.target.closest('a'))setOpen(false)});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&button.getAttribute('aria-expanded')==='true'){setOpen(false);button.focus()}});
  document.addEventListener('click',event=>{if(!nav.contains(event.target)&&!button.contains(event.target))setOpen(false)});
  window.addEventListener('resize',()=>{if(window.innerWidth>850)setOpen(false)});
 }
 document.querySelectorAll('[data-year]').forEach(x=>x.textContent=String(new Date().getFullYear()));
})();
/* Seasonal decoration: Rome calendar, automatically ends after Halloween 2026. */
(function(){'use strict';
 const today=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Rome',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
 if(today<'2026-10-28'||today>'2026-11-01')return;
 document.documentElement.classList.add('halloween');
 const hero=document.querySelector('.shopping-hero');
 if(hero){
  const badge=hero.querySelector('.eyebrow');if(badge)badge.textContent='Halloween a 4 zampe';
  const bubble=hero.querySelector('.pet-bubble');if(bubble)bubble.textContent='Dolcetto o crocchetta?';
  const art=hero.querySelector('.pet-hero-art');
  if(art&&!art.querySelector('.halloween-art')){
   const decor=document.createElement('img');decor.className='halloween-art';decor.src='/assets/halloween.svg';decor.alt='';decor.setAttribute('aria-hidden','true');decor.width=640;decor.height=560;art.append(decor);
  }
 }
})();

// Preserve already shared manual calculator fragments after moving the tool.
if(typeof location!=='undefined'&&location.pathname.replace(/\.html$/,'')==='/confronta-cibo'&&new URLSearchParams(location.hash.slice(1)).get('v')==='1')location.replace('/calcolatore'+location.hash);

// Festive themes are date-gated in Europe/Rome; normal site remains unchanged.
// The module adds only decoration; it never touches products, prices or discounts.
(function(){
 if(!document.head || document.getElementById('o4z-season-module'))return;
 const script=document.createElement('script');
 script.id='o4z-season-module';
 script.type='module';
 script.src='/assets/seasonal-theme.mjs?v=2026-2';
 document.head.append(script);
})();
