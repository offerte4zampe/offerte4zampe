(function(root){'use strict';
const metadata=typeof module!=='undefined'&&module.exports?require('./catalog-metadata.js'):root.O4ZMetadata;
function curatedURL(row,tag){
 if(!Object.hasOwn(row,'sitestripe_url'))return 'https://www.amazon.it/dp/'+row.asin+'?tag='+encodeURIComponent(tag);
 if(row.owner_variant_confirmed!==true||row.resolved_tracking_id!==tag||row.resolved_asin!==row.asin)return null;
 try{const u=new URL(row.sitestripe_url);if(u.protocol!=='https:'||u.hostname!=='link.amazon'||u.port||u.username||u.password||u.search||u.hash||!/^\/[A-Za-z0-9]{9}$/.test(u.pathname))return null;return row.sitestripe_url;}catch{return null}
}
// Editorial product links only: never add these to priced catalog offers or rankings.
function productLink(offer,config,now=Date.now()){
 if(!offer||!/^[a-z0-9-]+-21$/.test(config?.tracking_id||''))return null;
 const matches=(Array.isArray(config.links)?config.links:[]).filter(row=>row.offer_id===offer.id);
 if(matches.length!==1)return null;
 const row=matches[0],stamp=Date.parse(row.checked_at);
 if(!/^[A-Z0-9]{10}$/.test(row.asin||'')||!Number.isFinite(stamp)||stamp>now+300000||now-stamp>30*86400000)return null;
 if((metadata?metadata.brand(row.brand):String(row.brand??''))!==(metadata?metadata.brand(offer.brand):String(offer.brand??'')))return null;
 for(const key of ['title','variant','gtin'])if(String(row[key]??'')!==String(offer[key]??''))return null;
 try{const evidence=new URL(row.evidence_url);if(evidence.protocol!=='https:'||evidence.hostname!=='www.amazon.it'||evidence.username||evidence.password||!evidence.pathname.endsWith('/dp/'+row.asin))return null}catch{return null}
 const url=curatedURL(row,config.tracking_id);if(!url)return null;
 return {url,checked_at:row.checked_at};
}
function comparisonLink(seed,offers,config,now=Date.now()){
 const direct=productLink(seed,config,now);if(direct)return direct;
 const trade=typeof module!=='undefined'&&module.exports?require('./trade.js'):root.O4ZTrade;
 const key=trade.matchKey(seed,now);if(!key)return null;
 const matches=offers.filter(o=>trade.matchKey(o,now)===key).map(o=>productLink(o,config,now)).filter(Boolean);
 const urls=new Set(matches.map(m=>m.url));return urls.size===1?matches[0]:null;
}
const api={productLink,comparisonLink};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.O4ZAmazon=api;
})(typeof window!=='undefined'?window:null);
