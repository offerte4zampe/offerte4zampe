import metadata from '../site/assets/product-metadata.js';
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function rewrite(html,title,id){
 const name=metadata.title(title),description='Confronta '+title+'. Consulta formato e prezzi rilevati nei negozi; verifica disponibilità e totale prima di acquistare.';
 const url=new URL('https://offerte4zampe.it/prodotto');url.searchParams.set('id',id);
 return html.replace(/<title>[^<]*<\/title>/,()=>'<title>'+escape(name)+'</title>').replace(/<meta\s+(name|property)="(description|og:title|og:description|og:url)"\s+content="[^"]*"\s*>/g,(_,attr,key)=>'<meta '+attr+'="'+key+'" content="'+escape(key==='og:title'?name:key==='og:url'?url.href:description)+'">');
}
export async function productPreview(request,env){
 const url=new URL(request.url),ids=url.searchParams.getAll('id');
 if(request.method!=='GET'||!['/prodotto','/prodotto.html'].includes(url.pathname)||ids.length!==1||!ids[0]||ids[0].length>200)return env.ASSETS.fetch(request);
 try{
  const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(ids[0])),shard=[...new Uint8Array(digest)].slice(0,1).map(x=>x.toString(16).padStart(2,'0')).join('');
  const metaURL=new URL('/data/product-meta/'+shard+'.json',url.origin),meta=await env.ASSETS.fetch(new Request(metaURL));
  if(!meta.ok)return env.ASSETS.fetch(request);
  const names=await meta.json(),title=Object.hasOwn(names,ids[0])?names[ids[0]]:null;
  if(typeof title!=='string'||!title.trim()||title.length>240)return env.ASSETS.fetch(request);
  const asset=await env.ASSETS.fetch(new Request(new URL('/prodotto',url.origin)));
  if(!asset.ok||!asset.headers.get('Content-Type')?.includes('text/html'))return asset;
  const headers=new Headers(asset.headers);for(const key of ['Content-Length','Content-Encoding','ETag','Last-Modified'])headers.delete(key);
  headers.set('Cache-Control','no-store');
  headers.set('Cloudflare-CDN-Cache-Control','no-store');
  headers.set('CDN-Cache-Control','no-store');
  return new Response(rewrite(await asset.text(),title,ids[0]),{status:200,headers});
 }catch{return env.ASSETS.fetch(request)}
}
