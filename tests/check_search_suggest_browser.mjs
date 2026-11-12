import assert from 'node:assert/strict';
import {createRequire} from 'node:module';const require=createRequire(import.meta.url),amazonModel=require('../site/assets/amazon-links.js'),metadata=require('../site/assets/catalog-metadata.js'),productMetadata=require('../site/assets/product-metadata.js');
export async function checkSuggestions(page,origin,catalog){
 const now=Date.parse(catalog.generated_at),o=catalog.offers.find(o=>o.available&&typeof o.title==='string'&&o.title.length>4&&Number.isFinite(Date.parse(o.checked_at))&&now-Date.parse(o.checked_at)<=36*3600000&&Date.parse(o.checked_at)<=now+300000);
 assert(o,'Fresh catalog fixture required');const query=o.title.slice(0,Math.min(8,o.title.length));
 const navigations=[];const recordNavigation=frame=>{if(frame===page.mainFrame())navigations.push(frame.url())};page.on('framenavigated',recordNavigation);
 const homeRequests=[];const record=r=>homeRequests.push(r.url());page.on('request',record);
 await page.goto(origin+'/index.html',{waitUntil:'domcontentloaded'});
 await page.focus('#home-query');await page.type('#home-query',query);
 await page.waitForSelector('#home-query-suggestions [role=option]',{visible:true,timeout:30000});
 assert.equal(await page.$eval('#home-query',e=>e.getAttribute('aria-expanded')),'true');
 assert(await page.$$eval('#home-query-suggestions [role=option]',es=>es.length<=8));
 assert(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth<=1));
 assert(await page.$eval('#home-query-suggestions',e=>{const box=e.getBoundingClientRect(),y=Math.min(box.bottom-10,innerHeight-10),x=box.left+box.width/2;return y<=box.top||e.contains(document.elementFromPoint(x,y))}),'Suggestions must not be clipped by hero');
 await page.screenshot({path:'browser-reports/search-suggestions-mobile.png',fullPage:true});
 assert(homeRequests.some(url=>url.includes('/data/search-index.json')),'Home must use compact search index');
 assert(!homeRequests.some(url=>url.endsWith('/data/catalog.json.gz')),'Home search must not download the full catalog');
 page.off('request',record);
 await page.keyboard.press('ArrowDown');
 const expected=await page.$eval('#home-query-suggestions [aria-selected=true]',e=>e.dataset.productId);
 assert(await page.$eval('#home-query',e=>Boolean(e.getAttribute('aria-activedescendant'))));
 await Promise.all([page.waitForNavigation({waitUntil:'domcontentloaded'}),page.keyboard.press('Enter')]);
 assert.equal(new URL(page.url()).pathname,'/prodotto/'+catalog.offers.find(o=>o.id===expected).product_slug);
 // Continue compatibility checks against the explicitly requested legacy endpoint.
 await page.goto(origin+'/prodotto.html?id='+encodeURIComponent(expected),{waitUntil:'domcontentloaded'});
 await page.waitForSelector('#product-shops [data-product-shop]',{timeout:30000});
 assert.equal(await page.$$eval('#product-shops [data-product-shop]',rows=>rows.length),new Set([...catalog.sources.map(s=>s.id),'zooplus','bitiba']).size);
 const zooplus=await page.$eval('[data-product-shop="zooplus"]',e=>({text:e.textContent,links:e.querySelectorAll('a').length}));
 assert(zooplus.text.includes('Disponibilità: non verificata'));assert(zooplus.text.includes('Catalogo zooplus non ancora collegato'));assert.equal(zooplus.links,0);
 const bitiba=await page.$eval('[data-product-shop="bitiba"]',e=>({text:e.textContent,links:e.querySelectorAll('a').length}));
 assert(bitiba.text.includes('Disponibilità: non verificata'));assert(bitiba.text.includes('Catalogo bitiba non ancora collegato'));assert.equal(bitiba.links,0);
 const seed=catalog.offers.find(o=>o.id===expected);assert(seed);assert.equal(await page.$eval('#product-title',e=>e.textContent),productMetadata.name(seed.canonical_title||seed.title));
 const shareURL=await page.$eval('#product-share-url',e=>e.value);
 assert.equal(new URL(shareURL).origin,'https://offerte4zampe.it');assert.equal(new URL(shareURL).pathname,'/prodotto');assert.equal(new URL(shareURL).searchParams.get('id'),expected);assert.deepEqual([...new URL(shareURL).searchParams.keys()],['id']);
 await page.evaluate(()=>Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async()=>{throw Error('denied')}}}));
 await page.$eval('#product-share button:last-of-type',e=>e.click());
 await page.waitForFunction(()=>document.querySelector('#product-share [role=status]').textContent.includes('manualmente'));
 assert.equal(await page.$eval('#product-share-url',e=>e.readOnly),true);
 const catalogSearches=await page.$$eval('#product-shops [data-catalog-search]',rows=>rows.map(a=>a.href));for(const href of catalogSearches){const u=new URL(href);assert.equal(u.origin,origin);assert.equal(u.pathname,'/confronta-cibo');assert(catalog.sources.some(s=>s.name===u.searchParams.get('shop')));}
 const outbound=await page.$$eval('#product-shops a:not([data-shipping-conditions]):not([data-product-report]):not([data-catalog-search])',rows=>rows.map(a=>({href:a.href,rel:a.rel})));
 for(const a of outbound){const u=new URL(a.href);assert.equal(u.origin,origin);assert(u.pathname.startsWith('/go/'));assert(catalog.offers.some(o=>o.id===decodeURIComponent(u.pathname.slice(4))),'Exact catalog offer required');for(const rel of ['sponsored','nofollow','noopener'])assert(a.rel.split(' ').includes(rel))}
 assert(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth<=1));
 await page.select('#product-quantity','2');await page.select('#product-territory','special');
 assert(await page.$$eval('[data-shipping-estimate]',rows=>rows.every(e=>e.textContent.includes('Totale non calcolato'))));
 assert.equal(await page.$$eval('#product-shops [data-product-shop]',rows=>rows.length),new Set([...catalog.sources.map(s=>s.id),'zooplus','bitiba']).size);
 await page.select('#product-territory','standard');
 assert.equal(await page.$eval('#product-quantity',e=>e.value),'2');
 await page.screenshot({path:'browser-reports/product-mobile.png',fullPage:true});
 await page.goto(origin+'/index.html',{waitUntil:'domcontentloaded'});await page.focus('#home-query');await page.type('#home-query',query);await page.waitForSelector('#home-query-suggestions [role=option]',{visible:true});const clickedId=await page.$eval('#home-query-suggestions [role=option]',e=>e.dataset.productId);await Promise.all([page.waitForNavigation({waitUntil:'domcontentloaded'}),page.tap('#home-query-suggestions [role=option]')]);assert.equal(new URL(page.url()).pathname,'/prodotto/'+catalog.offers.find(o=>o.id===clickedId).product_slug);assert(!navigations.some(url=>url.includes('confronta-cibo')),'Home suggestion must navigate directly without comparator intermediate');page.off('framenavigated',recordNavigation);
 await page.goto(origin+'/confronta-cibo.html',{waitUntil:'domcontentloaded'});
 await page.click('#catalog-load');
 await page.waitForSelector('#catalog-query[role=combobox]',{timeout:60000}).catch(async error=>{console.error('Catalog readiness failure',await page.$eval('#catalog-status',e=>e.textContent));throw error});
 await page.focus('#catalog-query');await page.$eval('#catalog-query',(e,q)=>{e.value=q;e.dispatchEvent(new Event('input',{bubbles:true}))},query);
 await page.waitForSelector('#catalog-query-suggestions [role=option]',{visible:true});
 await page.keyboard.press('Escape');assert.equal(await page.$eval('#catalog-query-suggestions',e=>e.hidden),true);
 await page.$eval('#catalog-query',(e,q)=>{e.value=q;e.dispatchEvent(new Event('input',{bubbles:true}))},query);
 await page.waitForSelector('#catalog-query-suggestions [role=option]',{visible:true});
 const selected=await page.$eval('#catalog-query-suggestions [role=option]',e=>e.dataset.productId);
 await Promise.all([page.waitForNavigation({waitUntil:'domcontentloaded'}),page.tap('#catalog-query-suggestions [role=option]')]);
 assert.equal(new URL(page.url()).pathname,'/prodotto/'+catalog.offers.find(o=>o.id===selected).product_slug);

 const links=await page.evaluate(async()=>{const r=await fetch('/data/amazon-links.json');return r.json()});
 const mapping=links.links.find(row=>catalog.offers.some(o=>o.id===row.offer_id));assert(mapping,'At least one verified mapping must exist in catalog');
 await page.goto(origin+'/prodotto.html?id='+encodeURIComponent(mapping.offer_id),{waitUntil:'domcontentloaded'});
 await page.waitForSelector('#product-amazon a',{visible:true,timeout:30000});
 const amazon=await page.$eval('#product-amazon a',e=>({href:e.href,rel:e.rel,text:e.textContent}));
 const target=new URL(amazon.href);assert.equal(target.hostname,'www.amazon.it');assert.equal(target.pathname,'/dp/'+mapping.asin);assert.equal(target.searchParams.get('tag'),links.tracking_id);assert(amazon.rel.includes('sponsored'));assert.equal(amazon.text,'Verifica prezzo su Amazon ↗');
 assert(await page.$eval('#product-amazon',e=>!e.textContent.includes('€')&&!e.textContent.includes('Disponibile al rilevamento')));
 assert.equal(await page.$$eval('#product-shops [data-product-shop]',rows=>rows.length),new Set([...catalog.sources.map(s=>s.id),'zooplus','bitiba']).size);
 await page.select('#product-quantity','3');assert.equal(await page.$eval('#product-amazon a',e=>e.href),amazon.href);
 const unmapped=catalog.offers.find(o=>!amazonModel.comparisonLink(o,catalog.offers,links,now));assert(unmapped);
 await page.goto(origin+'/prodotto.html?id='+encodeURIComponent(unmapped.id),{waitUntil:'domcontentloaded'});
 await page.waitForSelector('#product-shops [data-product-shop]',{timeout:30000});assert.equal(await page.$eval('#product-amazon',e=>e.hidden),false);assert.equal(await page.$eval('#product-amazon',e=>e.querySelectorAll('a').length),0);assert((await page.$eval('#product-amazon',e=>e.textContent)).includes('Disponibilità: non verificata'));

 // Validate active editorial mappings; retired feed IDs must not produce destinations.
 for(const entry of links.links){
  const seed=catalog.offers.find(o=>o.id===entry.offer_id);if(!seed){assert.equal(amazonModel.comparisonLink({id:entry.offer_id},catalog.offers,links,now),null,'Retired offer must not generate an affiliate destination');continue;}
  for(const key of ['title','brand','variant','gtin'])assert.equal(key==='brand'?metadata.brand(seed[key]):String(seed[key]??''),key==='brand'?metadata.brand(entry[key]):String(entry[key]??''),'Mapped identity changed: '+entry.offer_id+' '+key);
  await page.goto(origin+'/prodotto.html?id='+encodeURIComponent(entry.offer_id),{waitUntil:'domcontentloaded'});
  await page.waitForSelector('#product-amazon a',{visible:true,timeout:30000});
  assert.equal(await page.$eval('#product-title',e=>e.textContent),seed.canonical_title||seed.title);
  const href=await page.$eval('#product-amazon a',e=>e.href);
  if(entry.sitestripe_url)assert.equal(href,entry.sitestripe_url);
  else{assert.equal(new URL(href).pathname,'/dp/'+entry.asin);assert.equal(new URL(href).searchParams.get('tag'),links.tracking_id);}
  assert(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth<=1));
 }

 const productHistoryRequests=[];const trackProductHistory=request=>{if(request.url().includes('/data/history/'))productHistoryRequests.push(request.url())};page.on('request',trackProductHistory);
 const food=catalog.offers.find(o=>o.available&&o.weight_kg>0&&/crocchette|umido|(?:cani|gatti) > cibo > secco/i.test(o.category||'')&&now-Date.parse(o.checked_at)<=36*3600000);assert(food,'Fresh food fixture');
 await page.goto(origin+'/prodotto.html?id='+encodeURIComponent(food.id),{waitUntil:'domcontentloaded'});
 await page.waitForSelector('[data-product-basket]',{timeout:30000});
 const initial=await page.evaluate(()=>localStorage.getItem('o4z-basket-v1'));
 await page.evaluate(()=>localStorage.removeItem('o4z-basket-v1'));
 await page.$eval('[data-product-basket="'+food.id+'"]',e=>e.scrollIntoView({behavior:'instant',block:'center'}));
 assert(await page.evaluate(()=>innerWidth<=394),'Product controls must not widen the mobile viewport');
 await page.tap('[data-product-basket="'+food.id+'"]');
 await page.waitForFunction(()=>Boolean(localStorage.getItem('o4z-basket-v1')),{timeout:10000});
 assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('o4z-basket-v1'))[0].quantity),1);
 assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('o4z-basket-v1'))[0].id),food.id);
 await page.evaluate(value=>value===null?localStorage.removeItem('o4z-basket-v1'):localStorage.setItem('o4z-basket-v1',value),initial);
 const report=await page.$eval('[data-product-report]',e=>e.href);assert.equal(new URLSearchParams(new URL(report).hash.slice(1)||new URL(report).search).get('id'),food.id);
 await page.$eval('.daily-cost',e=>{e.open=true;const input=e.querySelector('input');input.value='150';input.dispatchEvent(new Event('input',{bubbles:true}))});
 const daily=await page.$eval('.daily-cost [role=status]',e=>e.textContent);assert(daily.includes('al giorno'));
 assert.equal(productHistoryRequests.length,0,'Product history must remain lazy');
 await page.$eval('.observed-history',e=>e.open=true);
 await page.waitForFunction(()=>document.querySelector('.observed-history').textContent.includes('Periodo osservato'),{timeout:30000});
 await page.select('#product-quantity','2');
 assert.equal(await page.$eval('.daily-cost input',e=>e.value),'150');
 assert.equal(await page.$eval('.daily-cost [role=status]',e=>e.textContent),daily);
 assert(await page.$eval('.observed-history',e=>e.open));
 assert.equal(productHistoryRequests.length,1,'Quantity changes must reuse loaded history');page.off('request',trackProductHistory);
 assert(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth<=1));

}
