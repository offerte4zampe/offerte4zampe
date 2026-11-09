import {amazonMode,amazonApproved,amazonLink,amazonPick,amazonText} from './telegram-amazon.mjs';
// No public publishing route. Only the Worker's scheduled handler reaches this object.
export const TEST_POST = {id:'telegram-test-v1',kind:'test',text:'🧪 MESSAGGIO DI PROVA — Offerte a 4 Zampe\nIl collegamento automatico al canale è attivo. Qui troverai consigli per risparmiare e segnalazioni verificate per cane e gatto.',path:'/'};
export const POSTS = [
 {id:'guide-unit-price-v1',kind:'guide',path:'/prezzo-confezione-o-prezzo-kg',text:'🐾 Il sacco meno caro è davvero il più conveniente?\nConfronta il prezzo al kg e lo stesso formato: il prezzo della confezione da solo può ingannare. Ecco come fare il confronto.',image:'/assets/social-guide.png'},
 {id:'guide-shipping-v1',kind:'guide',path:'/spedizione-gratuita-conviene',text:'📦 Spedizione gratuita: controlla il totale\nPrima di aggiungere prodotti per raggiungere la soglia, confronta quanto spenderesti pagando la consegna. La nostra guida ti aiuta a fare i conti.'},
 {id:'guide-identity-v1',kind:'guide',path:'/stesso-prodotto-formato-gtin',text:'🔎 Due confezioni simili possono essere prodotti diversi.\nRicetta, peso e codice prodotto contano: verifica che il confronto riguardi davvero lo stesso articolo prima di scegliere.'}
];
// Only original product photos supplied by approved partner catalog feeds.
// Never replace a product photo with a generic brand graphic.
export function productPhoto(offer){
 const hosts={'bauzaar':['cdn.shopify.com'],'isola-dei-tesori':['www.isoladeitesori.it'],'paco':['www.pacopetshop.it']};
 try{
  const url=new URL(offer?.image);
  if(url.protocol!=='https:'||url.username||url.password||!hosts[offer?.merchant_id]?.includes(url.hostname)||!/\.(?:jpe?g|png)$/i.test(url.pathname))return null;
  return url.href;
 }catch{return null;}
}
// A price report is not a claimed discount. Use only fresh available records
// from a successful current source; expose source/time and exclude delivery.
export function offerPost(offer,sources,now){
 const source=sources?.find(s=>s.id===offer?.merchant_id&&s.status==='ok');
 const stamp=Date.parse(offer?.checked_at),sourceStamp=Date.parse(source?.checked_at);
 if(!source||!Number.isFinite(stamp)||stamp>now||now-stamp>24*3600000||!Number.isFinite(sourceStamp)||sourceStamp>now||now-sourceStamp>24*3600000)return null;
 if(offer.available!==true||!Number.isFinite(offer.price)||offer.price<=0||!Number.isFinite(offer.weight_kg)||offer.weight_kg<=0||!productPhoto(offer))return null;
 if(typeof offer.id!=='string'||offer.id.length>200||typeof offer.title!=='string'||!offer.title.trim()||offer.title.length>240||typeof offer.merchant!=='string'||!offer.merchant.trim())return null;
 const format=typeof offer.variant==='string'&&offer.variant.trim()?offer.variant.trim():typeof offer.canonical_format==='string'?offer.canonical_format.trim():'';
 if(!format&&!/\d+(?:[.,]\d+)?\s*(?:kg|g|gr|grammi|ml|l)\b/i.test(offer.title))return null;
 const euro=new Intl.NumberFormat('it-IT',{style:'currency',currency:'EUR'});
 const time=new Intl.DateTimeFormat('it-IT',{timeZone:'Europe/Rome',dateStyle:'short',timeStyle:'short'}).format(stamp);
 const path=typeof offer.product_url==='string'&&/^\/prodotto\/[a-z0-9-]{1,200}$/.test(offer.product_url)?offer.product_url:'/prodotto?id='+encodeURIComponent(offer.id);
 return {id:'catalog:'+offer.id,kind:'price_report',image:productPhoto(offer),verified_at:stamp,path,title:offer.title.trim(),variant:format,price:offer.price,merchant:offer.merchant.trim(),text:'🐾 '+offer.title+'\n'+euro.format(offer.price)+' · '+offer.merchant+'\nSpedizione esclusa. Rilevazione: '+time+'.'};
}
export function trackedUrl(post){
 const url=new URL(post.path,'https://offerte4zampe.it');
 if(url.origin!=='https://offerte4zampe.it'||url.username||url.password)throw new Error('invalid_site_link');
 url.searchParams.set('utm_source','telegram');url.searchParams.set('utm_medium','social');
 url.searchParams.set('utm_campaign',post.kind==='test'?'integration_test':'channel_editorial');url.searchParams.set('utm_content',post.id);
 return url.href;
}
export function escapeTelegramHtml(value){
 return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
export function payload(post,channel){
 if(channel!=='@sconti4zampe')throw new Error('invalid_channel');
 if(post.kind==='amazon_pick'){
  // Never turn this into a redirect through our own site.
  const link=amazonLink(post.asin,post.associate_tag);
  return amazonText(post,link,escapeTelegramHtml);
 }
 const target=escapeTelegramHtml(trackedUrl(post));
 const disclosure='Link affiliati: potremmo ricevere una commissione senza costi aggiuntivi.';
 let visible,text;
 if(post.kind==='price_report'){
  const title=String(post.title||'').trim();
  const format=String(post.variant||'').trim();
  const normalize=s=>s.toLocaleLowerCase('it').replace(/[\s.,]/g,'');
  const label=title+(format&&!normalize(title).includes(normalize(format))?' · '+format:'');
  const euro=new Intl.NumberFormat('it-IT',{style:'currency',currency:'EUR'}).format(post.price);
  const stamp=new Intl.DateTimeFormat('it-IT',{timeZone:'Europe/Rome',dateStyle:'short',timeStyle:'short'}).format(post.verified_at);
  const note='📦 Spedizione esclusa · rilevato '+stamp+'. Prezzo e disponibilità da verificare nel negozio.';
  const action='🔎 Vedi prodotto e confronta i prezzi';
  const useful='Confronta lo stesso formato per valutare correttamente il prezzo.';
  visible=['🐾 '+label,'💶 '+euro+' · '+post.merchant,useful,note,action,disclosure].join('\n\n');
  text='🐾 <b>'+escapeTelegramHtml(label)+'</b>\n\n💶 <b>'+escapeTelegramHtml(euro)+'</b> · '+escapeTelegramHtml(post.merchant)+'\n\n'+escapeTelegramHtml(useful)+'\n\n'+escapeTelegramHtml(note)+'\n\n<a href="'+target+'">'+action+'</a>\n\n'+escapeTelegramHtml(disclosure);
 }else{
  const action=post.kind==='test'?'🔎 Visita Offerte a 4 Zampe':'🔎 Leggi la guida';
  visible=[post.text,action,disclosure].join('\n\n');
  text=escapeTelegramHtml(post.text)+'\n\n<a href="'+target+'">'+action+'</a>\n\n'+escapeTelegramHtml(disclosure);
 }
 if(Array.from(visible).length>(post.image?1024:4096))throw new Error('message_too_long');
 if(post.image){
  const image=new URL(post.image,'https://offerte4zampe.it');
  if(image.username||image.password||image.protocol!=='https:'||!['https://offerte4zampe.it','https://cdn.shopify.com','https://www.isoladeitesori.it','https://www.pacopetshop.it'].includes(image.origin)||!(/\.(?:jpe?g|png)$/i.test(image.pathname)))throw new Error('invalid_image');
  return {method:'sendPhoto',body:{chat_id:channel,photo:image.href,caption:text,parse_mode:'HTML',disable_notification:post.kind==='test'}};
 }
 return {method:'sendMessage',body:{chat_id:channel,text,parse_mode:'HTML',disable_notification:post.kind==='test',link_preview_options:{is_disabled:true}}};
}
export async function telegramCall(token,method,body,transport=fetch){
 // Never return/log raw exceptions, response descriptions, request URLs or token.
 try{
  const response=await transport(`https://api.telegram.org/bot${token}/${method}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:AbortSignal.timeout(12000)});
  const data=await response.json();
  if(response.ok&&data.ok&&Number.isSafeInteger(data.result?.message_id)&&data.result?.chat?.username?.toLowerCase()==='sconti4zampe')return {status:'sent',message_id:data.result.message_id};
  if(data.ok===false&&(response.status===429||data.error_code===429))return {status:'retry',retry_after:Math.min(86400,Math.max(1,Number(data.parameters?.retry_after)||60))};
  // 5xx/network timeouts may have succeeded remotely. Never retry automatically.
  return {status:response.status>=500||data.ok===true?'uncertain':'failed',code:Number(data.error_code)||response.status};
 }catch{return {status:'uncertain',code:'transport_or_response_error'};}
}
export class TelegramPublisher {
 constructor(state,env){this.state=state;this.env=env;this.chain=Promise.resolve();}
 fetch(request){
  // Internal binding only; request body cannot supply text, recipient or URLs.
  if(request.method==='GET')return Promise.all([this.state.storage.get('post:'+TEST_POST.id),this.state.storage.get('last_day'),this.state.storage.get('halted'),this.state.storage.get('last_publication')]).then(([test,last_day,halted,last_publication])=>Response.json({integration:'telegram-v1',content_mode:amazonMode(this.env)?'amazon_only':'catalog',amazon_owner_enabled:amazonApproved(this.env),configured:Boolean(this.env.TELEGRAM_BOT_TOKEN)&&this.env.TELEGRAM_CHANNEL_ID==='@sconti4zampe',token_present:Boolean(this.env.TELEGRAM_BOT_TOKEN),channel_present:Boolean(this.env.TELEGRAM_CHANNEL_ID),channel_matches:this.env.TELEGRAM_CHANNEL_ID==='@sconti4zampe',test_status:test?.status||'pending',test_message_id:test?.message_id||null,last_sent_day:last_day||null,last_publication:last_publication||null,halted:Boolean(halted)}));
  if(request.method!=='POST')return Promise.resolve(new Response(null,{status:405}));
  const run=this.chain.then(()=>this.tick());this.chain=run.catch(()=>{});
  return run.then(result=>Response.json(result));
 }
 async publishAmazon(post,now,day){
  // One post/day, durable dedupe and bounded errors, same as catalog publisher.
  const store=this.state.storage,key='post:'+post.id,prior=await store.get(key);
  if(prior)return {status:prior.status};
  if(post.image){
   let photo;
   try{photo=await this.env.ASSETS.fetch(new Request('https://offerte4zampe.it'+post.image));}
   catch{return {status:'photo_unavailable'};}
   if(!photo.ok||!String(photo.headers.get('content-type')||'').startsWith('image/'))return {status:'photo_unavailable'};
  }
  let request;
  try{request=payload(post,this.env.TELEGRAM_CHANNEL_ID);}
  catch{return {status:'invalid_amazon_pick'};}
  await store.put(key,{id:post.id,status:'sending',attempts:1,attempted_at:new Date(now).toISOString()});
  const outcome=await telegramCall(this.env.TELEGRAM_BOT_TOKEN,request.method,request.body);
  await store.put(key,{id:post.id,status:outcome.status,message_id:outcome.message_id||null,finished_at:new Date().toISOString()});
  if(outcome.status==='sent'){
   await store.put('last_day',day);
   await store.put('last_publication',{kind:'amazon_pick',path:null,asin:post.asin,message_id:outcome.message_id,sent_at:new Date().toISOString()});
  }else{
   // No blind retry: rate limit, timeout or a restart may leave delivery uncertain.
   await store.put('halted',true);
  }
  return {status:outcome.status};
 }
 async tick(now=Date.now()){
  const store=this.state.storage;
  if(!this.env.TELEGRAM_BOT_TOKEN||this.env.TELEGRAM_CHANNEL_ID!=='@sconti4zampe')return {status:'not_configured'};
  // AMAZON-ONLY is deliberately fail-closed. Old catalog/test/retry posts may
  // not be transmitted while this mode is selected, even on the first cron.
  if(amazonMode(this.env)&&!amazonApproved(this.env))return {status:'amazon_owner_disabled'};
  if(await store.get('halted'))return {status:'halted'};
  if(amazonMode(this.env)){
   const day=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Rome',year:'numeric',month:'2-digit',day:'2-digit'}).format(now);
   const time=new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Rome',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(now);
   if(time<'09:15'||await store.get('last_day')===day)return {status:'idle'};
   let entries;
   try{
    const r=await this.env.ASSETS.fetch(new Request('https://offerte4zampe.it/data/telegram-amazon.json'));
    if(!r.ok)return {status:'amazon_feed_unavailable'};
    entries=(await r.json()).offers;
   }catch{return {status:'amazon_feed_unavailable'};}
   if(!Array.isArray(entries))return {status:'amazon_feed_invalid'};
   let post;
   for(const item of entries){
    const candidate=amazonPick(item,now,this.env);
    if(candidate&&!(await store.get('post:'+candidate.id))){post=candidate;break;}
   }
   if(!post)return {status:'no_approved_amazon_pick'};
   try{post.associate_tag=this.env.AMAZON_ASSOCIATE_TAG;amazonLink(post.asin,post.associate_tag);}
   catch{return {status:'amazon_tag_not_configured'};}
   return this.publishAmazon(post,now,day);
  }
  const test=await store.get('post:'+TEST_POST.id);
  let post;
  if(test?.status!=='sent')post=TEST_POST;
  else if(await store.get('retry_post'))post=await store.get('retry_post');
  else {
   // At most one ordinary post daily, 09:15 Europe/Rome; first ordinary post next day.
   const day=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Rome',year:'numeric',month:'2-digit',day:'2-digit'}).format(now);
   const time=new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Rome',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(now);
   if(time<'09:15'||await store.get('last_day')===day)return {status:'idle'};
   // Daily verified photo offers; never fall back to text-only guides.
   try{
    const data=await this.env.ASSETS.fetch(new Request('https://offerte4zampe.it/data/home.json'));
    if(data.ok){const home=await data.json();for(const offer of home.offers||[]){const candidate=offerPost(offer,home.sources,now);if(candidate&&!(await store.get('post:'+candidate.id))){post=candidate;break;}}}
   }catch{/* unavailable/invalid catalog: no fabricated prices */}
   // After homepage highlights are exhausted, use a separate small curated
   // feed from approved partner catalog photos; never scrape or invent prices.
   if(!post){
    try{
     const response=await this.env.ASSETS.fetch(new Request('https://offerte4zampe.it/data/telegram-picks.json'));
     if(response.ok){
      const picks=await response.json();
      for(const offer of picks.offers||[]){
       const candidate=offerPost(offer,picks.sources,now);
       if(candidate&&!(await store.get('post:'+candidate.id))){post=candidate;break;}
      }
     }
    }catch{/* stale/missing picks must not produce an unverified post */}
   }
   // No fallback to text-only or generic-image guides: editorial photo is mandatory.
   if(!post)return {status:'no_verified_photo_offer'};
  }
  const key='post:'+post.id,prior=await store.get(key);
  if(post.kind==='price_report'&&now-post.verified_at>24*3600000){await store.put(key,{id:post.id,status:'expired',finished_at:new Date(now).toISOString()});await store.delete('retry_post');return {status:'expired'};}
  if(prior&&prior.status!=='retry')return {status:prior.status};
  if(prior?.next_at>now)return {status:'waiting'};
  if((prior?.attempts||0)>=4){await store.put('halted',true);return {status:'halted'};}
  // Verify the linked page/image exists before reserving the send.
  // /prodotto?id=... is a Worker route, not a static ASSETS file.
  // Its offer id was validated against today's catalog by offerPost().
  if(post.kind!=='price_report'){
   const asset=await this.env.ASSETS.fetch(new Request(new URL(post.path,'https://offerte4zampe.it')));
   if(!asset.ok)return {status:'asset_unavailable'};
  }
  if(post.kind!=='test'&&!post.image)return {status:'photo_required'};
  if(post.image){
   let photo;
   try{
    const imageUrl=new URL(post.image,'https://offerte4zampe.it');
    photo=imageUrl.origin==='https://offerte4zampe.it'
      ?await this.env.ASSETS.fetch(new Request(imageUrl))
      :await fetch(imageUrl,{method:'GET',signal:AbortSignal.timeout(12000)});
   }catch{return {status:'photo_unavailable'};}
   if(!photo.ok||!String(photo.headers.get('content-type')||'').startsWith('image/'))return {status:'photo_unavailable'};
  }
  const request=payload(post,this.env.TELEGRAM_CHANNEL_ID);
  const pending={id:post.id,status:'sending',attempts:(prior?.attempts||0)+1,attempted_at:new Date(now).toISOString()};
  await store.put(key,pending); // persisted before network: restart cannot send twice
  const outcome=await telegramCall(this.env.TELEGRAM_BOT_TOKEN,request.method,request.body);
  const record={...pending,...outcome,finished_at:new Date().toISOString()};
  if(outcome.status==='retry'){record.next_at=Date.now()+outcome.retry_after*1000;await store.put('retry_post',post);}
  else await store.delete('retry_post');
  await store.put(key,record);
  if(outcome.status==='sent'){
   await store.put('last_day',new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Rome',year:'numeric',month:'2-digit',day:'2-digit'}).format(now));
   await store.put('last_publication',{kind:post.kind,path:post.path,message_id:outcome.message_id,sent_at:new Date().toISOString()});
  }else if(outcome.status!=='retry')await store.put('halted',true);
  console.log({type:'telegram_publish',id:post.id,status:outcome.status,...(outcome.message_id?{message_id:outcome.message_id}:{})});
  return {status:outcome.status};
 }
}
export async function scheduledTelegram(env){
 if(!env.TELEGRAM_PUBLISHER)return;
 const object=env.TELEGRAM_PUBLISHER.get(env.TELEGRAM_PUBLISHER.idFromName('sconti4zampe-v1'));
 await object.fetch(new Request('https://internal/tick',{method:'POST'}));
}
