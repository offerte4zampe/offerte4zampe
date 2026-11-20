// Offline generated-site HTTP smoke test; exercises the actual Worker fetch handler
// against a temporary local asset server. Never calls Cloudflare or Telegram.
// AMAZON_LINKS_ENABLED=true in this test only to validate the gated canonical SSR.
import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import worker from '../worker/index.mjs';
import {slugForOffer} from '../worker/canonical-product.mjs';
import {resolveAmazonOffer} from '../worker/amazon-product.mjs';

const site=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../site');
const reportDir=process.env.AMAZON_REPORT_DIR||'browser-reports/amazon-local';
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css','.json':'application/json','.gz':'application/gzip','.svg':'image/svg+xml','.png':'image/png','.webp':'image/webp'};
let assetsRead=0;
const env={PRICE_TRACKING_ENABLED:'false',AMAZON_LINKS_ENABLED:'true',ASSETS:{fetch:async req=>{
 assetsRead++;
 let requested=decodeURIComponent(new URL(req.url).pathname);
 const requestedFile=requested==='/'?'/index.html':requested==='/prodotto'?'/prodotto.html':requested;
 let full=path.resolve(site,'.'+requestedFile);
 if(!path.extname(full))full+='.html';
 if(!full.startsWith(site+path.sep))return new Response(null,{status:403});
 try{const data=await fs.readFile(full);return new Response(req.method==='HEAD'?null:data,{status:200,headers:{'Content-Type':mime[path.extname(full)]||'application/octet-stream'}})}catch{return new Response(null,{status:404})}
}}};
let expiredEnv=null;
const server=http.createServer(async(req,res)=>{
 try{
  const address='http://127.0.0.1:'+server.address().port+req.url;
  const fixture=new URL(address).searchParams.get('amazon_test_fixture');
  const selectedEnv=fixture==='expired'?expiredEnv:env;assert(selectedEnv,'Expired registry fixture must be initialized');
  const response=await worker.fetch(new Request(address,{method:req.method}),selectedEnv,{waitUntil(){}});
  res.writeHead(response.status,Object.fromEntries(response.headers));
  res.end(Buffer.from(await response.arrayBuffer()));
 }catch(e){res.writeHead(500);res.end('Local Worker error');console.error(e)}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const base='http://127.0.0.1:'+server.address().port;
const results=[];
let browser=null;
try{
 const registryPath=path.join(site,'data/amazon-links.json');
 const registryBytes=await fs.readFile(registryPath);const registryHash=createHash('sha256').update(registryBytes).digest('hex');
 const config=JSON.parse(registryBytes),now=Date.now();
 let amazonSlug=null,amazonMapping=null,expectedTarget=null;
 for(const row of config.links){
  const slug=await slugForOffer(env,base,row.offer_id);if(!slug)continue;
  const prefix=createHash('sha256').update(slug).digest('hex').slice(0,2);
  const shard=JSON.parse(await fs.readFile(path.join(site,'data/canonical-products',prefix+'.json'),'utf8'));
  const product=shard[slug];if(!product)continue;
  const resolved=resolveAmazonOffer(product,config,now);
  const seed=product.offers?.find(o=>o.id===row.offer_id);
  const direct=seed?resolveAmazonOffer({offers:[seed]},{tracking_id:config.tracking_id,links:[row]},now):null;
  if(!resolved||!direct||resolved.url!==direct.url)continue;
  const checked=Date.parse(String(row.checked_at||'')+'T00:00:00Z');
  assert(Number.isFinite(checked)&&checked<=now&&now-checked<=30*86400000,'Selected proof must independently be current and non-future');
  const normalize=value=>String(value??'').trim().toLocaleLowerCase('it');
  for(const key of ['brand','title','variant','gtin'])assert.equal(normalize(seed[key]),normalize(row[key]),'Selected registry identity must match exact offer: '+key);
  const expected=Object.hasOwn(row,'sitestripe_url')?row.sitestripe_url:'https://www.amazon.it/dp/'+row.asin+'?tag='+encodeURIComponent(config.tracking_id);
  assert.equal(resolved.url,expected,'Resolver must preserve the exact currently valid registry destination');
  const target=new URL(expected);assert.equal(target.protocol,'https:');assert.equal(target.username,'');assert.equal(target.password,'');assert.equal(target.port,'');
  if(Object.hasOwn(row,'sitestripe_url')){
   assert.equal(row.owner_variant_confirmed,true);assert.equal(row.resolved_asin,row.asin);assert.equal(row.resolved_tracking_id,config.tracking_id);
   assert.equal(target.hostname,'link.amazon');assert.match(target.pathname,/^\/[A-Za-z0-9]{9}$/);assert.equal(target.search,'');assert.equal(target.hash,'');
  }else{
   assert.equal(target.hostname,'www.amazon.it');assert.equal(target.pathname,'/dp/'+row.asin);assert.equal(target.searchParams.get('tag'),config.tracking_id);
  }
  amazonSlug=slug;amazonMapping=row;expectedTarget=expected;break;
 }
 assert(amazonSlug&&amazonMapping&&expectedTarget,'A currently valid Amazon mapping and canonical product are mandatory; never skip the positive fixture');
 // Test-only asset overlay: expire every editorial row in memory so that no
 // alternative verified mapping can hide a stale-evidence regression.
 const expiredConfig=structuredClone(config);
 for(const row of expiredConfig.links)row.checked_at=new Date(now-31*86400000).toISOString().slice(0,10);
 expiredEnv={...env,ASSETS:{fetch:async req=>new URL(req.url).pathname==='/data/amazon-links.json'
  ?new Response(JSON.stringify(expiredConfig),{headers:{'Content-Type':'application/json'}}):env.ASSETS.fetch(req)}};
 const withoutSlug=await (async()=>{
  try{
   const dataDir=path.join(site,'data','canonical-products');
   for(const filename of (await fs.readdir(dataDir)).filter(x=>x.endsWith('.json')).slice(0,256)){
    const shard=JSON.parse(await fs.readFile(path.join(dataDir,filename),'utf8'));
    for(const [slug,p] of Object.entries(shard)){
     if(slug!==amazonSlug&&p?.offers?.every(o=>!config.links.some(x=>x.offer_id===o.id)))return slug;
    }
   }
  }catch{}
  return null;
 })();
 assert(withoutSlug,'An ordinary canonical product is mandatory');
 const entries=[
  ['home','/','200'],
  ['privacy','/privacy','200'],
  ['favorites','/preferiti','410'],
  ['favorites_html','/preferiti.html','410'],
  ['history','/data/history/00.json.gz','410'],
  ['price_history','/data/price-history.json.gz','410'],
  ['price_alert','/api/price-alerts','410'],
  ['amazon_product','/prodotto/'+amazonSlug,'200'],
  ['expired_amazon_product','/prodotto/'+amazonSlug+'?amazon_test_fixture=expired','200'],
  ['ordinary_product','/prodotto/'+withoutSlug,'200']
 ];
 for(const [name,p,expected] of entries){
  const before=assetsRead,response=await fetch(base+p,{redirect:'manual'}),html=await response.text();
  const row={name,path:p,status:response.status,expected:Number(expected),length:html.length,
    history_text:/storico dei prezzi|minimo storico|massimo storico|avvisi di prezzo|prezzo desiderato/i.test(html),
    history_hooks:/data-history-offer=|data-watch-save=/.test(html)};
  if(name==='amazon_product'){
   const anchors=[...html.matchAll(/<a\b([^>]*)>/gi)].filter(match=>/\bdata-amazon-affiliate=["']verified["']/.test(match[1]));
   assert.equal(anchors.length,1,'Exactly one verified Amazon CTA is required');
   const href=/\bhref=["']([^"']+)["']/.exec(anchors[0][1])?.[1]?.replaceAll('&amp;','&');
   assert.equal(href,expectedTarget,'Rendered destination must exactly equal the currently valid registry URL');
   const rel=/\brel=["']([^"']+)["']/.exec(anchors[0][1])?.[1]||'';
   for(const token of ['sponsored','nofollow','noopener','noreferrer'])assert(rel.split(/\s+/).includes(token));
   row.amazon_link=true;row.destination_kind=Object.hasOwn(amazonMapping,'sitestripe_url')?'owner_confirmed_sitestripe':'tagged_dp';
   row.disclosure=html.includes('In qualità di Affiliato Amazon io ricevo un guadagno dagli acquisti idonei');
   row.checkout_notice=html.includes('Il prezzo valido è quello indicato su Amazon al momento dell’acquisto.');
  }
  if(name==='ordinary_product'||name==='expired_amazon_product')row.amazon_link=html.includes('data-amazon-verified')||html.includes('data-amazon-affiliate');
  if(name==='favorites')row.informative=html.includes('Funzione non disponibile')&&html.includes('/confronta-cibo');
  if(name==='history'||name==='price_history'||name==='price_alert'||name==='favorites')row.asset_reads=assetsRead-before;
  results.push(row);
  assert.equal(response.status,Number(expected),name);
  if(name==='home'||name==='privacy'||name.includes('product')){assert(!row.history_text,name);assert(!row.history_hooks,name)}
  if(name==='favorites'){assert(row.informative);assert.equal(row.asset_reads,0)}
  if(name==='history'||name==='price_history'||name==='price_alert')assert.equal(row.asset_reads,0);
  if(name==='amazon_product'){assert(row.amazon_link&&row.disclosure&&row.checkout_notice)}
  if(name==='ordinary_product'||name==='expired_amazon_product')assert(!row.amazon_link,'Expired or absent editorial evidence must not render an Amazon CTA');
 }
 assert.equal(createHash('sha256').update(await fs.readFile(registryPath)).digest('hex'),registryHash,'The on-disk editorial registry and proof dates must remain unchanged');
 await fs.mkdir(reportDir,{recursive:true});
 const packageRoot=process.env.PUPPETEER_ROOT&&path.join(process.env.PUPPETEER_ROOT,'node_modules/puppeteer-core');
 if(packageRoot&&process.env.CHROME_PATH){
  try{
   const meta=JSON.parse(await fs.readFile(path.join(packageRoot,'package.json'),'utf8'));
   const {default:puppeteer}=await import('file://'+path.join(packageRoot,meta.main));
   browser=await puppeteer.launch({headless:true,executablePath:process.env.CHROME_PATH,args:['--no-sandbox','--disable-dev-shm-usage']});
   for(const [name,viewport] of [['desktop',{width:1365,height:900}],['mobile',{width:393,height:852,isMobile:true,hasTouch:true}]]){
    const page=await browser.newPage();await page.setViewport(viewport);
    for(const [label,route] of [['home','/'],['privacy','/privacy'],['favorites','/preferiti'],...(amazonSlug?[['amazon','/prodotto/'+amazonSlug]]:[])]){
     await page.goto(base+route,{waitUntil:'domcontentloaded',timeout:30000});
     const leaked=await page.evaluate(()=>({
       historic:!!document.querySelector('[data-history-offer],.observed-history,[data-watch-add],[data-watch-save]'),
       favoriteNav:!!document.querySelector('a[href^="/preferiti"]'),
       pricePromise:/storico dei prezzi|minimo storico|massimo storico|avvisi di prezzo|prezzo desiderato/i.test(document.body.innerText)
     }));
     assert.deepEqual(leaked,{historic:false,favoriteNav:false,pricePromise:false},label+' '+name);

     await page.screenshot({path:path.join(reportDir,label+'-'+name+'.png'),fullPage:true});
    }
    await page.close();
   }
  }catch(e){results.push({screenshots:'unavailable',reason:String(e.message).slice(0,180)})}
 }
 await fs.writeFile(path.join(reportDir,'http-results.json'),JSON.stringify({results,amazon_slug:amazonSlug,ordinary_slug:withoutSlug,site:'generated local only',no_deploy:true,no_telegram_requests:true},null,2));
 console.log(JSON.stringify({results,amazon_slug:amazonSlug,ordinary_slug:withoutSlug}));
 if(!amazonSlug||!withoutSlug)throw Error('Both an Amazon-matched and an ordinary canonical product are required for complete smoke test');
}finally{await browser?.close().catch(()=>{});await new Promise(resolve=>server.close(resolve))}
