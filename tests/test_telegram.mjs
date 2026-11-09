import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../worker/index.mjs';
import {TelegramPublisher,telegramCall,payload,trackedUrl,TEST_POST,POSTS,offerPost} from '../worker/telegram.mjs';
function setup(){const map=new Map();const state={storage:{get:async k=>map.get(k),put:async(k,v)=>{map.set(k,structuredClone(v));},delete:async k=>map.delete(k)}};const env={TELEGRAM_BOT_TOKEN:'fake-test-value',TELEGRAM_CHANNEL_ID:'@sconti4zampe',ASSETS:{fetch:async()=>new Response('ok')}};return {map,state,env,object:new TelegramPublisher(state,env)};}
const ok=()=>Response.json({ok:true,result:{message_id:42,chat:{username:'sconti4zampe'}}});
test('site links are UTM tagged and foreign destinations rejected',()=>{const url=new URL(trackedUrl(TEST_POST));assert.equal(url.searchParams.get('utm_source'),'telegram');assert.equal(url.searchParams.get('utm_content'),TEST_POST.id);assert.throws(()=>trackedUrl({...TEST_POST,path:'https://evil.example'}));assert.throws(()=>payload(TEST_POST,'@other'));});
test('plain text, photo captions, affiliation and limits',()=>{assert.equal(payload(TEST_POST,'@sconti4zampe').method,'sendMessage');const p=payload(POSTS[0],'@sconti4zampe');assert.equal(p.method,'sendPhoto');assert.match(p.body.caption,/Link affiliati/);assert.equal(p.body.parse_mode,'HTML');assert.match(p.body.caption,/<a href=/);assert.doesNotMatch(p.body.caption,/\nhttps:\/\//);assert.throws(()=>payload({...TEST_POST,text:'a'.repeat(4096)},'@sconti4zampe'));assert.throws(()=>payload({...POSTS[0],image:'https://evil.example/a.png'},'@sconti4zampe'));});
test('missing credentials cause zero requests',async()=>{const x=setup();delete x.env.TELEGRAM_BOT_TOKEN;assert.equal((await x.object.tick()).status,'not_configured');assert.equal(x.map.size,0);});
test('persistent reservation survives restart and concurrent ticks send once',async()=>{const x=setup(),original=global.fetch;let calls=0;global.fetch=async()=>{calls++;return ok();};try{await Promise.all([x.object.fetch(new Request('https://internal',{method:'POST'})),x.object.fetch(new Request('https://internal',{method:'POST'}))]);const restarted=new TelegramPublisher(x.state,x.env);await restarted.tick();assert.equal(calls,1);assert.equal(x.map.get('post:'+TEST_POST.id).message_id,42);}finally{global.fetch=original;}});
test('429 is deferred and bounded; only rejected request is retried',async()=>{const x=setup(),original=global.fetch;let calls=0;global.fetch=async()=>{calls++;return calls===1?Response.json({ok:false,error_code:429,parameters:{retry_after:120}},{status:429}):ok();};try{const now=Date.now();assert.equal((await x.object.tick(now)).status,'retry');assert.equal((await x.object.tick(now+1000)).status,'waiting');assert.equal(calls,1);assert.equal((await x.object.tick(now+121000)).status,'sent');assert.equal(calls,2);}finally{global.fetch=original;}});
test('timeout and 5xx are ambiguous and halt further publishing without leaking errors',async()=>{for(const transport of [async()=>{throw Error('SECRET URL');},async()=>new Response('upstream',{status:503})]){const x=setup(),original=global.fetch;let calls=0;global.fetch=async(...args)=>{calls++;return transport(...args);};try{assert.equal((await x.object.tick()).status,'uncertain');assert.equal((await x.object.tick()).status,'halted');assert.equal(calls,1);assert.doesNotMatch(JSON.stringify([...x.map]),/SECRET/);}finally{global.fetch=original;}}});
test('reservation left by crash is never resent',async()=>{const x=setup();x.map.set('post:'+TEST_POST.id,{status:'sending'});assert.equal((await x.object.tick()).status,'sending');});
test('failed permissions halt; incorrect target response treated as uncertain',async()=>{assert.equal((await telegramCall('fake','sendMessage',{},async()=>Response.json({ok:false,error_code:403},{status:403}))).status,'failed');assert.equal((await telegramCall('fake','sendMessage',{},async()=>Response.json({ok:true,result:{message_id:1,chat:{username:'other'}}}))).status,'uncertain');});
test('ordinary Telegram posts never fall back to text-only guides',async()=>{const x=setup(),original=global.fetch;let calls=0;global.fetch=async()=>{calls++;return ok();};try{await x.object.tick(Date.parse('2026-10-26T08:15:00Z'));assert.equal(calls,1);assert.equal((await x.object.tick(Date.parse('2026-10-27T08:15:00Z'))).status,'no_verified_photo_offer');assert.equal(calls,1);}finally{global.fetch=original;}});
test('public HTTP requests cannot reach publisher',async()=>{let calls=0;const env={ASSETS:{fetch:async()=>new Response('not found',{status:404})},TELEGRAM_PUBLISHER:{get(){calls++;throw Error('must not run');}}};for(const method of ['GET','POST'])assert.equal((await worker.fetch(new Request('https://offerte4zampe.it/api/telegram/send',{method}),env)).status,404);assert.equal(calls,0);});
test('missing linked assets prevent transmission',async()=>{const x=setup();x.env.ASSETS.fetch=async()=>new Response('',{status:404});assert.equal((await x.object.tick()).status,'asset_unavailable');assert.equal(x.map.size,0);});

test('price reports require fresh available exact-format records and a healthy source',()=>{
 const now=Date.parse('2026-10-26T08:00:00Z'),source={id:'isola-dei-tesori',status:'ok',checked_at:'2026-10-26T07:00:00Z'};
 const offer={id:'isola-dei-tesori:1',merchant_id:'isola-dei-tesori',merchant:'Isola dei Tesori',title:'Crocchette 10 kg',variant:'10 kg',weight_kg:10,price:35,available:true,checked_at:source.checked_at,image:'https://www.isoladeitesori.it/on/demandware.static/-/Sites-it-master-catalog/default/product.jpg'};
 const post=offerPost(offer,[source],now);assert.match(post.text,/35,00/);assert.match(post.text,/Spedizione esclusa/);assert.equal(new URL(trackedUrl(post)).searchParams.get('id'),'isola-dei-tesori:1');
 for(const change of [{available:false},{price:0},{price:'35'},{weight_kg:null},{image:null},{image:'https://evil.example/other.jpg'},{image:'https://www.isoladeitesori.it/other.webp'},{checked_at:'2026-10-24T07:00:00Z'},{checked_at:'2026-10-27T07:00:00Z'}])assert.equal(offerPost({...offer,...change},[source],now),null);
 assert.ok(offerPost({...offer,variant:''},[source],now),'pack size in title is sufficient when variant is blank');
 assert.equal(offerPost(offer,[{...source,status:'error'}],now),null);
});
test('verified product report sends authentic image without static probing of dynamic route',async()=>{
 const x=setup(),original=global.fetch,now=Date.parse('2026-10-29T08:15:00Z');
 x.map.set('post:'+TEST_POST.id,{status:'sent',message_id:1});
 const stamp='2026-10-29T07:00:00Z';
 const offer={id:'isola-dei-tesori:1',merchant_id:'isola-dei-tesori',merchant:'Isola dei Tesori',title:'Crocchette cane 15 kg',variant:'15 kg',weight_kg:15,price:74.39,available:true,checked_at:stamp,image:'https://www.isoladeitesori.it/media/royal-canin-15kg.jpg'};
 const requested=[];x.env.ASSETS.fetch=async request=>{requested.push(new URL(request.url).pathname);return Response.json({sources:[{id:'isola-dei-tesori',status:'ok',checked_at:stamp}],offers:[offer]});};
 let photos=0,sends=0;
 global.fetch=async (url,init)=>{if(String(url).includes('api.telegram.org')){sends++;assert.equal(JSON.parse(init.body).photo,offer.image);return ok();}photos++;return new Response('photo',{headers:{'content-type':'image/jpeg'}});};
 try{assert.equal((await x.object.tick(now)).status,'sent');assert.deepEqual(requested,['/data/home.json']);assert.equal(photos,1);assert.equal(sends,1);}finally{global.fetch=original;}
});
test('status exposes verified publication receipt without private details',async()=>{
 const x=setup(),original=global.fetch;
 global.fetch=async()=>ok();
 try{
  assert.equal((await x.object.tick()).status,'sent');
  const status=await (await x.object.fetch(new Request('https://internal/status'))).json();
  assert.equal(status.last_publication.kind,'test');
  assert.equal(status.last_publication.path,'/');
  assert.equal(status.last_publication.message_id,42);
  assert.ok(Number.isFinite(Date.parse(status.last_publication.sent_at)));
  assert.doesNotMatch(JSON.stringify(status),/fake-test-value|TELEGRAM_BOT_TOKEN/);
 }finally{global.fetch=original;}
});
test('status is read only and never exposes secret or private history',async()=>{const x=setup();const result=await x.object.fetch(new Request('https://internal/status'));const body=await result.json();assert.equal(body.configured,true);assert.equal(body.last_sent_day,null);assert.equal(body.last_publication,null);assert.equal(body.halted,false);assert.doesNotMatch(JSON.stringify(body),/fake-test-value/);assert.equal(x.map.size,0);assert.equal((await worker.fetch(new Request('https://offerte4zampe.it/api/telegram/status',{method:'POST'}),{})).status,405);});

test('Telegram product caption has concise HTML, safe escaping and hidden UTM URL',()=>{
 const now=Date.parse('2026-10-31T08:30:00Z'),stamp='2026-10-31T06:57:07Z';
 const source={id:'isola-dei-tesori',status:'ok',checked_at:stamp};
 const offer={id:'isola-dei-tesori:000124327',merchant_id:'isola-dei-tesori',merchant:'Isola dei Tesori',title:'Royal Canin Dog Medium Adult 15 kg',variant:'',canonical_format:'15 kg',weight_kg:15,price:74.39,available:true,checked_at:stamp,image:'https://www.isoladeitesori.it/media/royal-canin-15kg.jpg',product_url:'/prodotto/royal-canin-dog-medium-adult-15-kg'};
 const post=offerPost(offer,[source],now),p=payload(post,'@sconti4zampe');
 assert.equal(p.method,'sendPhoto');assert.equal(p.body.parse_mode,'HTML');
 assert.match(p.body.caption,/<b>74,39/);assert.match(p.body.caption,/<a href="https:\/\/offerte4zampe\.it\/prodotto\//);
 assert.match(p.body.caption,/utm_source=telegram&amp;utm_medium=social/);
 assert.doesNotMatch(p.body.caption,/Prezzo rilevato sul comparatore|\nhttps:\/\//);
 assert.match(p.body.caption,/Confronta lo stesso formato per valutare correttamente il prezzo\./);
 assert.equal((p.body.caption.match(/Confronta lo stesso formato/g)||[]).length,1);
 assert.throws(()=>payload({...post,title:'X'.repeat(1200)},'@sconti4zampe'),/message_too_long/);
 assert.doesNotMatch(p.body.caption,/15 kg · 15 kg/);
 const escaped=payload({...post,title:'Prodotto <test> & "prova"'},'@sconti4zampe');
 assert.match(escaped.body.caption,/&lt;test&gt; &amp; &quot;prova&quot;/);
 assert.equal(offerPost({...offer,image:'https://evil.example/false.jpg'},[source],now),null);
});
test('missed 09:15 cron can recover later the same morning without duplicates',async()=>{
 const x=setup(),original=global.fetch,stamp='2026-10-31T06:57:07Z',now=Date.parse('2026-10-31T08:30:00Z');
 x.map.set('post:'+TEST_POST.id,{status:'sent',message_id:1});
 const offer={id:'isola-dei-tesori:000124327',merchant_id:'isola-dei-tesori',merchant:'Isola dei Tesori',title:'Royal Canin Dog Medium Adult 15 kg',variant:'',canonical_format:'15 kg',weight_kg:15,price:74.39,available:true,checked_at:stamp,image:'https://www.isoladeitesori.it/media/royal-canin-15kg.jpg'};
 x.env.ASSETS.fetch=async()=>Response.json({sources:[{id:'isola-dei-tesori',status:'ok',checked_at:stamp}],offers:[offer]});
 let sends=0;global.fetch=async(url)=>{if(String(url).includes('api.telegram.org')){sends++;return ok();}return new Response('photo',{headers:{'content-type':'image/jpeg'}});};
 try{
  assert.equal((await x.object.tick(now)).status,'sent');
  assert.equal((await x.object.tick(now+15*60*1000)).status,'idle');
  assert.equal(sends,1);
 }finally{global.fetch=original;}
});

test('curated verified photo feed supplies a new product after home highlights are exhausted',async()=>{
 const x=setup(),original=global.fetch,stamp='2026-10-31T07:00:00Z',now=Date.parse('2026-10-31T08:30:00Z');
 x.map.set('post:'+TEST_POST.id,{status:'sent',message_id:1});
 const offer={id:'paco:brand-new',merchant_id:'paco',merchant:'Paco Pet Shop',title:'Almo Nature umido gatti 55 g',variant:'55 g',weight_kg:.055,price:1.5,available:true,checked_at:stamp,image:'https://www.pacopetshop.it/123-food.jpg'};
 const requested=[];x.env.ASSETS.fetch=async req=>{
  const path=new URL(req.url).pathname;requested.push(path);
  return Response.json(path==='/data/home.json'?{sources:[],offers:[]}:{sources:[{id:'paco',status:'ok',checked_at:stamp}],offers:[offer]});
 };
 let sends=0;global.fetch=async url=>{
  if(String(url).includes('api.telegram.org')){sends++;return ok();}
  return new Response('photo',{headers:{'content-type':'image/jpeg'}});
 };
 try{
  assert.equal((await x.object.tick(now)).status,'sent');
  assert.deepEqual(requested,['/data/home.json','/data/telegram-picks.json']);
  assert.equal(sends,1);
 }finally{global.fetch=original;}
});


test('Amazon-only mode refuses all publishing until channel approval and registration',async()=>{
 const x=setup(),original=global.fetch;
 x.env.TELEGRAM_CONTENT_MODE='amazon_only';
 x.env.AMAZON_TELEGRAM_PLACEMENT_APPROVED='false';
 x.env.AMAZON_TELEGRAM_CHANNEL_REGISTERED='false';
 let sends=0; global.fetch=async()=>{sends++;return ok();};
 try{
  x.map.set('retry_post',TEST_POST);
  assert.equal((await x.object.tick()).status,'amazon_owner_disabled');
  assert.equal(sends,0);
  assert.equal(x.map.get('post:'+TEST_POST.id),undefined);
  const status=await (await x.object.fetch(new Request('https://internal/status'))).json();
  assert.equal(status.content_mode,'amazon_only');
  assert.equal(status.amazon_owner_enabled,false);
 }finally{global.fetch=original;}
});
test('Amazon-only feed publishes only reviewed product with direct tagged URL, never a price',async()=>{
 const x=setup(),original=global.fetch,now=Date.parse('2026-11-08T10:00:00Z');
 Object.assign(x.env,{
  TELEGRAM_CONTENT_MODE:'amazon_only',
  TELEGRAM_AMAZON_OWNER_ENABLED:'true',
  
  AMAZON_ASSOCIATE_TAG:'example-21'
 });
 const offer={asin:'B012345678',title:'Ciotola da viaggio per cani',note:'La ciotola pieghevole può essere utile durante le passeggiate, verificando dimensioni e materiali.',image:'/assets/telegram-amazon/ciotola.jpg',rights_confirmed:true,editorial_reviewed:true,reviewed_at:'2026-11-07T12:00:00Z'};
 x.env.ASSETS.fetch=async request=>new URL(request.url).pathname==='/data/telegram-amazon.json'
  ?Response.json({offers:[{...offer,asin:'BAD'},offer]})
  :new Response('photo',{headers:{'content-type':'image/jpeg'}});
 let sends=0;
 global.fetch=async (url,init)=>{sends++;assert.match(String(url),/api.telegram.org/);const b=JSON.parse(init.body);assert.match(b.caption,/amazon.it\/dp\/B012345678\?tag=example-21/);assert.match(b.caption,/#pubblicità/);assert.doesNotMatch(b.caption,/prezzo|ribasso|minimo storico|€\s*\d/i);return ok();};
 try{
  assert.equal((await x.object.tick(now)).status,'sent');
  assert.equal((await x.object.tick(now+900000)).status,'idle');
  assert.equal(sends,1);
  assert.equal(x.map.get('last_publication').asin,'B012345678');
 }finally{global.fetch=original;}
});
test('Amazon direct-link data rejects stale, unlicensed and foreign image content',async()=>{
 const {amazonPick,amazonLink}=await import('../worker/telegram-amazon.mjs');
 const now=Date.parse('2026-11-08T10:00:00Z');
 const base={asin:'B012345678',title:'Ciotola da viaggio per cani',note:'Testo originale verificato per descrivere questo prodotto.',image:'/assets/telegram-amazon/ciotola.jpg',rights_confirmed:true,editorial_reviewed:true,reviewed_at:'2026-11-08T09:00:00Z'};
 assert.ok(amazonPick(base,now));
 for(const change of [{asin:'B0BAD'},{reviewed_at:'2026-10-01T09:00:00Z'},{rights_confirmed:false},{editorial_reviewed:false},{image:'https://images.amazon.com/image.jpg'},{image:'/assets/not-ours.jpg'}])assert.equal(amazonPick({...base,...change},now),null);
 assert.equal(amazonLink('B012345678','example-21'),'https://www.amazon.it/dp/B012345678?tag=example-21');
 assert.throws(()=>amazonLink('B012345678','bad-value'));
});
test('Amazon editorial selection can send a text-only message without images or prices',async()=>{
 const x=setup(),original=global.fetch,now=Date.parse('2026-11-09T10:00:00Z');
 Object.assign(x.env,{TELEGRAM_CONTENT_MODE:'amazon_only',TELEGRAM_AMAZON_OWNER_ENABLED:'true',AMAZON_ASSOCIATE_TAG:'offerte4zam0c-21'});
 const entry={asin:'B0002AR15U',title:'KONG Classic rosso, taglia S',note:'Gioco per cani: verifica taglia, prezzo e disponibilità direttamente nello shop prima di acquistare.',reviewed_at:'2026-10-21T00:00:00Z',editorial_reviewed:true};
 x.env.ASSETS.fetch=async req=>Response.json({offers:[entry]});
 let count=0;
 global.fetch=async (url,init)=>{
  count++;
  assert.equal(String(url).includes('sendMessage'),true);
  const payload=JSON.parse(init.body);
  assert.match(payload.text,/B0002AR15U\\?tag=offerte4zam0c-21/);
  assert.doesNotMatch(payload.text,/€|minimo storico|sconto del/);
  return ok();
 };
 try{
  assert.equal((await x.object.tick(now)).status,'sent');
  assert.equal((await x.object.tick(now+900000)).status,'idle');
  assert.equal(count,1);
 }finally{global.fetch=original;}
});
