import {outbound} from './outbound.mjs';
import {scheduledTelegram} from './telegram.mjs';
export {TelegramPublisher} from './telegram.mjs';
import {canonicalProduct,slugForOffer} from './canonical-product.mjs';
import {productPreview} from './product-preview.mjs';
async function htmlAsset(request,env){
 const result=await env.ASSETS.fetch(request);
 if(!result.headers.get('Content-Type')?.includes('text/html'))return result;
 const headers=new Headers(result.headers);
 headers.set('Cache-Control','public, max-age=0, must-revalidate');
 headers.set('Cloudflare-CDN-Cache-Control','no-store');
 return new Response(result.body,{status:result.status,headers});
}
const EVENTS = new Set(['page_view','catalog_search','compare_add','merchant_click']);
const PRODUCTS = new Set(['monge-maxi-adult-pollo','monge-medium-adult-pollo','monge-adult-manzo-riso','monge-adult-cat-pollo','royal-canin-medium-adult','royal-canin-maxi-adult','pro-plan-large-athletic-agnello','pro-plan-medium-sensitive-skin-salmone']);
const SHOPS = new Set(['Bauzaar','WebPet','Animaliapet','Isola dei Tesori','Paco Pet Shop','Amazon']);
export default {
  scheduled(event,env,ctx){ctx.waitUntil(scheduledTelegram(env));},
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    // Amazon Associates default: no historical price tracking or alert endpoints.
    // Fail closed before ASSETS access, metrics or any storage interactions.
    const priceTrackingEnabled = env.PRICE_TRACKING_ENABLED === 'true';
    if (!priceTrackingEnabled && /^\/preferiti(?:\.html|\/)?$/.test(url.pathname)) {
      const headers={'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store','X-Robots-Tag':'noindex, nofollow'};
      const body='<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Funzione non disponibile | Offerte a 4 Zampe</title></head><body><main><h1>Funzione non disponibile</h1><p>Questo strumento non è attualmente disponibile. Puoi comunque consultare le offerte correnti dei negozi.</p><p><a href="/confronta-cibo">Vai al comparatore</a></p></main></body></html>';
      return new Response(request.method==='HEAD'?null:body,{status:410,headers});
    }

    if (!priceTrackingEnabled && (
      /^\/data\/history(?:\/|$)/.test(url.pathname) ||
      /^\/data\/(?:price-history|price-observatory)(?:\.|\/|$)/.test(url.pathname) ||
      /^\/api\/(?:price-history|price-alerts?|alerts?|watchlist)(?:\/|$)/.test(url.pathname) ||
      /^\/(?:osservatorio-prezzi|leggere-storico-prezzi|preferiti)(?:\.html|\/)?$/.test(url.pathname)
    )) return new Response(null,{status:410,headers:{'Cache-Control':'no-store','X-Robots-Tag':'noindex, nofollow'}});
    if (['GET','HEAD'].includes(request.method) && url.pathname.endsWith('.html') && url.pathname !== '/prodotto.html' && !/^\/google[\w-]+\.html$/.test(url.pathname)) {
      url.pathname = url.pathname.endsWith('/index.html') ? url.pathname.slice(0, -10) || '/' : url.pathname.slice(0, -5);
      return Response.redirect(url.href, 301);
    }
    if(url.pathname.startsWith('/marca-')){
      const asset=await env.ASSETS.fetch(new Request(new URL('/data/brand-redirects.json',url.origin)));
      const redirects=asset.ok?await asset.json():{};const target=redirects[url.pathname];
      if(typeof target==='string'&&/^\/marca-[a-z0-9-]+$/.test(target)&&target!==url.pathname)return Response.redirect(new URL(target,url.origin).href,301);
    }
    if(url.pathname.startsWith('/go/'))return outbound(request,env,ctx);
    if(url.pathname==='/api/telegram/status'){
      if(request.method!=='GET')return new Response(null,{status:405});
      if(!env.TELEGRAM_PUBLISHER)return Response.json({integration:'telegram-v1',configured:false},{status:503});
      const stub=env.TELEGRAM_PUBLISHER.get(env.TELEGRAM_PUBLISHER.idFromName('sconti4zampe-v1'));
      // Explicit operator recovery: normal status reads remain read-only.
      // There is no caller-supplied recipient, message or product. The existing
      // Durable Object enforces reviewed entries, one send/day and deduplication.
      // This allows a safe catch-up when Cloudflare's scheduled trigger is delayed.
      let recovery=null;
      if(url.searchParams.get('recover')==='1'&&env.TELEGRAM_STATUS_RECOVERY==='true'){
        try{
          const attempted=await stub.fetch(new Request('https://internal/tick',{method:'POST'}));
          recovery=attempted.ok?await attempted.json():{status:'unavailable'};
        }catch{recovery={status:'unavailable'};}
      }
      const result=await stub.fetch(new Request('https://internal/status'));
      if(recovery===null)return new Response(result.body,{headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});
      const state=await result.json();
      return Response.json({...state,recovery_status:recovery?.status||'unknown'},{headers:{'Cache-Control':'no-store'}});
    }
    if(url.pathname.startsWith('/prodotto/'))return canonicalProduct(request,env);
    if (['/prodotto','/prodotto.html'].includes(url.pathname)){
      const ids=url.searchParams.getAll('id');
      if(['GET','HEAD'].includes(request.method)&&ids.length===1&&ids[0]&&ids[0].length<=200){
        try{const slug=await slugForOffer(env,url.origin,ids[0]);if(slug&&/^[a-z0-9-]{1,200}$/.test(slug))return Response.redirect(new URL('/prodotto/'+slug,url.origin).href,301)}catch{}
      }
      return productPreview(request,env);
    }
    if(url.pathname==='/confronta-cibo'&&url.searchParams.has('brand')){const result=await htmlAsset(request,env);const headers=new Headers(result.headers);headers.set('X-Robots-Tag','noindex, follow');return new Response(result.body,{status:result.status,headers})}
    if (url.pathname !== '/api/metrics') return htmlAsset(request,env);
    const headers = {'Cache-Control':'no-store'};
    if (request.method !== 'POST') return new Response(null,{status:405,headers});
    if (request.headers.get('Origin') !== url.origin) return new Response(null,{status:403,headers});
    if (!request.headers.get('Content-Type')?.startsWith('application/json')) return new Response(null,{status:415,headers});
    // Bound streamed input too: Content-Length alone is not trustworthy.
    const reader=request.body?.getReader(); if(!reader) return new Response(null,{status:400,headers});
    let size=0, parts=[];
    while(true){const {value,done}=await reader.read();if(done)break;size+=value.byteLength;if(size>512){await reader.cancel();return new Response(null,{status:413,headers});}parts.push(value);}
    let event; try {event=JSON.parse(await new Blob(parts).text());} catch{return new Response(null,{status:400,headers});}
    if(!EVENTS.has(event.event)||!['home','catalog','product','other'].includes(event.page))return new Response(null,{status:400,headers});
    // Never log request objects, URLs, query text, IPs, headers or visitor IDs.
    console.log({type:'usage',event:event.event,page:event.page,...(SHOPS.has(event.merchant)?{merchant:event.merchant}:{}),...(PRODUCTS.has(event.product)?{product:event.product}:{})});
    return new Response(null,{status:204,headers});
  }
};
