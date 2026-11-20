(function(root){'use strict';
const metadata=typeof module!=='undefined'&&module.exports?require('./catalog-metadata.js'):root.O4ZMetadata;
const identity=o=>JSON.stringify([o.gtin,o.weight_kg,String(o.brand||'').trim().toLowerCase()]);
function valid(o,index){if(!o.id||typeof o.title!=='string'||!Number.isFinite(o.price)||o.price<=0)return false;if(index)return /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(o.product_slug||'');try{return new URL(o.url).protocol==='https:'}catch{return false}}
function yieldToMain(){return typeof globalThis.scheduler?.yield==='function'?globalThis.scheduler.yield():new Promise(resolve=>setTimeout(resolve,0))}
async function prepare(offers,{chunkSize=500,yieldTask=yieldToMain,onChunk=null,index=false}={}){
 if(!Number.isInteger(chunkSize)||chunkSize<1)throw Error('Invalid chunk size');
 const data=[],searchText=new Map(),identityIndex=new Map();
 for(let start=0;start<offers.length;start+=chunkSize){
  const began=performance.now(),end=Math.min(start+chunkSize,offers.length);
  for(let i=start;i<end;i++){const o=metadata.normalize(offers[i]);if(!valid(o,index))continue;data.push(o);
   if(o.gtin&&o.weight_kg&&o.comparison_review?.review_state!=='unverified'){const key=identity(o);if(!identityIndex.has(key))identityIndex.set(key,[]);identityIndex.get(key).push(o)}
   searchText.set(o.id,[o.title,o.variant,o.brand,o.category,o.sku,o.gtin].join(' ').toLocaleLowerCase('it'));
  }
  if(onChunk)onChunk(performance.now()-began);
  if(end<offers.length)await yieldTask();
 }
 return {data,searchText,identityIndex};
}
const api={prepare,identity};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.O4ZCatalogPrepare=api;
})(typeof window!=='undefined'?window:null);
