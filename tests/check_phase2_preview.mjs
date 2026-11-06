// Exercise a local/isolated preview only. Never follow an affiliate redirect externally.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {gunzipSync} from 'node:zlib';
import {assertPreviewRedirect} from './phase2_preview_redirect.mjs';
const origin=new URL(process.env.PREVIEW_ORIGIN||process.argv[2]||'http://127.0.0.1:8791').origin;
const host=new URL(origin).hostname;
assert(['localhost','127.0.0.1','[::1]'].includes(host)||(/^phase2-[a-z0-9-]+\..*workers\.dev$/i.test(host)),'Only a local or phase2 isolated preview is allowed');
const reports=process.env.PREVIEW_REPORTS||'browser-reports/phase2';
const pkg=path.join(process.env.PUPPETEER_ROOT,'node_modules/puppeteer-core');
const manifest=JSON.parse(await fs.readFile(path.join(pkg,'package.json')));
const {default:puppeteer}=await import(pathToFileURL(path.join(pkg,manifest.main)).href);
const raw=Buffer.from(await (await fetch(origin+'/data/catalog.json.gz')).arrayBuffer());
const catalog=JSON.parse(raw[0]===31&&raw[1]===139?gunzipSync(raw):raw);
const stamp=Date.now(),fresh=o=>o.available&&Number.isFinite(Date.parse(o.checked_at))&&stamp-Date.parse(o.checked_at)<=36*3600000;
const routes=[];
for(const source of catalog.sources){
 const o=catalog.offers.find(o=>o.merchant_id===source.id&&fresh(o)&&(o.affiliate_url||o.url));
 assert(o,'A fresh available offer is required for '+source.id);
 const r=await fetch(origin+'/go/'+encodeURIComponent(o.id)+'?from=product',{redirect:'manual'});
 assertPreviewRedirect(r,o.affiliate_url||o.url);
 routes.push({merchant:source.id,status:r.status,target_preserved:true});
}
const seed=catalog.offers.find(o=>o.gtin==='04002973213353'&&o.quantity?.volume_ml===7000&&fresh(o));
assert(seed,'Real Cat’s Best 7 L fixture required');
const route='/prodotto/'+seed.product_slug;
let browser;
const errors=[],metrics=[],outside=[],popups=[];
const result={origin,scope:'isolated-preview-no-production-deployment',snapshot:catalog.generated_at,redirects:routes};
try{
 browser=await puppeteer.launch({executablePath:process.env.CHROME_PATH,headless:true,args:['--disable-dev-shm-usage']});
 const page=await browser.newPage();
 await page.setViewport({width:393,height:852,isMobile:true,hasTouch:true});
 await page.setRequestInterception(true);
 page.on('pageerror',e=>errors.push(String(e)));
 page.on('request',request=>{const u=request.url();if(u.startsWith(origin+'/api/metrics'))metrics.push(u);if(u.startsWith(origin)||u.startsWith('data:'))return request.continue();outside.push(new URL(u).hostname);return request.abort();});
 const response=await page.goto(origin+route,{waitUntil:'networkidle0'});
 assert.equal(response.status(),200);assert.equal(response.headers()['x-o4z-security-mode'],'report-only');
 assert((await page.$eval('.canonical-offers',e=>e.textContent)).includes('Condizioni da ricontrollare'));
 assert((await page.$eval('.canonical-offers',e=>e.textContent)).includes('Italia continentale standard'));
 assert((await page.$eval('.canonical-offers',e=>e.textContent)).includes('€/l'));
 assert.equal(await page.$eval('link[rel=canonical]',e=>e.href),'https://offerte4zampe.it'+route);
 assert.equal(metrics.length,0,'No optional metrics before consent');
 await page.select('select[name=quantity]','2');await page.select('select[name=territory]','special');
 await Promise.all([page.waitForNavigation({waitUntil:'networkidle0'}),page.click('.canonical-controls button')]);
 assert.equal(new URL(page.url()).origin,origin);assert.equal(new URL(page.url()).searchParams.get('quantity'),'2');assert.equal(new URL(page.url()).searchParams.get('territory'),'special');
 assert.equal(await page.$eval('meta[name=robots]',e=>e.content),'noindex,follow');
 assert.equal(await page.$eval('a[href$="#main"]',e=>new URL(e.href).origin),origin);
 result.recalculation={same_origin:true,quantity:2,territory:'special',unknown_not_zero:true};
 await page.goto(origin+route,{waitUntil:'networkidle0'});
 await page.$eval('.observed-history',e=>e.open=true);
 await page.waitForSelector('.observed-history table',{timeout:30000});
 result.history={loaded:true,rows:await page.$$eval('.observed-history tbody tr',e=>e.length)};
 assert(result.history.rows>0);
 const link=await page.$eval('.canonical-offers a[href^="/go/"]',e=>({href:e.href,rel:e.rel,target:e.target}));
 assert.equal(link.target,'_blank');for(const rel of ['sponsored','nofollow','noopener'])assert(link.rel.split(' ').includes(rel));
 // Keep this one test click in the intercepted tab so no popup can escape interception.
 // The application's original target=_blank and sponsored relations were asserted above.
 await page.$eval('.canonical-offers a[href^="/go/"]',e=>e.target='_self');
 const externalAttempt=page.waitForRequest(r=>!r.url().startsWith(origin)&&!r.url().startsWith('data:'),{timeout:15000});
 await page.click('.canonical-offers a[href^="/go/"]');const attempted=await externalAttempt;
 popups.push(attempted.url());
 result.merchant_click={application_target_blank_verified:true,same_tab_interception_harness:true,external_request_blocked:true,affiliate_redirect_observed:popups.length>0};
 const initialMetricCount=metrics.length;
 await page.goto(origin+'/privacy',{waitUntil:'networkidle0'});
 const consent='footer button[aria-pressed]';await page.waitForSelector(consent);
 assert.equal(await page.$eval(consent,e=>e.getAttribute('aria-pressed')),'false');
 await page.click(consent);await page.waitForFunction(()=>localStorage.getItem('o4z-statistics-consent-v1')==='yes');
 await page.waitForFunction(()=>document.querySelector('footer button[aria-pressed="true"]'));
 await page.click(consent);await page.waitForFunction(()=>localStorage.getItem('o4z-statistics-consent-v1')==='no');
 assert.equal(await page.$eval(consent,e=>e.getAttribute('aria-pressed')),'false');
 assert(metrics.length>initialMetricCount,'Opt-in metrics should be sent only to preview');
 result.consent={initially_off:true,opt_in:true,opt_out:true,metrics_only_preview:metrics.every(u=>new URL(u).origin===origin)};
 assert.deepEqual(errors,[]);result.js_errors=errors;result.status='passed';
 await fs.mkdir(reports,{recursive:true});await fs.writeFile(path.join(reports,'acceptance.json'),JSON.stringify(result,null,2));
 console.log(JSON.stringify(result));
}catch(error){await fs.mkdir(reports,{recursive:true});await fs.writeFile(path.join(reports,'acceptance.json'),JSON.stringify({...result,status:'failed',error:String(error),js_errors:errors},null,2));throw error;}finally{await browser?.close();}
