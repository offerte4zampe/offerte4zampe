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
const server=http.createServer(async(req,res)=>{
 try{
  const address='http://127.0.0.1:'+server.address().port+req.url;
  const response=await worker.fetch(new Request(address,{method:req.method}),env,{waitUntil(){}});
  res.writeHead(response.status,Object.fromEntries(response.headers));
  res.end(Buffer.from(await response.arrayBuffer()));
 }catch(e){res.writeHead(500);res.end('Local Worker error');console.error(e)}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const base='http://127.0.0.1:'+server.address().port;
const results=[];
let browser=null;
try{
 const config=JSON.parse(await fs.readFile(path.join(site,'data/amazon-links.json'),'utf8'));
 let amazonSlug=null;
 for(const row of config.links){
  amazonSlug=await slugForOffer(env,base,row.offer_id);
  if(amazonSlug)break;
 }
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
 const entries=[
  ['home','/','200'],
  ['privacy','/privacy','200'],
  ['favorites','/preferiti','410'],
  ['favorites_html','/preferiti.html','410'],
  ['history','/data/history/00.json.gz','410'],
  ['price_history','/data/price-history.json.gz','410'],
  ['price_alert','/api/price-alerts','410'],
  ...(amazonSlug?[['amazon_product','/prodotto/'+amazonSlug,'200']]:[]),
  ...(withoutSlug?[['ordinary_product','/prodotto/'+withoutSlug,'200']]:[])
 ];
 for(const [name,p,expected] of entries){
  const before=assetsRead,response=await fetch(base+p,{redirect:'manual'}),html=await response.text();
  const row={name,path:p,status:response.status,expected:Number(expected),length:html.length,
    history_text:/storico dei prezzi|minimo storico|massimo storico|avvisi di prezzo|prezzo desiderato/i.test(html),
    history_hooks:/data-history-offer=|data-watch-save=/.test(html)};
  if(name==='amazon_product'){
   row.amazon_link=/https:\/\/www\.amazon\.it\/dp\/[A-Z0-9]{10}\?tag=offerte4zam0c-21/.test(html);
   row.disclosure=html.includes('In qualità di Affiliato Amazon io ricevo un guadagno dagli acquisti idonei');
   row.checkout_notice=html.includes('Il prezzo valido è quello indicato su Amazon al momento dell’acquisto.');
  }
  if(name==='ordinary_product')row.amazon_link=html.includes('data-amazon-verified');
  if(name==='favorites')row.informative=html.includes('Funzione non disponibile')&&html.includes('/confronta-cibo');
  if(name==='history'||name==='price_history'||name==='price_alert'||name==='favorites')row.asset_reads=assetsRead-before;
  results.push(row);
  assert.equal(response.status,Number(expected),name);
  if(name==='home'||name==='privacy'||name.includes('product')){assert(!row.history_text,name);assert(!row.history_hooks,name)}
  if(name==='favorites'){assert(row.informative);assert.equal(row.asset_reads,0)}
  if(name==='history'||name==='price_history'||name==='price_alert')assert.equal(row.asset_reads,0);
  if(name==='amazon_product'){assert(row.amazon_link&&row.disclosure&&row.checkout_notice)}
  if(name==='ordinary_product')assert(!row.amazon_link);
 }
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
