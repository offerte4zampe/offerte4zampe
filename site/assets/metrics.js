(()=>{'use strict';
const key='o4z-statistics-consent-v1';let enabled=false;try{enabled=localStorage.getItem(key)==='yes'}catch{}
function syncConsent(){const permitted=enabled&&!navigator.globalPrivacyControl&&navigator.doNotTrack!=='1';try{document.cookie='__Host-o4z-statistics='+ (permitted?'yes':'no')+'; Path=/; Secure; SameSite=Lax'}catch{}}
syncConsent();
// GA4 web stream measurement ID for offerte4zampe.it.
const ga4MeasurementId='G-KMQ20X9WDE';
const ga4Configured=/^G-[A-Z0-9]+$/.test(ga4MeasurementId);
let ga4Started=false;
function ga4Allowed(){return enabled&&!navigator.globalPrivacyControl&&navigator.doNotTrack!=='1'}
function startGa4(){
  if(!ga4Configured||!ga4Allowed()||ga4Started)return;
  ga4Started=true;
  window.dataLayer=window.dataLayer||[];
  window.gtag=window.gtag||function(){window.dataLayer.push(arguments)};
  window.gtag('consent','default',{analytics_storage:'granted',ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied'});
  window.gtag('js',new Date());
  // Page views are emitted by send() to avoid double counting.
  window.gtag('config',ga4MeasurementId,{send_page_view:false});
  const script=document.createElement('script');
  script.async=true;script.src='https://www.googletagmanager.com/gtag/js?id='+encodeURIComponent(ga4MeasurementId);
  document.head.appendChild(script);
}
function syncGa4Consent(){
  if(!ga4Configured)return;
  if(ga4Allowed()){startGa4();if(ga4Started)window.gtag('consent','update',{analytics_storage:'granted'})}
  else if(ga4Started)window.gtag('consent','update',{analytics_storage:'denied'});
}
const page=location.pathname.includes('confronta-cibo')?'catalog':document.querySelector('[data-product-page], [data-canonical-product]')?'product':/^\/(index\.html)?$/.test(location.pathname)?'home':'other';
const product=location.pathname.split('/').pop().replace(/\.html$/,'');
function send(event,merchant){if(!ga4Allowed())return;fetch('/api/metrics',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({event,page,merchant,product}),keepalive:true,credentials:'omit',referrerPolicy:'no-referrer'}).catch(()=>{});if(ga4Configured){startGa4();window.gtag('event',event,{page_type:page,product_slug:product,...(merchant?{merchant}:{})})}}
const footer=document.querySelector('footer .wrap');if(footer){const p=document.createElement('p');p.className='micro';p.textContent='Statistiche facoltative: contiamo visualizzazioni, ricerche, confronti e clic. Non inviamo il testo cercato né un identificatore del visitatore. ';const b=document.createElement('button');b.type='button';b.className='btn secondary';function label(){b.textContent=enabled?'Disattiva statistiche facoltative':'Attiva statistiche facoltative';b.setAttribute('aria-pressed',String(enabled))}label();b.onclick=()=>{enabled=!enabled;syncConsent();syncGa4Consent();try{localStorage.setItem(key,enabled?'yes':'no')}catch{}label();if(enabled)send('page_view')};p.append(b);footer.append(p);}
syncGa4Consent();send('page_view');let timer;document.addEventListener('input',e=>{if(e.target.id==='catalog-query'){clearTimeout(timer);timer=setTimeout(()=>{if(e.target.value.trim())send('catalog_search')},1200)}});
document.addEventListener('click',e=>{const a=e.target.closest('a');if(a){try{if(new URL(a.href,location.href).pathname.startsWith('/go/'))return;const u=new URL(a.href,location.href);const curatedAmazon=a.dataset?.amazonAffiliate==='verified'&&u.protocol==='https:'&&u.hostname==='link.amazon'&&!u.username&&!u.password&&/^\/[A-Za-z0-9]{9}$/.test(u.pathname)&&!u.search&&!u.hash;const merchant=curatedAmazon?'Amazon':window.O4ZTrade?.merchant(a.href);if(merchant)send('merchant_click',merchant)}catch{}}const b=e.target.closest('button');if(b?.textContent==='Confronta')send('compare_add')});
})();
